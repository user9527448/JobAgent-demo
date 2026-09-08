"""Provider-neutral contracts for deterministic, idempotent report delivery."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class DeliveryChannel(StrEnum):
    """Stable logical channels used by the delivery idempotency key."""

    PUSHPLUS_WECHAT = "pushplus_wechat"


class DeliveryFailureKind(StrEnum):
    """Safe provider-failure classes that control retry behavior."""

    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class ProviderDeliveryStatus(StrEnum):
    """Provider-confirmed state for an accepted message."""

    PENDING = "pending"
    SENDING = "sending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class DeliveryProviderError(Exception):
    """A credential-safe provider failure without raw response or transport text."""

    def __init__(
        self,
        code: str,
        *,
        kind: DeliveryFailureKind,
        status_code: int | None = None,
        provider_code: int | None = None,
    ) -> None:
        if not code.strip():
            raise ValueError("Delivery provider error code cannot be empty.")
        super().__init__(code)
        self.code = code
        self.kind = kind
        self.status_code = status_code
        self.provider_code = provider_code

    @property
    def retryable(self) -> bool:
        """Whether a caller may make another bounded submission attempt."""
        return self.kind is DeliveryFailureKind.TRANSIENT

    @property
    def ambiguous(self) -> bool:
        """Whether the provider may already have accepted the message."""
        return self.kind is DeliveryFailureKind.UNKNOWN


@dataclass(frozen=True, slots=True)
class DeliveryMessagePart:
    """One deterministic provider-sized part of an immutable report."""

    part_number: int
    part_count: int
    title: str
    content: str
    content_hash: str

    def __post_init__(self) -> None:
        if self.part_number <= 0 or self.part_count <= 0:
            raise ValueError("Delivery part numbers must be positive.")
        if self.part_number > self.part_count:
            raise ValueError("Delivery part number cannot exceed part count.")
        if not self.title.strip() or not self.content.strip():
            raise ValueError("Delivery part title and content cannot be empty.")
        _require_sha256(self.content_hash, "Delivery part content hash")
        if hashlib.sha256(self.content.encode()).hexdigest() != self.content_hash:
            raise ValueError("Delivery part content hash does not match its content.")


@dataclass(frozen=True, slots=True)
class DeliveryMessage:
    """Versioned deterministic message derived from one report snapshot."""

    report_snapshot_id: int
    report_content_hash: str
    channel: DeliveryChannel
    delivery_version: str
    message_hash: str
    parts: tuple[DeliveryMessagePart, ...]

    def __post_init__(self) -> None:
        if self.report_snapshot_id <= 0:
            raise ValueError("Delivery report snapshot ID must be positive.")
        _require_sha256(self.report_content_hash, "Report content hash")
        _require_sha256(self.message_hash, "Delivery message hash")
        if not self.delivery_version.strip():
            raise ValueError("Delivery version cannot be empty.")
        if not self.parts:
            raise ValueError("Delivery messages require at least one part.")
        expected_numbers = tuple(range(1, len(self.parts) + 1))
        if tuple(part.part_number for part in self.parts) != expected_numbers:
            raise ValueError("Delivery parts must be in contiguous one-based order.")
        if any(part.part_count != len(self.parts) for part in self.parts):
            raise ValueError("Delivery part counts must match the message part count.")


@dataclass(frozen=True, slots=True)
class ProviderSubmission:
    """Provider identifier returned after one accepted submission."""

    provider_message_id: str

    def __post_init__(self) -> None:
        if not self.provider_message_id.strip():
            raise ValueError("Provider message ID cannot be empty.")


@dataclass(frozen=True, slots=True)
class ProviderDeliveryResult:
    """Safe final-result projection; raw provider failure text is discarded."""

    status: ProviderDeliveryStatus
    error_code: str | None = None

    def __post_init__(self) -> None:
        if self.status is ProviderDeliveryStatus.FAILED and not self.error_code:
            raise ValueError("Failed provider results require a safe error code.")
        if self.status is not ProviderDeliveryStatus.FAILED and self.error_code is not None:
            raise ValueError("Only failed provider results may carry an error code.")


@dataclass(frozen=True, slots=True)
class DeliveryRetryPolicy:
    """Bounded submission policy approved by D-037."""

    max_attempts: int = 3
    delays_seconds: tuple[float, ...] = (30.0, 60.0)

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("Delivery retry attempts must be positive.")
        if len(self.delays_seconds) != self.max_attempts - 1:
            raise ValueError("Delivery retry delays must cover every retry.")
        if any(delay < 0 for delay in self.delays_seconds):
            raise ValueError("Delivery retry delays cannot be negative.")

    def delay_after(self, attempt: int) -> float:
        """Return the delay after a failed non-final attempt."""
        if attempt <= 0 or attempt >= self.max_attempts:
            raise ValueError("Delivery retry delay requires a non-final attempt number.")
        return self.delays_seconds[attempt - 1]


class DeliveryProvider(Protocol):
    """Replaceable asynchronous delivery provider boundary."""

    name: str

    async def submit(self, part: DeliveryMessagePart) -> ProviderSubmission:
        """Submit exactly once or raise a safe classified provider error."""

    async def get_result(self, provider_message_id: str) -> ProviderDeliveryResult:
        """Query an accepted message without resubmitting it."""


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{label} must be a lowercase SHA-256 hex string.")
