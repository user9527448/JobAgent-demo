"""Offline MockTransport checks for the credential-safe PushPlus adapter."""

from __future__ import annotations

import asyncio
import hashlib
import json

import httpx
import pytest
from pydantic import SecretStr

from jobagent.notifications import (
    DeliveryFailureKind,
    DeliveryMessagePart,
    DeliveryProviderError,
    ProviderDeliveryStatus,
    PushPlusProvider,
    PushPlusProviderConfig,
)

TEST_TOKEN = "synthetic-user-token"
TEST_SECRET = "synthetic-secret-key"
TEST_ACCESS_KEY = "synthetic-access-key"


class FakeTime:
    def __init__(self) -> None:
        self.value = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.value

    async def sleep(self, delay: float) -> None:
        self.sleeps.append(delay)
        self.value += delay


def test_submit_and_final_result_use_documented_shapes_without_url_secrets() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        if request.url.path == "/send":
            return httpx.Response(
                200,
                json={"code": 200, "msg": "accepted", "data": "synthetic-short-code"},
                request=request,
            )
        if request.url.path == "/api/common/openApi/getAccessKey":
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {"accessKey": TEST_ACCESS_KEY, "expiresIn": 7200},
                },
                request=request,
            )
        assert request.url.path == "/api/open/message/sendMessageResult"
        return httpx.Response(
            200,
            json={"code": 200, "data": {"status": 2, "errorMessage": ""}},
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            submission = await provider.submit(_part())
            first = await provider.get_result(submission.provider_message_id)
            second = await provider.get_result(submission.provider_message_id)
        assert submission.provider_message_id == "synthetic-short-code"
        assert first.status is ProviderDeliveryStatus.SUCCEEDED
        assert second == first

    asyncio.run(scenario())

    assert [request.url.path for request in captured] == [
        "/send",
        "/api/common/openApi/getAccessKey",
        "/api/open/message/sendMessageResult",
        "/api/open/message/sendMessageResult",
    ]
    send_body = json.loads(captured[0].content)
    assert send_body == {
        "token": TEST_TOKEN,
        "title": "JOBAGENT 日报 2026-09-08 [1/1]",
        "content": "# 合成日报\n",
        "template": "markdown",
        "channel": "wechat",
    }
    access_body = json.loads(captured[1].content)
    assert access_body == {"token": TEST_TOKEN, "secretKey": TEST_SECRET}
    assert captured[2].headers["access-key"] == TEST_ACCESS_KEY
    assert captured[2].url.params["shortCode"] == "synthetic-short-code"
    assert all(TEST_TOKEN not in str(request.url) for request in captured)
    assert all(TEST_SECRET not in str(request.url) for request in captured)


def test_provider_discards_raw_final_failure_reason() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("getAccessKey"):
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {"accessKey": TEST_ACCESS_KEY, "expiresIn": 120},
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "status": 3,
                    "errorMessage": f"raw failure containing {TEST_TOKEN} and {TEST_SECRET}",
                },
            },
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            result = await provider.get_result("synthetic-short-code")
        assert result.status is ProviderDeliveryStatus.FAILED
        assert result.error_code == "pushplus.delivery_failed"
        assert TEST_TOKEN not in repr(result)
        assert TEST_SECRET not in repr(result)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (0, ProviderDeliveryStatus.PENDING),
        (1, ProviderDeliveryStatus.SENDING),
        (2, ProviderDeliveryStatus.SUCCEEDED),
    ],
)
def test_provider_maps_each_non_failure_final_status(
    status: int,
    expected: ProviderDeliveryStatus,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("getAccessKey"):
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {"accessKey": TEST_ACCESS_KEY, "expiresIn": 120},
                },
                request=request,
            )
        return httpx.Response(
            200,
            json={"code": 200, "data": {"status": status}},
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            result = await provider.get_result("synthetic-short-code")
        assert result.status is expected

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("failure", "expected_kind", "expected_code"),
    [
        (
            httpx.ConnectError("raw synthetic credential transport detail"),
            DeliveryFailureKind.TRANSIENT,
            "pushplus.submit_not_connected",
        ),
        (
            httpx.ReadTimeout("raw synthetic credential transport detail"),
            DeliveryFailureKind.UNKNOWN,
            "pushplus.submit_outcome_unknown",
        ),
    ],
)
def test_submit_transport_failures_are_safe_and_conservative(
    failure: httpx.TransportError,
    expected_kind: DeliveryFailureKind,
    expected_code: str,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        failure.request = request
        raise failure

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            with pytest.raises(DeliveryProviderError) as captured:
                await provider.submit(_part())
        assert captured.value.kind is expected_kind
        assert captured.value.code == expected_code
        assert "credential" not in str(captured.value)
        assert captured.value.__cause__ is None

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("status_code", "kind"),
    [
        (400, DeliveryFailureKind.PERMANENT),
        (408, DeliveryFailureKind.TRANSIENT),
        (429, DeliveryFailureKind.TRANSIENT),
        (503, DeliveryFailureKind.TRANSIENT),
    ],
)
def test_submit_classifies_http_failures_without_response_content(
    status_code: int,
    kind: DeliveryFailureKind,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code,
            text=f"raw response containing {TEST_TOKEN} and {TEST_SECRET}",
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            with pytest.raises(DeliveryProviderError) as captured:
                await provider.submit(_part())
        assert captured.value.kind is kind
        assert captured.value.status_code == status_code
        assert TEST_TOKEN not in str(captured.value)
        assert TEST_SECRET not in str(captured.value)

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "body",
    [
        b"not-json",
        json.dumps({"code": 200, "data": ""}).encode(),
        json.dumps({"unexpected": True}).encode(),
    ],
)
def test_malformed_successful_submission_is_unknown_not_retryable(body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body, request=request)

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            with pytest.raises(DeliveryProviderError) as captured:
                await provider.submit(_part())
        assert captured.value.kind is DeliveryFailureKind.UNKNOWN
        assert captured.value.retryable is False
        assert captured.value.ambiguous is True

    asyncio.run(scenario())


