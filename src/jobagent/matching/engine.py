"""Pure deterministic hard filters and versioned component scoring."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC, datetime, timedelta
from typing import Final, cast

from jobagent.core.exceptions import JsonValue
from jobagent.preferences import EducationLevel, PreferenceValues

from .contracts import (
    ComponentScore,
    HardFilterDecision,
    HardFilterRule,
    JobMatchInput,
    MatchEvaluation,
    ScoreComponent,
    preference_payload,
)

CURRENT_SCORE_VERSION: Final = "jai-023-v1"

_EDUCATION_RANK: Final[dict[str, int]] = {
    "no_requirement": 0,
    "high_school": 1,
    "secondary_vocational": 1,
    "associate": 2,
    "associate_or_above": 2,
    "bachelor": 3,
    "bachelor_or_above": 3,
    "master": 4,
    "master_or_above": 4,
    "doctorate": 5,
}
_COMPONENT_MAXIMUMS: Final = {
    ScoreComponent.REGION: 25,
    ScoreComponent.JOB_DIRECTION: 30,
    ScoreComponent.MAJOR: 15,
    ScoreComponent.ORGANIZATION_TYPE: 10,
    ScoreComponent.DEADLINE_URGENCY: 10,
    ScoreComponent.INFORMATION_COMPLETENESS: 10,
}
_WHITESPACE_RE: Final = re.compile(r"\s+")


class DeterministicMatchingEngine:
    """Evaluate one explicit snapshot without consulting clocks, I/O, or LLMs."""

    def evaluate(
        self,
        match_input: JobMatchInput,
        preferences: PreferenceValues,
        *,
        evaluated_at: datetime,
        score_version: str = CURRENT_SCORE_VERSION,
    ) -> MatchEvaluation:
        """Return the same output for identical input, preferences, time, and version."""
        evaluated_at = _aware_utc(evaluated_at)
        if score_version != CURRENT_SCORE_VERSION:
            raise ValueError(f"Unsupported score version: {score_version}")
        deadline = _deadline(match_input.deadline)

        hard_filters = (
            _validation_filter(match_input),
            _education_filter(match_input.education, preferences.education),
            _deadline_filter(deadline, evaluated_at),
            _exclusion_filter(match_input, preferences.exclusions),
        )
        components = (
            _region_component(match_input, preferences),
            _direction_component(match_input, preferences),
            _major_component(match_input, preferences),
            _organization_component(match_input, preferences),
            _urgency_component(deadline, evaluated_at),
            _completeness_component(match_input, deadline),
        )
        hard_filter_passed = all(item.passed for item in hard_filters)
        score = sum(item.score for item in components) if hard_filter_passed else 0
        input_hash = _hash_payload(_input_payload(match_input, deadline, evaluated_at))
        preference_hash = _hash_payload(preference_payload(preferences))
        result_payload: dict[str, JsonValue] = {
            "position_id": match_input.position_id,
            "post_id": match_input.post_id,
            "score_version": score_version,
            "input_hash": input_hash,
            "preference_hash": preference_hash,
            "hard_filter_passed": hard_filter_passed,
            "score": score,
            "hard_filters": [item.as_json() for item in hard_filters],
            "components": [item.as_json() for item in components],
        }
        return MatchEvaluation(
            position_id=match_input.position_id,
            post_id=match_input.post_id,
            score_version=score_version,
            input_hash=input_hash,
            preference_hash=preference_hash,
            result_hash=_hash_payload(result_payload),
            hard_filter_passed=hard_filter_passed,
            score=score,
            hard_filters=hard_filters,
            components=components,
        )


def _validation_filter(match_input: JobMatchInput) -> HardFilterDecision:
    passed = match_input.recommendation_eligible
    return HardFilterDecision(
        rule=HardFilterRule.VALIDATION_ELIGIBILITY,
        inputs={"recommendation_eligible": passed},
        passed=passed,
        explanation=(
            "The extraction passed recommendation validation."
            if passed
            else "The extraction is blocked from automatic recommendation."
        ),
    )


def _education_filter(
    requirement: EducationLevel | None,
    candidate: EducationLevel | None,
) -> HardFilterDecision:
    explicit = requirement not in (None, "no_requirement") and candidate not in (
        None,
        "no_requirement",
    )
    if explicit:
        assert candidate is not None and requirement is not None
        passed = _EDUCATION_RANK[candidate] >= _EDUCATION_RANK[requirement]
    else:
        passed = True
    return HardFilterDecision(
        rule=HardFilterRule.EDUCATION,
        inputs={"position_requirement": requirement, "candidate_education": candidate},
        passed=passed,
        explanation=(
            "No explicit education mismatch was evidenced."
            if passed
            else "The candidate education is below the evidenced position requirement."
        ),
    )


def _deadline_filter(deadline: datetime | None, evaluated_at: datetime) -> HardFilterDecision:
    passed = deadline is None or deadline > evaluated_at
    return HardFilterDecision(
        rule=HardFilterRule.DEADLINE,
        inputs={
            "deadline": _iso(deadline),
            "evaluated_at": _iso(evaluated_at),
        },
        passed=passed,
        explanation=(
            "The application deadline is open or not evidenced."
            if passed
            else "The application deadline has been reached or passed."
        ),
    )


def _exclusion_filter(
    match_input: JobMatchInput,
    exclusions: tuple[str, ...],
) -> HardFilterDecision:
    searchable = _searchable_values(match_input)
    matches = _matched_terms(exclusions, searchable)
    return HardFilterDecision(
        rule=HardFilterRule.EXCLUSION,
        inputs={
            "terms": list(exclusions),
            "matched_terms": list(matches),
            "organization": match_input.organization,
            "title": match_input.title,
            "position_name": match_input.position_name,
            "department": match_input.department,
            "major": match_input.major,
            "requirements": match_input.requirements,
        },
        passed=not matches,
        explanation=(
            "No explicit exclusion term matched."
            if not matches
            else "One or more explicit exclusion terms matched the position text."
        ),
    )


def _region_component(
    match_input: JobMatchInput,
    preferences: PreferenceValues,
) -> ComponentScore:
    preferred = tuple(preferences.regions)
    unrestricted = not preferred
    matched = unrestricted or "national" in preferred or match_input.region == "national"
    matched = matched or match_input.region in preferred
    score = _COMPONENT_MAXIMUMS[ScoreComponent.REGION] if matched else 0
    return _component(
        ScoreComponent.REGION,
        "region-any-or-exact-v1",
        {"position_region": match_input.region, "preferred_regions": list(preferred)},
        score,
        "Region is unrestricted or matches a preferred region."
        if matched
        else "Region did not match.",
    )


def _direction_component(
    match_input: JobMatchInput,
    preferences: PreferenceValues,
) -> ComponentScore:
    terms = tuple(preferences.job_keywords)
    matches = _matched_terms(terms, _direction_values(match_input))
    matched = not terms or bool(matches)
    return _component(
        ScoreComponent.JOB_DIRECTION,
        "job-keyword-any-v1",
        {
            "preferred_keywords": list(terms),
            "matched_keywords": list(matches),
            "position_name": match_input.position_name,
            "title": match_input.title,
            "department": match_input.department,
            "requirements": match_input.requirements,
        },
        _COMPONENT_MAXIMUMS[ScoreComponent.JOB_DIRECTION] if matched else 0,
        "Job direction is unrestricted or an explicit keyword matched."
        if matched
        else "No preferred job keyword matched.",
    )


def _major_component(
    match_input: JobMatchInput,
    preferences: PreferenceValues,
) -> ComponentScore:
    terms = tuple(preferences.majors)
    matches = _matched_terms(terms, (match_input.major,))
    matched = not terms or bool(matches)
    return _component(
        ScoreComponent.MAJOR,
        "major-any-v1",
        {
            "position_major": match_input.major,
            "preferred_majors": list(terms),
            "matched_majors": list(matches),
        },
        _COMPONENT_MAXIMUMS[ScoreComponent.MAJOR] if matched else 0,
        "Major is unrestricted or an explicit major preference matched."
        if matched
        else "No preferred major matched.",
    )


def _organization_component(
    match_input: JobMatchInput,
    preferences: PreferenceValues,
) -> ComponentScore:
    preferred = tuple(preferences.organization_types)
    matched = not preferred or match_input.organization_type in preferred
    return _component(
        ScoreComponent.ORGANIZATION_TYPE,
        "organization-type-exact-v1",
        {
            "position_organization_type": match_input.organization_type,
            "preferred_organization_types": list(preferred),
        },
        _COMPONENT_MAXIMUMS[ScoreComponent.ORGANIZATION_TYPE] if matched else 0,
        "Organization type is unrestricted or matches exactly."
        if matched
        else "Organization type did not match.",
    )


def _urgency_component(deadline: datetime | None, evaluated_at: datetime) -> ComponentScore:
    remaining_seconds: int | None = None
    if deadline is None or deadline <= evaluated_at:
        score = 0
    else:
        remaining = deadline - evaluated_at
        remaining_seconds = int(remaining.total_seconds())
        if remaining <= timedelta(hours=72):
            score = 10
        elif remaining <= timedelta(days=7):
            score = 8
        elif remaining <= timedelta(days=14):
            score = 5
        else:
            score = 2
    return _component(
        ScoreComponent.DEADLINE_URGENCY,
        "deadline-buckets-v1",
        {
            "deadline": _iso(deadline),
            "evaluated_at": _iso(evaluated_at),
            "remaining_seconds": remaining_seconds,
        },
        score,
        "Deadline urgency uses fixed 72-hour, 7-day, and 14-day boundaries.",
    )


def _completeness_component(
    match_input: JobMatchInput,
    deadline: datetime | None,
) -> ComponentScore:
    fields = {
        "organization": match_input.organization,
        "title": match_input.position_name or match_input.title,
        "region": match_input.region,
        "deadline": _iso(deadline),
        "source_url": match_input.source_url,
    }
    present = sorted(name for name, value in fields.items() if _present(value))
    missing = sorted(set(fields) - set(present))
    score = len(present) * 2
    return _component(
        ScoreComponent.INFORMATION_COMPLETENESS,
        "five-core-fields-v1",
        {
            "present_fields": cast(list[JsonValue], present),
            "missing_fields": cast(list[JsonValue], missing),
        },
        score,
        f"{len(present)} of 5 core fields are present.",
    )


def _component(
    component: ScoreComponent,
    rule: str,
    inputs: dict[str, JsonValue],
    score: int,
    explanation: str,
) -> ComponentScore:
    return ComponentScore(
        component=component,
        rule=rule,
        inputs=inputs,
        score=score,
        maximum=_COMPONENT_MAXIMUMS[component],
        explanation=explanation,
    )


def _input_payload(
    match_input: JobMatchInput,
    deadline: datetime | None,
    evaluated_at: datetime,
) -> dict[str, JsonValue]:
    return {
        "position_id": match_input.position_id,
        "post_id": match_input.post_id,
        "recommendation_eligible": match_input.recommendation_eligible,
        "organization": match_input.organization,
        "organization_type": match_input.organization_type,
        "region": match_input.region,
        "deadline": _iso(deadline),
        "title": match_input.title,
        "source_url": match_input.source_url,
        "position_name": match_input.position_name,
        "department": match_input.department,
        "education": match_input.education,
        "major": match_input.major,
        "requirements": match_input.requirements,
        "evaluated_at": _iso(evaluated_at),
    }


def _direction_values(match_input: JobMatchInput) -> tuple[str | None, ...]:
    return (
        match_input.position_name,
        match_input.title,
        match_input.department,
        match_input.requirements,
    )


def _searchable_values(match_input: JobMatchInput) -> tuple[str | None, ...]:
    return (
        match_input.organization,
        match_input.title,
        match_input.position_name,
        match_input.department,
        match_input.major,
        match_input.requirements,
    )


def _matched_terms(terms: tuple[str, ...], values: tuple[str | None, ...]) -> tuple[str, ...]:
    normalized_values = tuple(
        _normalize(value) for value in values if value is not None and value.strip()
    )
    matches = []
    for term in terms:
        normalized_term = _normalize(term)
        if normalized_term and any(normalized_term in value for value in normalized_values):
            matches.append(term)
    return tuple(matches)


def _normalize(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", unicodedata.normalize("NFKC", value)).strip().casefold()


def _present(value: object | None) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _deadline(value: object | None) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise ValueError("Matching deadlines must be timezone-aware datetimes.")
    return _aware_utc(value)


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Matching evaluation times must include timezone information.")
    return value.astimezone(UTC)


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _hash_payload(payload: dict[str, JsonValue]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def education_rank(value: EducationLevel) -> int:
    """Expose the documented education ordering for focused boundary checks."""
    return _EDUCATION_RANK[cast(str, value)]
