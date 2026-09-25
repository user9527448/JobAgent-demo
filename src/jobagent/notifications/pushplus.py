"""Credential-safe PushPlus adapter with no implicit submission retries."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Final

import httpx
from pydantic import SecretStr

from .contracts import (
    DeliveryFailureKind,
    DeliveryMessagePart,
    DeliveryProviderError,
    ProviderDeliveryResult,
    ProviderDeliveryStatus,
    ProviderSubmission,
)

PUSHPLUS_PROVIDER: Final = "pushplus"
PUSHPLUS_BASE_URL: Final = "https://www.pushplus.plus/"
PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS: Final = 13.0
_TRANSIENT_CODES: Final = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
_TRANSIENT_PROVIDER_CODES: Final = frozenset({408, 429, 500, 502, 503, 504})

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class PushPlusProviderConfig:
    """Secrets and transport bounds for the approved personal-WeChat channel."""

    token: SecretStr
    secret_key: SecretStr
    base_url: str = PUSHPLUS_BASE_URL
    timeout_seconds: float = 20.0
    min_submission_interval_seconds: float = PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS

    def __post_init__(self) -> None:
        if not self.token.get_secret_value().strip():
            raise ValueError("PushPlus token cannot be empty.")
        if not self.secret_key.get_secret_value().strip():
            raise ValueError("PushPlus secret key cannot be empty.")
        if self.timeout_seconds <= 0:
            raise ValueError("PushPlus timeout must be positive.")
        if self.min_submission_interval_seconds < PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS:
            raise ValueError("PushPlus submission interval must preserve the approved rate margin.")
        try:
            parsed = httpx.URL(self.base_url)
        except (TypeError, ValueError) as error:
            raise ValueError("PushPlus base URL must be valid.") from error
        if (
            parsed.scheme != "https"
            or not parsed.host
            or bool(parsed.username)
            or bool(parsed.password)
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        ):
            raise ValueError("PushPlus base URL must be a credential-free HTTPS origin.")


class PushPlusProvider:
    """Submit and reconcile PushPlus messages through an injected HTTP transport."""

    name = PUSHPLUS_PROVIDER

    def __init__(
        self,
        config: PushPlusProviderConfig,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        self._config = config
        self._sleep = sleep
        self._clock = clock
        self._submission_lock = asyncio.Lock()
        self._access_key_lock = asyncio.Lock()
        self._next_submission_at = 0.0
        self._access_key: str | None = None
        self._access_key_valid_until = 0.0
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(config.timeout_seconds),
            transport=transport,
            headers={"content-type": "application/json"},
        )

    async def __aenter__(self) -> PushPlusProvider:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP client."""
        await self._client.aclose()

    async def submit(self, part: DeliveryMessagePart) -> ProviderSubmission:
        """Submit one part exactly once; persistence owns any later retry decision."""
        await self._wait_for_submission_slot()
        payload = {
            "token": self._config.token.get_secret_value(),
            "title": part.title,
            "content": part.content,
            "template": "markdown",
            "channel": "wechat",
        }
        try:
            response = await self._client.post("send", json=payload)
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            raise DeliveryProviderError(
                "pushplus.submit_not_connected",
                kind=DeliveryFailureKind.TRANSIENT,
            ) from None
        except httpx.TransportError:
            raise DeliveryProviderError(
                "pushplus.submit_outcome_unknown",
                kind=DeliveryFailureKind.UNKNOWN,
            ) from None

        _raise_for_http(response.status_code, operation="submit")
        body = _response_object(response, ambiguous=True)
        code = _provider_code(body, ambiguous=True)
        if code != 200:
            _raise_for_provider_code(code, operation="submit")
        short_code = body.get("data")
        if not isinstance(short_code, str) or not short_code.strip():
            raise DeliveryProviderError(
                "pushplus.submit_outcome_unknown",
                kind=DeliveryFailureKind.UNKNOWN,
                provider_code=code,
            )
        return ProviderSubmission(provider_message_id=short_code)

    async def get_result(self, provider_message_id: str) -> ProviderDeliveryResult:
        """Query provider-final state without exposing the provider error message."""
        if not provider_message_id.strip():
            raise ValueError("PushPlus provider message ID cannot be empty.")
        access_key = await self._get_access_key()
        try:
            response = await self._client.get(
                "api/open/message/sendMessageResult",
                params={"shortCode": provider_message_id},
                headers={"access-key": access_key},
            )
        except httpx.TransportError:
            raise DeliveryProviderError(
                "pushplus.result_transport",
                kind=DeliveryFailureKind.TRANSIENT,
            ) from None
        _raise_for_http(response.status_code, operation="result")
        body = _response_object(response)
        code = _provider_code(body)
        if code != 200:
            _raise_for_provider_code(code, operation="result")
        data = body.get("data")
        if not isinstance(data, dict):
            raise _invalid_response("result", provider_code=code)
        status = data.get("status")
        if not isinstance(status, int) or isinstance(status, bool):
            raise _invalid_response("result", provider_code=code)
        if status == 0:
            return ProviderDeliveryResult(ProviderDeliveryStatus.PENDING)
        if status == 1:
            return ProviderDeliveryResult(ProviderDeliveryStatus.SENDING)
        if status == 2:
            return ProviderDeliveryResult(ProviderDeliveryStatus.SUCCEEDED)
        if status == 3:
            return ProviderDeliveryResult(
                ProviderDeliveryStatus.FAILED,
                error_code="pushplus.delivery_failed",
            )
        raise _invalid_response("result", provider_code=code)

    async def _get_access_key(self) -> str:
        async with self._access_key_lock:
            now = self._clock()
            if self._access_key is not None and now < self._access_key_valid_until:
                return self._access_key
            try:
                response = await self._client.post(
                    "api/common/openApi/getAccessKey",
                    json={
                        "token": self._config.token.get_secret_value(),
                        "secretKey": self._config.secret_key.get_secret_value(),
                    },
                )
            except httpx.TransportError:
                raise DeliveryProviderError(
                    "pushplus.access_key_transport",
                    kind=DeliveryFailureKind.TRANSIENT,
                ) from None
            _raise_for_http(response.status_code, operation="access_key")
            body = _response_object(response)
            code = _provider_code(body)
            if code != 200:
                _raise_for_provider_code(code, operation="access_key")
            data = body.get("data")
            if not isinstance(data, dict):
                raise _invalid_response("access_key", provider_code=code)
            access_key = data.get("accessKey")
            expires_in = data.get("expiresIn", data.get("expireIn"))
            if (
                not isinstance(access_key, str)
                or not access_key.strip()
                or not isinstance(expires_in, int)
                or isinstance(expires_in, bool)
                or expires_in <= 0
            ):
                raise _invalid_response("access_key", provider_code=code)
            refresh_margin = min(60.0, expires_in / 10)
            self._access_key = access_key
            self._access_key_valid_until = now + expires_in - refresh_margin
            return access_key

    async def _wait_for_submission_slot(self) -> None:
        async with self._submission_lock:
            delay = max(0.0, self._next_submission_at - self._clock())
            if delay > 0:
                await self._sleep(delay)
            self._next_submission_at = self._clock() + self._config.min_submission_interval_seconds


