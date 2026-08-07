"""Domain-level exceptions shared by all JOBAGENT modules."""

from enum import StrEnum
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]


class ErrorCategory(StrEnum):
    """Stable categories used to decide whether an operation can be retried."""

    CONFIGURATION = "configuration"
    TRANSIENT = "transient"
    PERMANENT = "permanent"


class JobAgentError(Exception):
    """Base exception with a machine-readable code and retry policy."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        category: ErrorCategory,
        retryable: bool,
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.category = category
        self.retryable = retryable
        self.details = details or {}

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a safe payload suitable for logs and API error responses."""
        return {
            "code": self.code,
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "details": self.details,
        }


class ConfigurationError(JobAgentError):
    """Raised when required application configuration is missing or invalid."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "configuration.invalid",
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            category=ErrorCategory.CONFIGURATION,
            retryable=False,
            details=details,
        )


class TransientJobAgentError(JobAgentError):
    """Raised for temporary failures that callers may retry."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            category=ErrorCategory.TRANSIENT,
            retryable=True,
            details=details,
        )


class PermanentJobAgentError(JobAgentError):
    """Raised for failures that require input, code, or source changes."""

    def __init__(
        self,
        message: str,
        *,
        code: str,
        details: dict[str, JsonValue] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            category=ErrorCategory.PERMANENT,
            retryable=False,
            details=details,
        )
