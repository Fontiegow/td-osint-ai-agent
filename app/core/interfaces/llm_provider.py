from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.domain.llm.schemas import GenerationRequest, GenerationResponse, LLMStreamEvent

class BaseLLMProvider(ABC):
    """
    The strict contract for all LLM providers.
    Adapters MUST implement these methods and handle their own HTTP client lifecycles.
    """
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Returns the identifier of the provider (e.g., 'ollama', 'vllm')."""
        pass

    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """
        Executes a single, complete generation request.
        Must translate internal domain schemas to provider-specific payloads,
        and translate provider-specific responses/errors back to domain models.
        """
        pass

    @abstractmethod
    async def stream(self, request: GenerationRequest) -> AsyncGenerator[LLMStreamEvent, None]:
        """
        Executes a streaming generation request.
        Must yield normalized stream events.
        """
        pass