"""PostgreSQL persistence for the single-user preference profile."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.db.models import UserPreference
from jobagent.preferences.contracts import (
    EducationLevel,
    OrganizationType,
    PreferenceSnapshot,
    PreferenceValues,
    RegionCode,
)


class SqlAlchemyPreferenceRepository:
    """Serialize updates to the singleton preference row."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get(self) -> PreferenceSnapshot:
        """Load the profile created by the JAI-022 migration."""
        try:
            async with self._session_factory() as session:
                model = await session.get(UserPreference, 1)
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Preferences are temporarily unavailable.",
                code="preferences.database_unavailable",
            ) from error
        return _snapshot(_require_profile(model))

    async def replace(
        self,
        values: PreferenceValues,
        *,
        trigger_recompute: bool,
    ) -> PreferenceSnapshot:
        """Replace the profile atomically and retain any pending recomputation signal."""
        try:
            async with self._session_factory() as session, session.begin():
                model = await session.scalar(
                    select(UserPreference).where(UserPreference.id == 1).with_for_update()
                )
                profile = _require_profile(model)
                now = datetime.now(UTC)
                profile.regions = list(values.regions)
                profile.education = values.education
                profile.majors = list(values.majors)
                profile.job_keywords = list(values.job_keywords)
                profile.organization_types = list(values.organization_types)
                profile.exclusions = list(values.exclusions)
                profile.updated_at = now
                if trigger_recompute:
                    profile.recompute_required = True
                    profile.recompute_requested_at = now
                await session.flush()
                snapshot = _snapshot(profile)
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Preferences could not be updated.",
                code="preferences.update_failed",
            ) from error
        return snapshot


def _require_profile(model: UserPreference | None) -> UserPreference:
    if model is None:
        raise PermanentJobAgentError(
            "The single-user preference profile is not initialized.",
            code="preferences.not_initialized",
        )
    return model


def _snapshot(model: UserPreference) -> PreferenceSnapshot:
    return PreferenceSnapshot(
        values=PreferenceValues(
            regions=cast(tuple[RegionCode, ...], tuple(model.regions)),
            education=cast(EducationLevel | None, model.education),
            majors=tuple(model.majors),
            job_keywords=tuple(model.job_keywords),
            organization_types=cast(tuple[OrganizationType, ...], tuple(model.organization_types)),
            exclusions=tuple(model.exclusions),
        ),
        recompute_required=model.recompute_required,
        recompute_requested_at=model.recompute_requested_at,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
