"""Deterministic report delivery contracts and provider adapters."""

from .contracts import (
    DeliveryAttemptSnapshot,
    DeliveryAttemptStatus,
    DeliveryChannel,
    DeliveryDispatchStatus,
    DeliveryExecutionResult,
    DeliveryFailureKind,
    DeliveryMessage,
    DeliveryMessagePart,
    DeliveryOperations,
    DeliveryProvider,
    DeliveryProviderError,
    DeliveryRetryPolicy,
    DeliverySnapshot,
    DeliveryStatus,
    ProviderDeliveryResult,
    ProviderDeliveryStatus,
    ProviderSubmission,
)
from .persistence import SqlAlchemyDeliveryLock, SqlAlchemyDeliveryRepository
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
from .runtime import build_pushplus_delivery_service
from .service import DeliveryServicePolicy, SqlAlchemyNotificationDeliveryService

__all__ = [
    "CURRENT_DELIVERY_VERSION",
    "PUSHPLUS_BASE_URL",
    "PUSHPLUS_BODY_CHAR_LIMIT",
    "PUSHPLUS_MIN_SUBMISSION_INTERVAL_SECONDS",
    "PUSHPLUS_PROVIDER",
    "PUSHPLUS_TITLE_CHAR_LIMIT",
    "DeliveryAttemptSnapshot",
    "DeliveryAttemptStatus",
    "DeliveryChannel",
    "DeliveryDispatchStatus",
    "DeliveryExecutionResult",
    "DeliveryFailureKind",
    "DeliveryMessage",
    "DeliveryMessagePart",
    "DeliveryOperations",
    "DeliveryProvider",
    "DeliveryProviderError",
    "DeliveryRetryPolicy",
    "DeliveryServicePolicy",
    "DeliverySnapshot",
    "DeliveryStatus",
    "DeterministicDeliveryRenderer",
    "ProviderDeliveryResult",
    "ProviderDeliveryStatus",
    "ProviderSubmission",
    "PushPlusProvider",
    "PushPlusProviderConfig",
    "SqlAlchemyDeliveryLock",
    "SqlAlchemyDeliveryRepository",
    "SqlAlchemyNotificationDeliveryService",
    "build_pushplus_delivery_service",
]
