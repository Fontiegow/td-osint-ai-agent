import json
import logging
import time
from typing import Any, AsyncGenerator, Dict

import httpx

from app.core.exceptions import (
    LLMAuthenticationError,
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


class OpenAICompatProvider(BaseLLMProvider):
    """
    Adapter for OpenAI-compatible APIs.

    Compatible with services such as:
    - OpenAI
    - vLLM
    - OpenRouter
    - LocalAI
    - other OpenAI-compatible inference servers
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        api_key: str = "not-needed",
        default_model: str = "llama3.2:3b",
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
        self.timeout = timeout

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    def _format_request_payload(
        self,
        request: GenerationRequest,
    ) -> Dict[str, Any]:

        messages = [
            {
                "role": msg.role.value,
                "content": msg.content,
            }
            for msg in request.messages
        ]

        payload: Dict[str, Any] = {
            "model": (
                request.model_override
                or self.default_model
            ),
            "messages": messages,
            "temperature": request.temperature,
        }

        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        if request.response_format is not None:
            payload["response_format"] = {
                "type": "json_object"
            }

        return payload

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResponse:

        url = f"{self.base_url}/chat/completions"

        payload = self._format_request_payload(
            request
        )

        headers = self._get_headers()

        start_time = time.perf_counter()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                )

        except httpx.RequestError as exc:
            raise LLMConnectionError(
                f"OpenAI-compatible connection error: {exc}"
            ) from exc

        latency_ms = (
            time.perf_counter() - start_time
        ) * 1000

        if response.status_code == 401:
            raise LLMAuthenticationError(
                f"OpenAI-compatible authentication failed: "
                f"{response.text}"
            )

        if response.status_code == 429:
            raise LLMRateLimitError(
                f"OpenAI-compatible rate limit exceeded: "
                f"{response.text}"
            )

        if response.status_code >= 400:
            raise LLMResponseError(
                f"OpenAI-compatible API error "
                f"({response.status_code}): "
                f"{response.text}"
            )

        try:
            data = response.json()

            choices = data.get("choices", [])

            if not choices:
                raise ValueError(
                    "Response contains no choices"
                )

            choice = choices[0]

            message = choice.get("message", {})

            content = message.get(
                "content",
                "",
            )

            finish_reason = choice.get(
                "finish_reason",
                "stop",
            )

            usage_data = data.get(
                "usage",
                {},
            )

            prompt_tokens = usage_data.get(
                "prompt_tokens",
                0,
            )

            completion_tokens = usage_data.get(
                "completion_tokens",
                0,
            )

            total_tokens = usage_data.get(
                "total_tokens",
                prompt_tokens + completion_tokens,
            )

            return GenerationResponse(
                content=content,
                finish_reason=finish_reason,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                ),
                latency_ms=latency_ms,
                provider=self.provider_name,
                model=data.get(
                    "model",
                    payload["model"],
                ),
            )

        except (
            KeyError,
            IndexError,
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise LLMResponseError(
                "Failed to parse OpenAI-compatible "
                f"response: {exc}"
            ) from exc

    async def stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[LLMStreamEvent, None]:

        url = f"{self.base_url}/chat/completions"

        payload = self._format_request_payload(
            request
        )

        payload["stream"] = True

        headers = self._get_headers()

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout
            ) as client:

                async with client.stream(
                    "POST",
                    url,
                    json=payload,
                    headers=headers,
                ) as response:

                    if response.status_code == 401:
                        raise LLMAuthenticationError(
                            "OpenAI-compatible authentication "
                            f"failed: {response.text}"
                        )

                    if response.status_code == 429:
                        raise LLMRateLimitError(
                            "OpenAI-compatible rate limit "
                            f"exceeded: {response.text}"
                        )

                    if response.status_code >= 400:
                        raise LLMResponseError(
                            "OpenAI-compatible stream error "
                            f"({response.status_code}): "
                            f"{response.text}"
                        )

                    async for line in response.aiter_lines():

                        if not line.strip():
                            continue

                        # OpenAI-compatible streaming responses
                        # are Server-Sent Events:
                        #
                        # data: {...}
                        # data: [DONE]

                        if line.startswith("data:"):
                            line = line[
                                len("data:"):
                            ].strip()

                        if line == "[DONE]":
                            yield LLMStreamEvent(
                                content_delta="",
                                finish_reason="stop",
                            )
                            break

                        try:
                            chunk = json.loads(line)

                        except json.JSONDecodeError as exc:
                            raise LLMResponseError(
                                "Invalid JSON in "
                                f"OpenAI-compatible stream: "
                                f"{line}"
                            ) from exc

                        choices = chunk.get(
                            "choices",
                            [],
                        )

                        if not choices:
                            continue

                        choice = choices[0]

                        delta = choice.get(
                            "delta",
                            {},
                        )

                        content_delta = delta.get(
                            "content",
                            "",
                        )

                        finish_reason = choice.get(
                            "finish_reason"
                        )

                        yield LLMStreamEvent(
                            content_delta=content_delta,
                            finish_reason=finish_reason,
                        )

        except httpx.RequestError as exc:
            raise LLMConnectionError(
                "OpenAI-compatible streaming "
                f"connection error: {exc}"
            ) from exc