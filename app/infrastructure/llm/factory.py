import logging
from typing import Dict, Type

from app.core.config import settings
from app.core.exceptions import LLMConfigurationError
from app.core.interfaces.llm_provider import BaseLLMProvider
from app.infrastructure.llm.ollama_adapter import OllamaProvider
from app.infrastructure.llm.openai_adapter import OpenAICompatProvider
from app.infrastructure.llm.fake_provider import FakeLLMProvider

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """Centralized registry for resolving LLM provider implementations."""

    _registry: Dict[str, Type[BaseLLMProvider]] = {
        "ollama": OllamaProvider,
        "openai": OpenAICompatProvider,
        "vllm": OpenAICompatProvider,
        "fake": FakeLLMProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_cls: Type[BaseLLMProvider]) -> None:
        """Allows registering new custom providers at runtime."""
        cls._registry[name.lower()] = provider_cls

    @classmethod
    def create(
        cls,
        provider_name: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
    ) -> BaseLLMProvider:
        """Instantiates a provider using explicit arguments or fallbacks to application settings."""
        name = (provider_name or settings.LLM_PROVIDER).lower()

        if name not in cls._registry:
            raise LLMConfigurationError(
                f"Unsupported LLM provider '{name}'. Configured providers: {list(cls._registry.keys())}"
            )

        if name == "ollama":
            return OllamaProvider(
                base_url=base_url or settings.LLM_BASE_URL,
                default_model=model or settings.LLM_MODEL,
            )
        elif name in ("openai", "vllm"):
            return OpenAICompatProvider(
                base_url=base_url or settings.LLM_BASE_URL,
                api_key=api_key or settings.LLM_API_KEY,
                default_model=model or settings.LLM_MODEL,
                timeout=settings.LLM_TIMEOUT,
            )
        elif name == "fake":
            return FakeLLMProvider()

        raise LLMConfigurationError(f"Initialization logic missing for registered provider '{name}'.")