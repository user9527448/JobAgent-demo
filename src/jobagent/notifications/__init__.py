"""Deterministic report delivery contracts and provider adapters."""

from .contracts import (
    DeliveryChannel,
    DeliveryFailureKind,
    DeliveryMessage,
    DeliveryMessagePart,
    DeliveryProvider,
    DeliveryProviderError,
    DeliveryRetryPolicy,
    ProviderDeliveryResult,
    ProviderDeliveryStatus,
    ProviderSubmission,
)
from .pushplus import (
    PUSHPLUS_BASE_URL,
    PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS,
    PUSHPLUS_PROVIDER,
    PushPlusProvider,
    PushPlusProviderConfig,
)
from .rendering import (
    CURRENT_DELIVERY_VERSION,
    PUSHPLUS_BODY_CHAR_LIMIT,
    PUSHPLUS_TITLE_CHAR_LIMIT,
    DeterministicDeliveryRenderer,
)

__all__ = [
    "CURRENT_DELIVERY_VERSION",
    "PUSHPLUS_BASE_URL",
    "PUSHPLUS_BODY_CHAR_LIMIT",
    "PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS",
    "PUSHPLUS_PROVIDER",
    "PUSHPLUS_TITLE_CHAR_LIMIT",
    "DeliveryChannel",
    "DeliveryFailureKind",
    "DeliveryMessage",
    "DeliveryMessagePart",
    "DeliveryProvider",
    "DeliveryProviderError",
    "DeliveryRetryPolicy",
    "DeterministicDeliveryRenderer",
    "ProviderDeliveryResult",
    "ProviderDeliveryStatus",
    "ProviderSubmission",
    "PushPlusProvider",
    "PushPlusProviderConfig",
]
