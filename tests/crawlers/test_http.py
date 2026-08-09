"""Deterministic checks for source-level HTTP access policy."""

from __future__ import annotations

import asyncio
from typing import cast

import httpx
import pytest

from jobagent.core.exceptions import (
    ConfigurationError,
    PermanentJobAgentError,
    TransientJobAgentError,
)
from jobagent.crawlers import HttpCacheValidators, HttpSourcePolicy, SourceHttpClient


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.value += delay


def _policy(
    *,
    source_id: int = 7,
    timeout_seconds: float = 4.0,
    min_interval_seconds: float = 0.0,
    max_concurrency: int = 1,
    max_attempts: int = 4,
    backoff_base_seconds: float = 0.25,
    backoff_max_seconds: float = 2.0,
) -> HttpSourcePolicy:
    return HttpSourcePolicy(
        source_id=source_id,
        user_agent="JOBAGENT/0.1 (+https://example.invalid/contact)",
        timeout_seconds=timeout_seconds,
        min_interval_seconds=min_interval_seconds,
        max_concurrency=max_concurrency,
        max_attempts=max_attempts,
        backoff_base_seconds=backoff_base_seconds,
        backoff_max_seconds=backoff_max_seconds,
    )


def test_429_5xx_and_transport_errors_retry_with_exponential_backoff() -> None:
    fake_time = FakeTime()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(429, request=request)
        if len(requests) == 2:
            return httpx.Response(503, request=request)
        if len(requests) == 3:
            raise httpx.ConnectError("temporary connection failure", request=request)
        return httpx.Response(200, text="ok", request=request)

    async def scenario() -> None:
        async with SourceHttpClient(
            _policy(),
            transport=httpx.MockTransport(handler),
            sleep=fake_time.sleep,
            clock=fake_time.monotonic,
        ) as client:
            result = await client.get("https://example.invalid/jobs")

        assert result.response.text == "ok"
        assert result.attempts == 4

    asyncio.run(scenario())

    assert fake_time.sleeps == [0.25, 0.5, 1.0]
    assert len(requests) == 4
    assert all(
        request.headers["user-agent"] == "JOBAGENT/0.1 (+https://example.invalid/contact)"
        for request in requests
    )


def test_non_retryable_4xx_fails_once_and_sanitizes_url() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404, request=request)

    async def scenario() -> None:
        async with SourceHttpClient(_policy(), transport=httpx.MockTransport(handler)) as client:
            with pytest.raises(PermanentJobAgentError) as captured_error:
                await client.get(
                    "https://user:secret@example.invalid/missing?token=sensitive#fragment"
                )

        assert captured_error.value.code == "crawler.http_permanent_response"
        assert captured_error.value.details == {
            "source_id": 7,
            "url": "https://example.invalid/missing",
            "attempts": 1,
            "status_code": 404,
        }

    asyncio.run(scenario())
    assert calls == 1


def test_retry_exhaustion_is_transient_and_records_attempts() -> None:
    fake_time = FakeTime()
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, request=request)

    async def scenario() -> None:
        async with SourceHttpClient(
            _policy(max_attempts=3),
            transport=httpx.MockTransport(handler),
            sleep=fake_time.sleep,
            clock=fake_time.monotonic,
        ) as client:
            with pytest.raises(TransientJobAgentError) as captured_error:
                await client.get("https://example.invalid/unstable")

        assert captured_error.value.code == "crawler.http_retry_exhausted"
        assert captured_error.value.details["attempts"] == 3
        assert captured_error.value.details["status_code"] == 500

    asyncio.run(scenario())

    assert calls == 3
    assert fake_time.sleeps == [0.25, 0.5]


def test_etag_and_last_modified_round_trip_through_a_304() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            assert "if-none-match" not in request.headers
            assert "if-modified-since" not in request.headers
            return httpx.Response(
                200,
                headers={
                    "ETag": '"revision-1"',
                    "Last-Modified": "Sun, 09 Aug 2026 08:00:00 GMT",
                },
                request=request,
            )
        assert request.headers["if-none-match"] == '"revision-1"'
        assert request.headers["if-modified-since"] == "Sun, 09 Aug 2026 08:00:00 GMT"
        return httpx.Response(304, request=request)

    async def scenario() -> None:
        async with SourceHttpClient(_policy(), transport=httpx.MockTransport(handler)) as client:
            first = await client.get("https://example.invalid/list")
            second = await client.get(
                "https://example.invalid/list",
                validators=first.validators,
            )

        assert first.validators == HttpCacheValidators(
            etag='"revision-1"',
            last_modified="Sun, 09 Aug 2026 08:00:00 GMT",
        )
        assert second.not_modified is True
        assert second.validators == first.validators

    asyncio.run(scenario())
    assert calls == 2


def test_source_instances_enforce_independent_timeout_and_rate_policy() -> None:
    slow_time = FakeTime()
    fast_time = FakeTime()
    observations: list[tuple[int, float]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        timeout = cast(dict[str, float], request.extensions["timeout"])
        observations.append((int(request.url.path.removeprefix("/")), timeout["read"]))
        return httpx.Response(200, request=request)

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)
        async with (
            SourceHttpClient(
                _policy(source_id=1, timeout_seconds=2.0, min_interval_seconds=3.0),
                transport=transport,
                sleep=slow_time.sleep,
                clock=slow_time.monotonic,
            ) as slow_client,
            SourceHttpClient(
                _policy(source_id=2, timeout_seconds=9.0, min_interval_seconds=0.0),
                transport=httpx.MockTransport(handler),
                sleep=fast_time.sleep,
                clock=fast_time.monotonic,
            ) as fast_client,
        ):
            await slow_client.get("https://example.invalid/1")
            await slow_client.get("https://example.invalid/1")
            await fast_client.get("https://example.invalid/2")
            await fast_client.get("https://example.invalid/2")

    asyncio.run(scenario())

    assert slow_time.sleeps == [3.0]
    assert fast_time.sleeps == []
    assert observations == [(1, 2.0), (1, 2.0), (2, 9.0), (2, 9.0)]


def test_concurrency_is_capped_per_source() -> None:
    active = 0
    max_active = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, request=request)

    async def scenario() -> None:
        async with SourceHttpClient(
            _policy(max_concurrency=2),
            transport=httpx.MockTransport(handler),
        ) as client:
            await asyncio.gather(
                *(client.get(f"https://example.invalid/{index}") for index in range(5))
            )

    asyncio.run(scenario())
    assert max_active == 2


def test_invalid_policy_fails_as_configuration_error() -> None:
    with pytest.raises(ConfigurationError) as captured_error:
        HttpSourcePolicy(source_id=7, user_agent=" ", max_concurrency=0)

    assert captured_error.value.code == "crawler.http_policy_invalid"
    fields = captured_error.value.details["fields"]
    assert isinstance(fields, dict)
    assert fields == {"user_agent": " ", "max_concurrency": 0}