def _response_object(response: httpx.Response, *, ambiguous: bool = False) -> dict[str, object]:
    try:
        body = response.json()
    except ValueError:
        if ambiguous:
            raise DeliveryProviderError(
                "pushplus.submit_outcome_unknown",
                kind=DeliveryFailureKind.UNKNOWN,
                status_code=response.status_code,
            ) from None
        raise _invalid_response("response", status_code=response.status_code) from None
    if not isinstance(body, dict):
        if ambiguous:
            raise DeliveryProviderError(
                "pushplus.submit_outcome_unknown",
                kind=DeliveryFailureKind.UNKNOWN,
                status_code=response.status_code,
            )
        raise _invalid_response("response", status_code=response.status_code)
    return body


def _provider_code(body: dict[str, object], *, ambiguous: bool = False) -> int:
    code = body.get("code")
    if isinstance(code, int) and not isinstance(code, bool):
        return code
    if ambiguous:
        raise DeliveryProviderError(
            "pushplus.submit_outcome_unknown",
            kind=DeliveryFailureKind.UNKNOWN,
        )
    raise _invalid_response("response")


def _raise_for_http(status_code: int, *, operation: str) -> None:
    if 200 <= status_code < 300:
        return
    kind = (
        DeliveryFailureKind.TRANSIENT
        if status_code in _TRANSIENT_CODES or status_code >= 500
        else DeliveryFailureKind.PERMANENT
    )
    raise DeliveryProviderError(
        f"pushplus.{operation}_http_response",
        kind=kind,
        status_code=status_code,
    )


def _raise_for_provider_code(code: int, *, operation: str) -> None:
    kind = (
        DeliveryFailureKind.TRANSIENT
        if code in _TRANSIENT_PROVIDER_CODES
        else DeliveryFailureKind.PERMANENT
    )
    raise DeliveryProviderError(
        f"pushplus.{operation}_rejected",
        kind=kind,
        provider_code=code,
    )


def _invalid_response(
    operation: str,
    *,
    status_code: int | None = None,
    provider_code: int | None = None,
) -> DeliveryProviderError:
    return DeliveryProviderError(
        f"pushplus.{operation}_invalid_response",
        kind=DeliveryFailureKind.PERMANENT,
        status_code=status_code,
        provider_code=provider_code,
    )
