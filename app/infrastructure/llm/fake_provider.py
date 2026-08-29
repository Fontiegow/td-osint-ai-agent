from typing import AsyncGenerator, Optional

from app.core.interfaces.llm_provider import BaseLLMProvider
from app.domain.llm.schemas import (
    GenerationRequest,
    GenerationResponse,
    LLMStreamEvent,
    TokenUsage,
)


class FakeLLMProvider(BaseLLMProvider):
    """Deterministic fake provider for fast offline unit testing."""

    def __init__(self, default_response: str = '{"status": "ok", "summary": "test OSINT output"}'):
        self.default_response = default_response
        self.should_fail: Optional[Exception] = None
        self.call_count = 0
        self.last_request: Optional[GenerationRequest] = None

    @property
    def provider_name(self) -> str:
        return "fake"

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        self.call_count += 1
        self.last_request = request

        if self.should_fail:
            raise self.should_fail

        return GenerationResponse(
            content=self.default_response,
            finish_reason="stop",
            usage=TokenUsage(prompt_tokens=10, completion_tokens=15, total_tokens=25),
            latency_ms=1.5,
            provider=self.provider_name,
            model=request.model_override or "fake-model",
        )

    async def stream(self, request: GenerationRequest) -> AsyncGenerator[LLMStreamEvent, None]:
        yield LLMStreamEvent(content_delta=self.default_response, finish_reason="stop")