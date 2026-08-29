import json
import logging
from typing import Any, AsyncGenerator, Dict

import httpx

from app.core.exceptions import (
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
)
from app.core.interfaces.llm_provider import BaseLLMProvider
from app.domain.llm.schemas import (
    GenerationRequest,
    GenerationResponse,
    LLMStreamEvent,
    TokenUsage,
)

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    """Adapter for local or remote Ollama native API (/api/chat)."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama3.2:3b",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "ollama"

    def _format_request_payload(
        self,
        request: GenerationRequest,
    ) -> Dict[str, Any]:
        """Convert the normalized request into Ollama's API format."""

        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in request.messages
        ]

        payload: Dict[str, Any] = {
            "model": request.model_override or self.default_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": request.temperature,
            },
        }

        # Ollama uses `num_predict` for maximum generated tokens.
        if request.max_tokens is not None:
            payload["options"]["num_predict"] = request.max_tokens

        # GenerationRequest exposes `response_format`.
        # Ollama's native API accepts `format="json"` for JSON output.
        if request.response_format is not None:
            payload["format"] = "json"

        return payload

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResponse:
        """Generate a complete response using Ollama's /api/chat endpoint."""

        url = f"{self.base_url}/api/chat"
        payload = self._format_request_payload(request)

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                )

        except httpx.RequestError as exc:
            raise LLMConnectionError(
                f"Ollama connection error: {exc}"
            ) from exc

        # ---------------------------------------------------------
        # HTTP error mapping
        # ---------------------------------------------------------

        if response.status_code == 404:
            raise LLMResponseError(
                f"Model or endpoint not found: {response.text}"
            )

        if response.status_code == 429:
            raise LLMRateLimitError(
                f"Ollama rate limit exceeded: {response.text}"
            )

        if response.status_code >= 400:
            raise LLMResponseError(
                f"Ollama API error "
                f"({response.status_code}): {response.text}"
            )

        # ---------------------------------------------------------
        # Parse Ollama response
        # ---------------------------------------------------------

        try:
            data = response.json()

            message_content = (
                data.get("message", {})
                .get("content", "")
            )

            finish_reason = data.get(
                "done_reason",
                "stop",
            )

            # Ollama calls these evaluation counts.
            prompt_tokens = data.get(
                "prompt_eval_count",
                0,
            )

            completion_tokens = data.get(
                "eval_count",
                0,
            )

            # Ollama reports total_duration in nanoseconds.
            #
            # Example:
            #     500,000,000 ns
            #
            # becomes:
            #     500 ms
            #
            # because:
            #     1 ms = 1,000,000 ns
            total_duration_ns = data.get(
                "total_duration"
            )

            if total_duration_ns is not None:
                latency_ms = (
                    total_duration_ns / 1_000_000
                )
            else:
                # Some compatible/mock responses may not
                # provide Ollama's timing metadata.
                latency_ms = 0.0

            return GenerationResponse(
                content=message_content,
                finish_reason=finish_reason,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=(
                        prompt_tokens
                        + completion_tokens
                    ),
                ),
                latency_ms=latency_ms,
                provider=self.provider_name,
                model=payload["model"],
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise LLMResponseError(
                f"Failed to parse Ollama response: {exc}"
            ) from exc

    async def stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[LLMStreamEvent, None]:
        """Stream generated tokens from Ollama's /api/chat endpoint."""

        url = f"{self.base_url}/api/chat"

        payload = self._format_request_payload(request)

        # Override the non-streaming default.
        payload["stream"] = True

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                ) as response:

                    # -------------------------------------------------
                    # HTTP error mapping
                    # -------------------------------------------------

                    if response.status_code == 404:
                        raise LLMResponseError(
                            "Ollama model or endpoint not found: "
                            f"{response.text}"
                        )

                    if response.status_code == 429:
                        raise LLMRateLimitError(
                            "Ollama rate limit exceeded: "
                            f"{response.text}"
                        )

                    if response.status_code >= 400:
                        raise LLMResponseError(
                            f"Ollama stream error "
                            f"({response.status_code}): "
                            f"{response.text}"
                        )

                    # -------------------------------------------------
                    # Process NDJSON stream
                    # -------------------------------------------------

                    async for line in response.aiter_lines():

                        if not line.strip():
                            continue

                        try:
                            chunk = json.loads(line)

                        except json.JSONDecodeError as exc:
                            raise LLMResponseError(
                                "Invalid JSON in Ollama stream: "
                                f"{line}"
                            ) from exc

                        content_delta = (
                            chunk.get("message", {})
                            .get("content", "")
                        )

                        finish_reason = (
                            chunk.get("done_reason")
                            if chunk.get("done")
                            else None
                        )

                        yield LLMStreamEvent(
                            content_delta=content_delta,
                            finish_reason=finish_reason,
                        )

        except httpx.RequestError as exc:
            raise LLMConnectionError(
                f"Ollama streaming connection error: {exc}"
            ) from exc