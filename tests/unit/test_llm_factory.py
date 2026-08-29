import pytest

from app.core.exceptions import LLMConfigurationError
from app.infrastructure.llm.factory import LLMProviderFactory
from app.infrastructure.llm.ollama_adapter import OllamaProvider
from app.infrastructure.llm.openai_adapter import OpenAICompatProvider
from app.infrastructure.llm.fake_provider import FakeLLMProvider


def test_factory_creates_ollama_provider():
    provider = LLMProviderFactory.create(provider_name="ollama")
    assert isinstance(provider, OllamaProvider)
    assert provider.provider_name == "ollama"


def test_factory_creates_openai_provider():
    provider = LLMProviderFactory.create(provider_name="openai")
    assert isinstance(provider, OpenAICompatProvider)
    assert provider.provider_name == "openai_compatible"


def test_factory_creates_fake_provider():
    provider = LLMProviderFactory.create(provider_name="fake")
    assert isinstance(provider, FakeLLMProvider)
    assert provider.provider_name == "fake"


def test_factory_raises_on_invalid_provider():
    with pytest.raises(LLMConfigurationError) as exc_info:
        LLMProviderFactory.create(provider_name="unsupported_vendor")

    assert "Unsupported LLM provider 'unsupported_vendor'" in str(exc_info.value)