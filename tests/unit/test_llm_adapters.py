import json
from unittest.mock import patch

import httpx
import pytest

from app.core.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
)
from app.domain.llm.schemas import GenerationRequest, MessageRole, NormalizedMessage
from app.infrastructure.llm.ollama_adapter import OllamaProvider
from app.infrastructure.llm.openai_adapter import OpenAICompatProvider

@pytest.mark.asyncio
async def test_ollama_adapter_successful_payload_mapping(monkeypatch):
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/chat"
        payload = json.loads(request.read())
        assert payload["model"] == "llama3.2:3b"
        assert payload["messages"][0]["role"] == "user"
        assert payload["options"]["temperature"] == 0.7

        mock_ollama_response = {
            "message": {"content": "Ollama response text"},
            "done_reason": "stop",
            "prompt_eval_count": 12,
            "eval_count": 8,
            "total_duration": 500000000,  # 500ms in nanoseconds
        }
        return httpx.Response(200, json=mock_ollama_response)

    transport = httpx.MockTransport(mock_handler)
    
    # Inject mock transport into async client creation
    provider = OllamaProvider(base_url="http://mock-ollama:11434")

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Test prompt")]
    )

    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        response = await provider.generate(request)

    assert response.content == "Ollama response text"
    assert response.usage.prompt_tokens == 12
    assert response.usage.completion_tokens == 8
    assert response.usage.total_tokens == 20
    assert response.latency_ms == 500.0


@pytest.mark.asyncio
async def test_ollama_adapter_404_error_mapping():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "model 'missing:latest' not found"})

    transport = httpx.MockTransport(mock_handler)
    provider = OllamaProvider(base_url="http://mock-ollama:11434")

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Test prompt")],
        model_override="missing:latest",
    )

    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        with pytest.raises(LLMResponseError) as exc_info:
            await provider.generate(request)
        assert "404" in str(exc_info.value) or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_openai_adapter_rate_limit_mapping():
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Rate limit exceeded"}})

    transport = httpx.MockTransport(mock_handler)
    provider = OpenAICompatProvider(base_url="http://mock-vllm:8000/v1")

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Test prompt")]
    )

    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=transport)):
        with pytest.raises(LLMRateLimitError):
            await provider.generate(request)