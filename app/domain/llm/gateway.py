import time
import logging
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.interfaces.llm_provider import BaseLLMProvider
from app.domain.llm.schemas import GenerationRequest, GenerationResponse
from app.core.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMStructuredOutputError
)

logger = logging.getLogger(__name__)

# Type variable for structured output validation
T = TypeVar("T", bound=BaseModel)

class LLMGateway:
    """
    Application-level orchestrator for LLM interactions.
    Handles cross-cutting concerns: retries, telemetry, and schema validation.
    """
    
    def __init__(self, provider: BaseLLMProvider):
        # The Gateway does not know if this is Ollama or vLLM. It only knows it's a BaseLLMProvider.
        self._provider = provider

    # Bounded retries: Only retry on transient network/rate-limit errors.
    # Do NOT retry on validation errors or bad requests.
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LLMConnectionError, LLMTimeoutError, LLMRateLimitError)),
        reraise=True
    )
    async def generate(self, request: GenerationRequest) -> GenerationResponse | T:
        """
        Executes the generation request.
        If `response_format` is provided in the request, this method parses the LLM text
        into the requested Pydantic model and returns the model.
        """
        start_time = time.perf_counter()
        
        try:
            # 1. Execute the actual network call via the injected provider
            response = await self._provider.generate(request)
            
            # 2. Record Metrics (Latency is handled by the provider or gateway, we log it here)
            duration_ms = (time.perf_counter() - start_time) * 1000
            response.latency_ms = duration_ms
            
            logger.info(
                f"LLM Generation successful | Provider: {self._provider.provider_name} | "
                f"Latency: {duration_ms:.2f}ms | Tokens: {response.usage.total_tokens}"
            )
            
            # 3. Handle Structured Output Validation (if requested)
            if request.response_format:
                return self._parse_structured_output(response.content, request.response_format)
                
            return response
            
        except Exception as e:
            # We log the failure before bubbling it up to the OSINT workflow
            logger.error(f"LLM Gateway encountered an error: {str(e)}")
            raise

    def _parse_structured_output(self, content: str, schema: type[T]) -> T:
        """Attempts to parse the raw text into the requested Pydantic schema."""
        try:
            # Pydantic's model_validate_json is highly optimized and strict
            return schema.model_validate_json(content)
        except ValidationError as e:
            raise LLMStructuredOutputError(
                f"Failed to parse LLM output into {schema.__name__}. "
                f"Raw output: {content}. Validation errors: {e.errors()}"
            ) from e