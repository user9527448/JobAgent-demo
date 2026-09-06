"""Atomic PostgreSQL persistence and preference-triggered full recomputation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final, cast

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.db.models import JobPosition, JobPost, MatchResult, RawDocument, UserPreference
from jobagent.extraction.dictionaries import EDUCATION_ALIASES, REGION_ALIASES
from jobagent.preferences import (
    EducationLevel,
    OrganizationType,
    PreferenceValues,
    RegionCode,
)

from .contracts import JobMatchInput, MatchEvaluation
from .engine import CURRENT_SCORE_VERSION, DeterministicMatchingEngine

_REGION_CODES: Final = frozenset(code for code, _aliases in REGION_ALIASES)
_EDUCATION_LEVELS: Final = frozenset(code for code, _aliases in EDUCATION_ALIASES)
_ORGANIZATION_TYPES: Final = frozenset(
    {"government", "public_institution", "state_owned", "private", "foreign_enterprise"}
)
_CATEGORY_ORGANIZATION_TYPE: Final[dict[str, str]] = {
    "civil_service": "government",
    "public_institution": "public_institution",
    "state_owned": "state_owned",
}


class RecomputeStatus(StrEnum):
    """Observable outcome of checking the sticky preference signal."""

    NOT_REQUIRED = "not_required"
    COMPLETED = "completed"


@dataclass(frozen=True, slots=True)
class MatchingRecomputeResult:
    """Summary of one atomic preference-signal consumption attempt."""

    status: RecomputeStatus
    score_version: str
    evaluated_at: datetime
    requested_at: datetime | None
    preference_updated_at: datetime
    processed_count: int
    passed_count: int
    filtered_count: int
    created_count: int
    unchanged_count: int
    result_ids: tuple[int, ...]


class SqlAlchemyMatchingService:
    """Recompute every current position and acknowledge the signal only on commit."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        engine: DeterministicMatchingEngine | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine or DeterministicMatchingEngine()

    async def recompute_if_requested(
        self,
        *,
        evaluated_at: datetime,
        score_version: str = CURRENT_SCORE_VERSION,
        force: bool = False,
    ) -> MatchingRecomputeResult:
        """Consume a pending signal or explicitly force one atomic full evaluation."""
        evaluated_at = _aware_utc(evaluated_at)
        try:
            async with self._session_factory() as session, session.begin():
                profile = await session.scalar(
                    select(UserPreference).where(UserPreference.id == 1).with_for_update()
                )
                if profile is None:
                    raise PermanentJobAgentError(
                        "The single-user preference profile is not initialized.",
                        code="matching.preferences_not_initialized",
                    )
                preferences = _preference_values(profile)
                preference_updated_at = profile.updated_at
                if not profile.recompute_required and not force:
                    return MatchingRecomputeResult(
                        status=RecomputeStatus.NOT_REQUIRED,
                        score_version=score_version,
                        evaluated_at=evaluated_at,
                        requested_at=profile.recompute_requested_at,
                        preference_updated_at=preference_updated_at,
                        processed_count=0,
                        passed_count=0,
                        filtered_count=0,
                        created_count=0,
                        unchanged_count=0,
                        result_ids=(),
                    )

                rows = (
                    await session.execute(
                        select(JobPosition, JobPost, RawDocument)
                        .join(JobPost, JobPosition.post_id == JobPost.id)
                        .join(RawDocument, JobPost.document_id == RawDocument.id)
                        .where(JobPost.is_current.is_(True))
                        .order_by(JobPosition.id)
                    )
                ).all()
                passed = filtered = created = unchanged = 0
                result_ids: list[int] = []
                for position, post, document in rows:
                    evaluation = self._engine.evaluate(
                        _match_input(position, post, document),
                        preferences,
                        evaluated_at=evaluated_at,
                        score_version=score_version,
                    )
                    if evaluation.hard_filter_passed:
                        passed += 1
                    else:
                        filtered += 1
                    result_id, was_created = await _persist_evaluation(
                        session,
                        evaluation,
                        evaluated_at=evaluated_at,
                        preference_updated_at=preference_updated_at,
                    )
                    result_ids.append(result_id)
                    if was_created:
                        created += 1
                    else:
                        unchanged += 1

                await session.execute(
                    update(UserPreference)
                    .where(UserPreference.id == 1)
                    .values(
                        recompute_required=False,
                        updated_at=preference_updated_at,
                    )
                )
                return MatchingRecomputeResult(
                    status=RecomputeStatus.COMPLETED,
                    score_version=score_version,
                    evaluated_at=evaluated_at,
                    requested_at=profile.recompute_requested_at,
                    preference_updated_at=preference_updated_at,
                    processed_count=len(rows),
                    passed_count=passed,
                    filtered_count=filtered,
                    created_count=created,
                    unchanged_count=unchanged,
                    result_ids=tuple(result_ids),
                )
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Matching recomputation could not be completed.",
                code="matching.database_unavailable",
            ) from error


