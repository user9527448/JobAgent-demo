"""Polite, observable HTTP access shared by source adapters."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from types import TracebackType
from urllib.parse import urlsplit, urlunsplit

import httpx

from jobagent.core.exceptions import (
    ConfigurationError,
    JsonValue,
    PermanentJobAgentError,
    TransientJobAgentError,
)
from jobagent.core.logging import get_logger

logger = get_logger(__name__)

Sleep = Callable[[float], Awaitable[None]]
Clock = Callable[[], float]


@dataclass(frozen=True, slots=True)
class HttpSourcePolicy:
    """Independent timeout, pacing and retry policy for one source."""

    source_id: int
    user_agent: str
    timeout_seconds: float = 20.0
    min_interval_seconds: float = 1.0
    max_concurrency: int = 1
    max_attempts: int = 3
    backoff_base_seconds: float = 0.5
    backoff_max_seconds: float = 8.0

    def __post_init__(self) -> None:
        invalid_fields: dict[str, JsonValue] = {}
        if self.source_id <= 0:
            invalid_fields["source_id"] = self.source_id
        if not self.user_agent.strip():
            invalid_fields["user_agent"] = self.user_agent
        if self.timeout_seconds <= 0:
            invalid_fields["timeout_seconds"] = self.timeout_seconds
        if self.min_interval_seconds < 0:
            invalid_fields["min_interval_seconds"] = self.min_interval_seconds
        if self.max_concurrency <= 0:
            invalid_fields["max_concurrency"] = self.max_concurrency
        if self.max_attempts <= 0:
            invalid_fields["max_attempts"] = self.max_attempts
        if self.backoff_base_seconds < 0:
            invalid_fields["backoff_base_seconds"] = self.backoff_base_seconds
        if self.backoff_max_seconds < self.backoff_base_seconds:
            invalid_fields["backoff_max_seconds"] = self.backoff_max_seconds
        if invalid_fields:
            raise ConfigurationError(
                "Source HTTP policy is invalid.",
                code="crawler.http_policy_invalid",
                details={"fields": invalid_fields},
            )


@dataclass(frozen=True, slots=True)
class HttpCacheValidators:
    """Conditional request validators retained from a previous response."""

    etag: str | None = None
    last_modified: str | None = None

    def request_headers(self) -> dict[str, str]:
        """Render validators as standard conditional request headers."""
        headers: dict[str, str] = {}
        if self.etag is not None:
            headers["If-None-Match"] = self.etag
        if self.last_modified is not None:
            headers["If-Modified-Since"] = self.last_modified
        return headers

    def updated(self, headers: Mapping[str, str]) -> HttpCacheValidators:
        """Return response validators while retaining values omitted by a 304."""
        return HttpCacheValidators(
            etag=headers.get("etag", self.etag),
            last_modified=headers.get("last-modified", self.last_modified),
        )


@dataclass(frozen=True, slots=True)
class HttpFetchResult:
    """A successful response plus retry and conditional-cache metadata."""

    response: httpx.Response
    attempts: int
    validators: HttpCacheValidators

    @property
    def not_modified(self) -> bool:
        """Whether the origin confirmed that cached content is still current."""
        return self.response.status_code == httpx.codes.NOT_MODIFIED


class SourceHttpClient:
    """Apply one source's access policy to all asynchronous GET requests."""

    def __init__(
        self,
        policy: HttpSourcePolicy,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        sleep: Sleep = asyncio.sleep,
        clock: Clock = time.monotonic,
    ) -> None:
        self.policy = policy
        self._sleep = sleep
        self._clock = clock
        self._semaphore = asyncio.Semaphore(policy.max_concurrency)
        self._rate_lock = asyncio.Lock()
        self._next_request_at = 0.0
        self._client = httpx.AsyncClient(
            headers={"User-Agent": policy.user_agent},
            timeout=httpx.Timeout(policy.timeout_seconds),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=policy.max_concurrency,
                max_keepalive_connections=policy.max_concurrency,
            ),
            transport=transport,
        )

    async def __aenter__(self) -> SourceHttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close pooled connections and the underlying transport."""
        await self._client.aclose()

    async def get(
        self,
        url: str,
        *,
        validators: HttpCacheValidators | None = None,
    ) -> HttpFetchResult:
        """GET a URL with source-level pacing, retry and cache validation."""
        safe_url = _safe_url(url)
        request_validators = validators or HttpCacheValidators()
        headers = request_validators.request_headers()

        for attempt in range(1, self.policy.max_attempts + 1):
            logger.info(
                "http.request.attempt",
                extra={
                    "source_id": self.policy.source_id,
                    "url": safe_url,
                    "attempt": attempt,
                    "max_attempts": self.policy.max_attempts,
                },
            )
            try:
                async with self._semaphore:
                    await self._wait_for_rate_slot()
                    response = await self._client.get(url, headers=headers)
            except httpx.InvalidURL as error:
                raise PermanentJobAgentError(
                    "Source URL is invalid.",
                    code="crawler.http_invalid_url",
                    details={"source_id": self.policy.source_id, "url": safe_url},
                ) from error
            except httpx.TransportError as error:
                if attempt == self.policy.max_attempts:
                    raise _retry_exhausted(
                        self.policy,
                        safe_url,
                        attempts=attempt,
                        error_type=type(error).__name__,
                    ) from error
                await self._wait_before_retry(
                    attempt,
                    safe_url,
                    reason=type(error).__name__,
                )
                continue

            if response.is_success or response.status_code == httpx.codes.NOT_MODIFIED:
                logger.info(
                    "http.request.completed",
                    extra={
                        "source_id": self.policy.source_id,
                        "url": safe_url,
                        "attempts": attempt,
                        "status_code": response.status_code,
                    },
                )
                return HttpFetchResult(
                    response=response,
                    attempts=attempt,
                    validators=request_validators.updated(response.headers),
                )

            if response.status_code == httpx.codes.TOO_MANY_REQUESTS or response.is_server_error:
                if attempt == self.policy.max_attempts:
                    raise _retry_exhausted(
                        self.policy,
                        safe_url,
                        attempts=attempt,
                        status_code=response.status_code,
                    )
                await self._wait_before_retry(
                    attempt,
                    safe_url,
                    reason=f"http_{response.status_code}",
                    status_code=response.status_code,
                )
                continue

            raise PermanentJobAgentError(
                "Source returned a non-retryable HTTP response.",
                code="crawler.http_permanent_response",
                details={
                    "source_id": self.policy.source_id,
                    "url": safe_url,
                    "attempts": attempt,
                    "status_code": response.status_code,
                },
            )

        raise AssertionError("HTTP retry loop exited without a result.")

    async def _wait_for_rate_slot(self) -> None:
        async with self._rate_lock:
            delay = max(0.0, self._next_request_at - self._clock())
            if delay > 0:
                await self._sleep(delay)
            self._next_request_at = self._clock() + self.policy.min_interval_seconds

    async def _wait_before_retry(
        self,
        attempt: int,
        safe_url: str,
        *,
        reason: str,
        status_code: int | None = None,
    ) -> None:
        delay = min(
            self.policy.backoff_base_seconds * (2 ** (attempt - 1)),
            self.policy.backoff_max_seconds,
        )
        logger.warning(
            "http.request.retrying",
            extra={
                "source_id": self.policy.source_id,
                "url": safe_url,
                "attempt": attempt,
                "reason": reason,
                "status_code": status_code,
                "delay_seconds": delay,
            },
        )
        await self._sleep(delay)


def _retry_exhausted(
    policy: HttpSourcePolicy,
    safe_url: str,
    *,
    attempts: int,
    status_code: int | None = None,
    error_type: str | None = None,
) -> TransientJobAgentError:
    details: dict[str, JsonValue] = {
        "source_id": policy.source_id,
        "url": safe_url,
        "attempts": attempts,
    }
    if status_code is not None:
        details["status_code"] = status_code
    if error_type is not None:
        details["error_type"] = error_type
    return TransientJobAgentError(
        "Source HTTP request exhausted its retry policy.",
        code="crawler.http_retry_exhausted",
        details=details,
    )


def _safe_url(url: str) -> str:
    parsed = urlsplit(url)
    netloc = parsed.netloc.rsplit("@", 1)[-1]
    return urlunsplit((parsed.scheme, netloc, parsed.path, "", ""))
