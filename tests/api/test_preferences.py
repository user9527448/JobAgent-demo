"""JAI-022 single-user preference API checks."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from pydantic import SecretStr

from jobagent.api import create_app
from jobagent.core.config import Settings
from jobagent.preferences import PreferenceSnapshot, PreferenceValues


class FakeDatabase:
    async def ping(self) -> None:
        return None

    async def close(self) -> None:
        return None


class FakePreferenceService:
    def __init__(self) -> None:
        timestamp = datetime(2026, 8, 30, 8, tzinfo=UTC)
        self.snapshot = PreferenceSnapshot(
            values=PreferenceValues(),
            recompute_required=False,
            recompute_requested_at=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.updates: list[tuple[PreferenceValues, bool]] = []

    async def get(self) -> PreferenceSnapshot:
        return self.snapshot

    async def replace(
        self,
        values: PreferenceValues,
        *,
        trigger_recompute: bool,
    ) -> PreferenceSnapshot:
        self.updates.append((values, trigger_recompute))
        updated_at = datetime(2026, 8, 30, 9, tzinfo=UTC)
        self.snapshot = PreferenceSnapshot(
            values=values,
            recompute_required=trigger_recompute,
            recompute_requested_at=updated_at if trigger_recompute else None,
            created_at=self.snapshot.created_at,
            updated_at=updated_at,
        )
        return self.snapshot


def test_default_profile_is_unrestricted_and_does_not_request_recomputation() -> None:
    service = FakePreferenceService()
    with TestClient(create_app(_settings(), FakeDatabase(), preference_service=service)) as client:
        response = client.get("/preferences")

    assert response.status_code == 200
    payload = response.json()
    for field_name in (
        "regions",
        "majors",
        "job_keywords",
        "organization_types",
        "exclusions",
    ):
        assert payload[field_name] == []
    assert payload["education"] is None
    assert payload["recompute_required"] is False
    assert payload["recompute_requested_at"] is None


def test_update_normalizes_values_and_requests_recomputation() -> None:
    service = FakePreferenceService()
    with TestClient(create_app(_settings(), FakeDatabase(), preference_service=service)) as client:
        response = client.put(
            "/preferences",
            json={
                "regions": ["shanghai", "jiangsu", "shanghai"],
                "education": "bachelor_or_above",
                "majors": ["  计算机   科学  ", "计算机 科学"],
                "job_keywords": ["Python", "\uff30\uff59\uff54\uff48\uff4f\uff4e"],
                "organization_types": ["state_owned"],
                "exclusions": ["销售"],
            },
        )

    assert response.status_code == 200
    assert response.json()["regions"] == ["shanghai", "jiangsu"]
    assert response.json()["majors"] == ["计算机 科学"]
    assert response.json()["job_keywords"] == ["Python"]
    assert response.json()["recompute_required"] is True
    assert response.json()["recompute_requested_at"] == "2026-08-30T09:00:00Z"
    assert service.updates == [
        (
            PreferenceValues(
                regions=("shanghai", "jiangsu"),
                education="bachelor_or_above",
                majors=("计算机 科学",),
                job_keywords=("Python",),
                organization_types=("state_owned",),
                exclusions=("销售",),
            ),
            True,
        )
    ]


def test_update_can_defer_recomputation() -> None:
    service = FakePreferenceService()
    with TestClient(create_app(_settings(), FakeDatabase(), preference_service=service)) as client:
        response = client.put(
            "/preferences",
            json={"regions": ["beijing"], "trigger_recompute": False},
        )

    assert response.status_code == 200
    assert response.json()["recompute_required"] is False
    assert service.updates[0][1] is False


def test_update_rejects_unknown_enum_and_empty_keyword_before_service_call() -> None:
    service = FakePreferenceService()
    with TestClient(create_app(_settings(), FakeDatabase(), preference_service=service)) as client:
        unknown_region = client.put("/preferences", json={"regions": ["mars"]})
        empty_keyword = client.put("/preferences", json={"job_keywords": ["   "]})

    assert unknown_region.status_code == 422
    assert empty_keyword.status_code == 422
    assert service.updates == []


def test_preference_endpoint_is_explicitly_unavailable_without_service() -> None:
    with TestClient(create_app(_settings(), FakeDatabase())) as client:
        response = client.get("/preferences")

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "preferences.service_unavailable"


def _settings() -> Settings:
    return Settings(
        environment="test",
        log_level="CRITICAL",
        timezone="UTC",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