@pytest.mark.parametrize(
    ("provider_code", "kind"),
    [
        (503, DeliveryFailureKind.TRANSIENT),
        (900, DeliveryFailureKind.PERMANENT),
        (905, DeliveryFailureKind.PERMANENT),
        (999, DeliveryFailureKind.PERMANENT),
    ],
)
def test_provider_rejection_codes_use_a_narrow_retry_allowlist(
    provider_code: int,
    kind: DeliveryFailureKind,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": provider_code,
                "msg": f"raw response containing {TEST_TOKEN} and {TEST_SECRET}",
            },
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
        ) as provider:
            with pytest.raises(DeliveryProviderError) as captured:
                await provider.submit(_part())
        assert captured.value.kind is kind
        assert captured.value.provider_code == provider_code
        assert TEST_TOKEN not in str(captured.value)
        assert TEST_SECRET not in str(captured.value)

    asyncio.run(scenario())


def test_submission_rate_margin_is_enforced_without_real_sleep() -> None:
    fake_time = FakeTime()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"code": 200, "data": "synthetic-short-code"},
            request=request,
        )

    async def scenario() -> None:
        async with PushPlusProvider(
            _config(),
            transport=httpx.MockTransport(handler),
            sleep=fake_time.sleep,
            clock=fake_time.monotonic,
        ) as provider:
            await provider.submit(_part())
            await provider.submit(_part())

    asyncio.run(scenario())
    assert fake_time.sleeps == [13.0]


@pytest.mark.parametrize(
    "base_url",
    [
        "http://pushplus.example.invalid",
        "https://identity:credential@pushplus.example.invalid",
        "https://pushplus.example.invalid?query=value",
        "https://pushplus.example.invalid/base/",
    ],
)
def test_config_rejects_insecure_or_credential_bearing_origins(base_url: str) -> None:
    with pytest.raises(ValueError, match="credential-free HTTPS origin"):
        _config(base_url=base_url)


def _config(*, base_url: str = "https://pushplus.example.invalid/") -> PushPlusProviderConfig:
    return PushPlusProviderConfig(
        token=SecretStr(TEST_TOKEN),
        secret_key=SecretStr(TEST_SECRET),
        base_url=base_url,
    )


def _part() -> DeliveryMessagePart:
    content = "# 合成日报\n"
    return DeliveryMessagePart(
        part_number=1,
        part_count=1,
        title="JOBAGENT 日报 2026-09-08 [1/1]",
        content=content,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
