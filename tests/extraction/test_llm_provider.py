"""Mock-transport tests for configurable LLM providers."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from jobagent.core.exceptions import ConfigurationError
from jobagent.extraction import (
    LlmProviderConfig,
    LlmProviderError,
    LlmProviderRequest,
    LlmProviderResponse,
    LlmUsage,
    OpenAIResponsesProvider,
    build_llm_provider,
)


def _request() -> LlmProviderRequest:
    return LlmProviderRequest(
        model="configured-model",
        prompt_version="prompt-v7",
        instructions="Return evidenced fields only.",
        input_text="招聘人数: 10人",
        output_schema={"type": "object", "additionalProperties": False},
        max_output_tokens=256,
    )


def _config() -> LlmProviderConfig:
    return LlmProviderConfig(
        name="openai_responses",
        api_key=SecretStr("test-key-never-log"),
        base_url="https://llm.example.invalid/v1",
        timeout_seconds=2,
    )


def test_openai_responses_request_uses_strict_schema_and_records_usage() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(
            200,
            json={
                "output_text": '{"candidates":[]}',
                "usage": {"input_tokens": 12, "output_tokens": 4, "total_tokens": 16},
            },
            request=request,
        )

    async def scenario() -> LlmProviderResponse:
        async with OpenAIResponsesProvider(
            _config(), transport=httpx.MockTransport(handler)
        ) as provider:
            return await provider.complete(_request())

    response = asyncio.run(scenario())

    assert response.output_text == '{"candidates":[]}'
    assert response.usage == LlmUsage(input_tokens=12, output_tokens=4, total_tokens=16)
    assert len(captured) == 1
    body = json.loads(captured[0].content)
    assert body["model"] == "configured-model"
    assert body["max_output_tokens"] == 256
    assert body["text"]["format"] == {
        "type": "json_schema",
        "name": "jobagent_llm_extraction",
        "strict": True,
        "schema": {"type": "object", "additionalProperties": False},
    }
    assert captured[0].headers["authorization"] == "Bearer test-key-never-log"


def test_openai_responses_reads_nested_output_and_rejects_missing_usage() -> None:
    responses = [
        {
            "output": [{"content": [{"type": "output_text", "text": '{"candidates":[]}'}]}],
            "usage": {"input_tokens": 7, "output_tokens": 3, "total_tokens": 10},
        },
        {"output_text": '{"candidates":[]}'},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=responses.pop(0), request=request)

    async def scenario() -> None:
        async with OpenAIResponsesProvider(
            _config(), transport=httpx.MockTransport(handler)
        ) as provider:
            first = await provider.complete(_request())
            assert first.output_text == '{"candidates":[]}'
            with pytest.raises(LlmProviderError) as captured:
                await provider.complete(_request())
            assert captured.value.code == "llm.provider_missing_usage"
            assert captured.value.retryable is False

    asyncio.run(scenario())


def test_openai_responses_sanitizes_transport_and_malformed_success_failures() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("credential-bearing transport detail", request=request)
        if calls == 2:
            return httpx.Response(200, content=b"not-json", request=request)
        return httpx.Response(200, json=[], request=request)

    async def scenario() -> None:
        async with OpenAIResponsesProvider(
            _config(), transport=httpx.MockTransport(handler)
        ) as provider:
            with pytest.raises(LlmProviderError) as transport_error:
                await provider.complete(_request())
            assert transport_error.value.code == "llm.provider_transport"
            assert transport_error.value.retryable is True
            assert "credential-bearing" not in str(transport_error.value)

            for _ in range(2):
                with pytest.raises(LlmProviderError) as malformed:
                    await provider.complete(_request())
                assert malformed.value.code == "llm.provider_invalid_response"
                assert malformed.value.retryable is False

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status_code", "retryable"),
    [(400, False), (408, True), (429, True), (503, True)],
)
def test_openai_responses_classifies_safe_http_failures(status_code: int, retryable: bool) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            text="sensitive provider response must not escape",
            request=request,
        )

    async def scenario() -> None:
        async with OpenAIResponsesProvider(
            _config(), transport=httpx.MockTransport(handler)
        ) as provider:
            with pytest.raises(LlmProviderError) as captured:
                await provider.complete(_request())
        assert captured.value.retryable is retryable
        assert captured.value.status_code == status_code
        assert "sensitive" not in str(captured.value)

    asyncio.run(scenario())


def test_provider_builder_supports_configured_replacement_and_safe_errors() -> None:
    class ReplacementProvider:
        name = "replacement"

        async def complete(self, request: LlmProviderRequest) -> LlmProviderResponse:
            return LlmProviderResponse('{"candidates":[]}', LlmUsage())

    replacement = ReplacementProvider()
    configured = build_llm_provider(
        LlmProviderConfig(name="replacement"),
        factories={"replacement": lambda config: replacement},
    )
    assert configured is replacement

    with pytest.raises(ConfigurationError) as captured:
        build_llm_provider(LlmProviderConfig(name="not-registered"))
    assert captured.value.code == "llm.provider_not_registered"

    with pytest.raises(ConfigurationError) as missing_key:
        build_llm_provider(LlmProviderConfig(name="openai_responses"))
    assert missing_key.value.code == "llm.provider_missing_api_key"


@pytest.mark.parametrize(
    ("name", "base_url", "timeout_seconds"),
    [
        ("", "https://example.invalid", 1.0),
        ("provider", "https://example.invalid", 0.0),
        ("provider", "http://insecure.example.invalid", 1.0),
        ("provider", "not a URL", 1.0),
    ],
)
def test_provider_config_rejects_empty_or_insecure_connections(
    name: str, base_url: str, timeout_seconds: float
) -> None:
    with pytest.raises(ValueError):
        LlmProviderConfig(name=name, base_url=base_url, timeout_seconds=timeout_seconds)
