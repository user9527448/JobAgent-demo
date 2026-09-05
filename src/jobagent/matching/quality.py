"""Deterministic offline Top-K review for fixed relevance-labelled samples."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, cast

from jobagent.preferences import (
    EducationLevel,
    OrganizationType,
    PreferenceValues,
    RegionCode,
)

from .contracts import JobMatchInput
from .engine import CURRENT_SCORE_VERSION, LEGACY_SCORE_VERSION, DeterministicMatchingEngine


class RelevanceLabel(StrEnum):
    """Binary manual-review judgement used by the MVP Top-K benchmark."""

    RELEVANT = "relevant"
    NOT_RELEVANT = "not_relevant"


@dataclass(frozen=True, slots=True)
class QualityReviewCase:
    """One sanitized position with an explicit relevance judgement and rationale."""

    match_input: JobMatchInput
    label: RelevanceLabel
    reason_category: str
    rationale: str

    def __post_init__(self) -> None:
        if not self.reason_category.strip() or not self.rationale.strip():
            raise ValueError("Quality-review labels require a category and rationale.")


@dataclass(frozen=True, slots=True)
class QualityReviewSet:
    """Fixed preferences, evaluation time, and labelled cases for one review."""

    schema_version: str
    evaluated_at: datetime
    preferences: PreferenceValues
    cases: tuple[QualityReviewCase, ...]

    def __post_init__(self) -> None:
        if not self.schema_version.strip() or not self.cases:
            raise ValueError("Quality-review sets require a schema version and cases.")
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("Quality-review evaluation time must include a timezone.")
        identifiers = [case.match_input.position_id for case in self.cases]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Quality-review position IDs must be unique.")


@dataclass(frozen=True, slots=True)
class RankedQualityCase:
    """One evaluated sample with its stable rank and manual label."""

    rank: int
    position_id: int
    score: int
    hard_filter_passed: bool
    label: RelevanceLabel
    reason_category: str
    rationale: str

    def as_json(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "position_id": self.position_id,
            "score": self.score,
            "hard_filter_passed": self.hard_filter_passed,
            "label": self.label.value,
            "reason_category": self.reason_category,
            "rationale": self.rationale,
        }


@dataclass(frozen=True, slots=True)
class QualityVersionReview:
    """Top-K quality metrics and auditable false-positive/miss classifications."""

    score_version: str
    top_k: int
    total_cases: int
    total_relevant: int
    true_positive_count: int
    false_positive_count: int
    miss_count: int
    precision_at_k: float
    recall_at_k: float
    top_items: tuple[RankedQualityCase, ...]
    false_positives: tuple[RankedQualityCase, ...]
    misses: tuple[RankedQualityCase, ...]

    def as_json(self) -> dict[str, object]:
        return {
            "score_version": self.score_version,
            "top_k": self.top_k,
            "total_cases": self.total_cases,
            "total_relevant": self.total_relevant,
            "true_positive_count": self.true_positive_count,
            "false_positive_count": self.false_positive_count,
            "miss_count": self.miss_count,
            "precision_at_k": self.precision_at_k,
            "recall_at_k": self.recall_at_k,
            "top_items": [item.as_json() for item in self.top_items],
            "false_positives": [item.as_json() for item in self.false_positives],
            "misses": [item.as_json() for item in self.misses],
        }


@dataclass(frozen=True, slots=True)
class QualityComparison:
    """Before/after review over identical inputs and labels."""

    schema_version: str
    baseline: QualityVersionReview
    candidate: QualityVersionReview

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "baseline": self.baseline.as_json(),
            "candidate": self.candidate.as_json(),
            "precision_at_k_delta": round(
                self.candidate.precision_at_k - self.baseline.precision_at_k, 6
            ),
            "recall_at_k_delta": round(self.candidate.recall_at_k - self.baseline.recall_at_k, 6),
        }


def compare_quality(
    review_set: QualityReviewSet,
    *,
    top_k: int = 20,
    baseline_version: str = LEGACY_SCORE_VERSION,
    candidate_version: str = CURRENT_SCORE_VERSION,
    engine: DeterministicMatchingEngine | None = None,
) -> QualityComparison:
    """Evaluate two explicit score versions against the same immutable review set."""
    if top_k <= 0 or top_k > len(review_set.cases):
        raise ValueError("Top-K must be positive and no larger than the review set.")
    matcher = engine or DeterministicMatchingEngine()
    return QualityComparison(
        schema_version=review_set.schema_version,
        baseline=_review_version(review_set, matcher, score_version=baseline_version, top_k=top_k),
        candidate=_review_version(
            review_set, matcher, score_version=candidate_version, top_k=top_k
        ),
    )


def load_quality_review_set(path: Path) -> QualityReviewSet:
    """Load the compact, sanitized JSON review fixture with strict required fields."""
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    defaults = _mapping(payload.get("input_defaults"), "input_defaults")
    preferences = _preferences(_mapping(payload.get("preferences"), "preferences"))
    evaluated_at = _datetime(payload.get("evaluated_at"), "evaluated_at")
    raw_cases = payload.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("Quality-review cases must be a JSON array.")
    cases = tuple(_case(item, defaults) for item in raw_cases)
    schema_version = payload.get("schema_version")
    if not isinstance(schema_version, str):
        raise ValueError("Quality-review schema_version must be a string.")
    return QualityReviewSet(schema_version, evaluated_at, preferences, cases)


def _review_version(
    review_set: QualityReviewSet,
    engine: DeterministicMatchingEngine,
    *,
    score_version: str,
    top_k: int,
) -> QualityVersionReview:
    evaluated = [
        (
            case,
            engine.evaluate(
                case.match_input,
                review_set.preferences,
                evaluated_at=review_set.evaluated_at,
                score_version=score_version,
            ),
        )
        for case in review_set.cases
    ]
    evaluated.sort(key=lambda item: (-item[1].score, item[0].match_input.position_id))
    ranked = tuple(
        RankedQualityCase(
            rank=index,
            position_id=case.match_input.position_id,
            score=result.score,
            hard_filter_passed=result.hard_filter_passed,
            label=case.label,
            reason_category=case.reason_category,
            rationale=case.rationale,
        )
        for index, (case, result) in enumerate(evaluated, start=1)
    )
    top_items = ranked[:top_k]
    false_positives = tuple(item for item in top_items if item.label is RelevanceLabel.NOT_RELEVANT)
    misses = tuple(item for item in ranked[top_k:] if item.label is RelevanceLabel.RELEVANT)
    total_relevant = sum(case.label is RelevanceLabel.RELEVANT for case in review_set.cases)
    true_positives = top_k - len(false_positives)
    return QualityVersionReview(
        score_version=score_version,
        top_k=top_k,
        total_cases=len(review_set.cases),
        total_relevant=total_relevant,
        true_positive_count=true_positives,
        false_positive_count=len(false_positives),
        miss_count=len(misses),
        precision_at_k=round(true_positives / top_k, 6),
        recall_at_k=round(true_positives / total_relevant, 6) if total_relevant else 0.0,
        top_items=top_items,
        false_positives=false_positives,
        misses=misses,
    )


def _case(value: object, defaults: dict[str, Any]) -> QualityReviewCase:
    payload = _mapping(value, "case")
    identifier = payload.get("position_id")
    if not isinstance(identifier, int) or isinstance(identifier, bool) or identifier <= 0:
        raise ValueError("Quality-review position_id must be a positive integer.")
    overrides = _mapping(payload.get("input"), "case.input")
    input_payload = {**defaults, **overrides}
    source_url = input_payload.get("source_url")
    if source_url is None:
        source_url = f"https://example.invalid/jai-025/{identifier:03d}"
    label = payload.get("label")
    if not isinstance(label, str):
        raise ValueError("Quality-review label must be relevant or not_relevant.")
    try:
        relevance = RelevanceLabel(label)
    except (TypeError, ValueError) as error:
        raise ValueError("Quality-review label must be relevant or not_relevant.") from error
    return QualityReviewCase(
        match_input=JobMatchInput(
            position_id=identifier,
            post_id=identifier,
            recommendation_eligible=_boolean(
                input_payload.get("recommendation_eligible"), "recommendation_eligible"
            ),
            organization=_optional_string(input_payload.get("organization")),
            organization_type=cast(
                OrganizationType | None,
                _optional_string(input_payload.get("organization_type")),
            ),
            region=cast(RegionCode | None, _optional_string(input_payload.get("region"))),
            deadline=_optional_datetime(input_payload.get("deadline"), "deadline"),
            title=_optional_string(input_payload.get("title")),
            source_url=_optional_string(source_url),
            position_name=_optional_string(input_payload.get("position_name")),
            department=_optional_string(input_payload.get("department")),
            education=cast(EducationLevel | None, _optional_string(input_payload.get("education"))),
            major=_optional_string(input_payload.get("major")),
            requirements=_optional_string(input_payload.get("requirements")),
        ),
        label=relevance,
        reason_category=_required_string(payload.get("reason_category"), "reason_category"),
        rationale=_required_string(payload.get("rationale"), "rationale"),
    )


def _preferences(payload: dict[str, Any]) -> PreferenceValues:
    return PreferenceValues(
        regions=cast(tuple[RegionCode, ...], _string_tuple(payload.get("regions"))),
        education=cast(EducationLevel | None, _optional_string(payload.get("education"))),
        majors=_string_tuple(payload.get("majors")),
        job_keywords=_string_tuple(payload.get("job_keywords")),
        organization_types=cast(
            tuple[OrganizationType, ...],
            _string_tuple(payload.get("organization_types")),
        ),
        exclusions=_string_tuple(payload.get("exclusions")),
    )


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"Quality-review {label} must be a JSON object.")
    return cast(dict[str, Any], value)


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise ValueError("Quality-review preference lists require non-empty strings.")
    return tuple(value)


def _required_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Quality-review {label} must be a non-empty string.")
    return value


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Quality-review optional text fields must be strings or null.")
    return value


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Quality-review {label} must be a boolean.")
    return value


def _datetime(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"Quality-review {label} must be an ISO datetime string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Quality-review {label} must be an ISO datetime string.") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"Quality-review {label} must include a timezone.")
    return parsed.astimezone(UTC)


def _optional_datetime(value: object, label: str) -> datetime | None:
    return None if value is None else _datetime(value, label)