async def _persist_evaluation(
    session: AsyncSession,
    evaluation: MatchEvaluation,
    *,
    evaluated_at: datetime,
    preference_updated_at: datetime,
) -> tuple[int, bool]:
    existing = await session.scalar(
        select(MatchResult).where(
            MatchResult.position_id == evaluation.position_id,
            MatchResult.score_version == evaluation.score_version,
            MatchResult.input_hash == evaluation.input_hash,
            MatchResult.preference_hash == evaluation.preference_hash,
            MatchResult.preference_updated_at == preference_updated_at,
        )
    )
    if existing is not None:
        if existing.result_hash != evaluation.result_hash:
            raise PermanentJobAgentError(
                "The same score version and inputs produced a different result.",
                code="matching.version_not_deterministic",
                details={
                    "position_id": evaluation.position_id,
                    "score_version": evaluation.score_version,
                },
            )
        return existing.id, False

    current = await session.scalar(
        select(MatchResult)
        .where(
            MatchResult.position_id == evaluation.position_id,
            MatchResult.is_current.is_(True),
        )
        .with_for_update()
    )
    if current is not None:
        current.is_current = False
    row = MatchResult(
        position_id=evaluation.position_id,
        preference_id=1,
        score_version=evaluation.score_version,
        input_hash=evaluation.input_hash,
        preference_hash=evaluation.preference_hash,
        result_hash=evaluation.result_hash,
        hard_filter_passed=evaluation.hard_filter_passed,
        score=evaluation.score,
        components=[item.as_json() for item in evaluation.components],
        matched_rules=[item.as_json() for item in evaluation.hard_filters],
        evaluated_at=evaluated_at,
        preference_updated_at=preference_updated_at,
        is_current=True,
        supersedes_id=None if current is None else current.id,
    )
    session.add(row)
    await session.flush()
    return row.id, True


def _preference_values(profile: UserPreference) -> PreferenceValues:
    return PreferenceValues(
        regions=cast(tuple[RegionCode, ...], tuple(profile.regions)),
        education=cast(EducationLevel | None, profile.education),
        majors=tuple(profile.majors),
        job_keywords=tuple(profile.job_keywords),
        organization_types=cast(
            tuple[OrganizationType, ...],
            tuple(profile.organization_types),
        ),
        exclusions=tuple(profile.exclusions),
    )


def _match_input(
    position: JobPosition,
    post: JobPost,
    document: RawDocument,
) -> JobMatchInput:
    region_value = position.location if position.location in _REGION_CODES else post.region
    region = cast(RegionCode | None, region_value if region_value in _REGION_CODES else None)
    education = cast(
        EducationLevel | None,
        position.education if position.education in _EDUCATION_LEVELS else None,
    )
    mapped_type = _CATEGORY_ORGANIZATION_TYPE.get(post.category or "")
    organization_type = cast(
        OrganizationType | None,
        mapped_type if mapped_type in _ORGANIZATION_TYPES else None,
    )
    return JobMatchInput(
        position_id=position.id,
        post_id=post.id,
        recommendation_eligible=post.recommendation_eligible,
        organization=post.organization,
        organization_type=organization_type,
        region=region,
        deadline=post.deadline,
        title=document.title,
        source_url=document.canonical_url,
        position_name=position.name,
        department=position.department,
        education=education,
        major=position.major,
        requirements=position.requirements,
    )


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Matching recomputation time must include timezone information.")
    return value.astimezone(UTC)
