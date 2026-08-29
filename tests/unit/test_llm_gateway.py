import pytest
from pydantic import BaseModel
from unittest.mock import AsyncMock, patch

from app.domain.llm.gateway import LLMGateway
from app.domain.llm.schemas import (
    GenerationRequest,
    GenerationResponse,
    NormalizedMessage,
    MessageRole,
    TokenUsage,
)
from app.infrastructure.llm.fake_provider import FakeLLMProvider
from app.core.exceptions import (
    LLMConnectionError,
    LLMTimeoutError,
    LLMStructuredOutputError,
    LLMProviderError,
)

# Test Pydantic schema for structured output
class TargetSchema(BaseModel):
    summary: str
    risk_score: int


@pytest.mark.asyncio
async def test_gateway_successful_generation():
    fake_provider = FakeLLMProvider(default_response="Test response")
    gateway = LLMGateway(provider=fake_provider)

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Hello")]
    )

    response = await gateway.generate(request)

    assert isinstance(response, GenerationResponse)
    assert response.content == "Test response"
    assert response.latency_ms > 0
    assert fake_provider.call_count == 1


@pytest.mark.asyncio
async def test_gateway_structured_output_parsing_success():
    valid_json = '{"summary": "Suspicious activity detected", "risk_score": 8}'
    fake_provider = FakeLLMProvider(default_response=valid_json)
    gateway = LLMGateway(provider=fake_provider)

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Analyze threat")],
        response_format=TargetSchema,
    )

    result = await gateway.generate(request)

    assert isinstance(result, TargetSchema)
    assert result.summary == "Suspicious activity detected"
    assert result.risk_score == 8


@pytest.mark.asyncio
async def test_gateway_structured_output_validation_failure():
    invalid_json = '{"summary": "Missing risk score"}'
    fake_provider = FakeLLMProvider(default_response=invalid_json)
    gateway = LLMGateway(provider=fake_provider)

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Analyze threat")],
        response_format=TargetSchema,
    )

    with pytest.raises(LLMStructuredOutputError) as exc_info:
        await gateway.generate(request)

    assert "Failed to parse LLM output into TargetSchema" in str(exc_info.value)


@pytest.mark.asyncio
async def test_gateway_retry_on_transient_connection_error():
    fake_provider = FakeLLMProvider()
    gateway = LLMGateway(provider=fake_provider)

    # Simulate connection error on first call, success on second
    side_effects = [
        LLMConnectionError("Network drop"),
        GenerationResponse(
            content="Recovered",
            finish_reason="stop",
            usage=TokenUsage(),
            latency_ms=1.0,
            provider="fake",
            model="fake-model",
        ),
    ]

    with patch.object(fake_provider, "generate", side_effect=side_effects) as mock_gen:
        request = GenerationRequest(
            messages=[NormalizedMessage(role=MessageRole.USER, content="Ping")]
        )
        
        # Override wait exponential to speed up test execution
        with patch("tenacity.nap.sleep", AsyncMock()):
            response = await gateway.generate(request)

        assert response.content == "Recovered"
        assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_gateway_no_retry_on_non_transient_error():
    fake_provider = FakeLLMProvider()
    fake_provider.should_fail = LLMProviderError("Bad Request 400")
    gateway = LLMGateway(provider=fake_provider)

    request = GenerationRequest(
        messages=[NormalizedMessage(role=MessageRole.USER, content="Invalid")]
    )

    with pytest.raises(LLMProviderError):
        await gateway.generate(request)

    assert fake_provider.call_count == 1