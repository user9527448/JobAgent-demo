"""Configurable LLM provider construction and an OpenAI Responses adapter."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Final, TypeAlias, cast

import httpx
from pydantic import SecretStr

from jobagent.core.exceptions import ConfigurationError, JsonValue
from jobagent.extraction.llm_contracts import (
    LlmProvider,
    LlmProviderRequest,
    LlmProviderResponse,
    LlmUsage,
)

OPENAI_RESPONSES_PROVIDER: Final = "openai_responses"


class LlmProviderError(Exception):
    """Safe provider failure with explicit retry behavior and no response body."""

    def __init__(self, code: str, *, retryable: bool, status_code: int | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class LlmProviderConfig:
    """Connection configuration independent from prompt and budget policy."""

    name: str
    api_key: SecretStr | None = None
    base_url: str = "https://api.openai.com/v1"
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("LLM provider name cannot be empty.")
        if self.timeout_seconds <= 0:
            raise ValueError("LLM provider timeout must be positive.")
        try:
            parsed_url = httpx.URL(self.base_url)
        except (TypeError, ValueError) as error:
            raise ValueError("LLM provider base URL must be valid.") from error
        if parsed_url.scheme != "https" or not parsed_url.host:
            raise ValueError("LLM provider base URL must use HTTPS.")


class OpenAIResponsesProvider:
    """OpenAI-compatible Responses API adapter using strict JSON Schema output."""

    name = OPENAI_RESPONSES_PROVIDER

    def __init__(
        self,
        config: LlmProviderConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if config.api_key is None or not config.api_key.get_secret_value().strip():
            raise ConfigurationError(
                "The OpenAI Responses provider requires an API key.",
                code="llm.provider_missing_api_key",
            )
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(config.timeout_seconds),
            transport=transport,
            headers={
                "authorization": f"Bearer {config.api_key.get_secret_value()}",
                "content-type": "application/json",
            },
        )

    async def __aenter__(self) -> OpenAIResponsesProvider:
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP client."""
        await self._client.aclose()

    async def complete(self, request: LlmProviderRequest) -> LlmProviderResponse:
        """Make one Responses API attempt; retry orchestration belongs to the service."""
        payload: dict[str, JsonValue] = {
            "model": request.model,
            "instructions": request.instructions,
            "input": request.input_text,
            "max_output_tokens": request.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "jobagent_llm_extraction",
                    "strict": True,
                    "schema": cast(JsonValue, request.output_schema),
                }
            },
        }
        try:
            response = await self._client.post("responses", json=payload)
        except httpx.TimeoutException as error:
            raise LlmProviderError("llm.provider_timeout", retryable=True) from error
        except httpx.TransportError as error:
            raise LlmProviderError("llm.provider_transport", retryable=True) from error

        if not response.is_success:
            retryable = response.status_code in {408, 409, 429} or response.is_server_error
            raise LlmProviderError(
                "llm.provider_retryable_response"
                if retryable
                else "llm.provider_permanent_response",
                retryable=retryable,
                status_code=response.status_code,
            )
        try:
            body = response.json()
        except ValueError as error:
            raise LlmProviderError("llm.provider_invalid_response", retryable=False) from error
        if not isinstance(body, dict):
            raise LlmProviderError("llm.provider_invalid_response", retryable=False)
        output_text = _response_output_text(body)
        usage = _response_usage(body)
        return LlmProviderResponse(output_text=output_text, usage=usage)


ProviderFactory: TypeAlias = Callable[[LlmProviderConfig], LlmProvider]


def build_llm_provider(
    config: LlmProviderConfig,
    *,
    factories: Mapping[str, ProviderFactory] | None = None,
) -> LlmProvider:
    """Build the configured provider while allowing deployment-specific replacements."""
    available: dict[str, ProviderFactory] = {
        OPENAI_RESPONSES_PROVIDER: OpenAIResponsesProvider,
    }
    if factories is not None:
        available.update(factories)
    factory = available.get(config.name)
    if factory is None:
        raise ConfigurationError(
            "The configured LLM provider is not registered.",
            code="llm.provider_not_registered",
            details={"provider": config.name},
        )
    return factory(config)


def _response_output_text(body: dict[str, object]) -> str:
    direct = body.get("output_text")
    if isinstance(direct, str) and direct.strip():
        return direct
    output = body.get("output")
    if not isinstance(output, list):
        raise LlmProviderError("llm.provider_missing_output", retryable=False)
    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if not isinstance(part, dict):
                continue
            text = part.get("text")
            if isinstance(text, str) and text:
                parts.append(text)
    result = "".join(parts)
    if not result.strip():
        raise LlmProviderError("llm.provider_missing_output", retryable=False)
    return result


def _response_usage(body: dict[str, object]) -> LlmUsage:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        raise LlmProviderError("llm.provider_missing_usage", retryable=False)
    values: list[int] = []
    for key in ("input_tokens", "output_tokens", "total_tokens"):
        value = usage.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise LlmProviderError("llm.provider_invalid_usage", retryable=False)
        values.append(value)
    try:
        return LlmUsage(*values)
    except ValueError as error:
        raise LlmProviderError("llm.provider_invalid_usage", retryable=False) from error
