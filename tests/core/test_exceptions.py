"""Tests for machine-readable domain exceptions."""

from jobagent.core.exceptions import TransientJobAgentError


def test_transient_error_is_retryable_and_serializable() -> None:
    error = TransientJobAgentError(
        "The source temporarily rejected the request.",
        code="crawler.rate_limited",
        details={"source_id": 42},
    )

    assert error.retryable is True
    assert error.to_dict() == {
        "code": "crawler.rate_limited",
        "message": "The source temporarily rejected the request.",
        "category": "transient",
        "retryable": True,
        "details": {"source_id": 42},
    }
