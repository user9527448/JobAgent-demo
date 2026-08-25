"""JAI-020 reparse API contract checks."""

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core import PermanentJobAgentError
from jobagent.core.config import Settings
from jobagent.extraction import (
    ExtractionWriteResult,
    ExtractionWriteStatus,
    ReviewStatus,
)


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


class FakeReparseService:
    def __init__(self, error: PermanentJobAgentError | None = None) -> None:
        self.error = error
        self.requests: list[tuple[int, str]] = []

    async def reparse(self, document_id: int, extraction_version: str) -> ExtractionWriteResult:
        self.requests.append((document_id, extraction_version))
        if self.error is not None:
            raise self.error
        return ExtractionWriteResult(
            post_id=23,
            position_ids=(41, 42),
            version=2,
            extraction_version=extraction_version,
            result_hash="a" * 64,
            status=ExtractionWriteStatus.UNCHANGED,
            previous_post_id=12,
            review_status=ReviewStatus.APPROVED,
            recommendation_eligible=True,
            validation_version="validation-v1",
            validation_error_count=0,
            validation_warning_count=0,
        )


def test_reparse_endpoint_returns_persisted_validation_outcome() -> None:
    service = FakeReparseService()
    with TestClient(create_app(_settings(), FakeDatabase(), service)) as client:
        response = client.post(
            "/extraction/documents/19/reparse",
            json={"extraction_version": "rules-2026.08.25"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "post_id": 23,
        "position_ids": [41, 42],
        "version": 2,
        "extraction_version": "rules-2026.08.25",
        "result_hash": "a" * 64,
        "write_status": "unchanged",
        "previous_post_id": 12,
        "review_status": "approved",
        "recommendation_eligible": True,
        "validation_version": "validation-v1",
        "validation_error_count": 0,
        "validation_warning_count": 0,
    }
    assert service.requests == [(19, "rules-2026.08.25")]


def test_reparse_endpoint_maps_missing_document_to_404() -> None:
    service = FakeReparseService(
        PermanentJobAgentError(
            "Missing.",
            code="reparse.document_not_found",
            details={"document_id": 999},
        )
    )
    with TestClient(create_app(_settings(), FakeDatabase(), service)) as client:
        response = client.post(
            "/extraction/documents/999/reparse",
            json={"extraction_version": "rules-v2"},
        )

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "reparse.document_not_found"


def test_reparse_endpoint_rejects_invalid_version_before_service_call() -> None:
    service = FakeReparseService()
    with TestClient(create_app(_settings(), FakeDatabase(), service)) as client:
        response = client.post(
            "/extraction/documents/19/reparse",
            json={"extraction_version": "bad version"},
        )

    assert response.status_code == 422
    assert service.requests == []


def test_reparse_endpoint_is_explicitly_unavailable_without_service() -> None:
    with TestClient(create_app(_settings(), FakeDatabase())) as client:
        response = client.post(
            "/extraction/documents/19/reparse",
            json={"extraction_version": "rules-v2"},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "reparse.service_unavailable"


def _settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="UTC",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
