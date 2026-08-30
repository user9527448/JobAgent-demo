"""Stable contracts for deterministic hard filtering and rule scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from jobagent.core.exceptions import JsonValue
from jobagent.preferences import EducationLevel, OrganizationType, PreferenceValues, RegionCode


class HardFilterRule(StrEnum):
    """Hard conditions that can reduce the recommendation score to zero."""

    VALIDATION_ELIGIBILITY = "validation_eligibility"
    EDUCATION = "education"
    DEADLINE = "deadline"
    EXCLUSION = "exclusion"


class ScoreComponent(StrEnum):
    """The six fixed JAI-023 scoring components."""

    REGION = "region"
    JOB_DIRECTION = "job_direction"
    MAJOR = "major"
    ORGANIZATION_TYPE = "organization_type"
    DEADLINE_URGENCY = "deadline_urgency"
    INFORMATION_COMPLETENESS = "information_completeness"


@dataclass(frozen=True, slots=True)
class JobMatchInput:
    """One persisted position plus the announcement facts required for matching."""

    position_id: int
    post_id: int
    recommendation_eligible: bool
    organization: str | None = None
    organization_type: OrganizationType | None = None
    region: RegionCode | None = None
    deadline: datetime | None = None
    title: str | None = None
    source_url: str | None = None
    position_name: str | None = None
    department: str | None = None
    education: EducationLevel | None = None
    major: str | None = None
    requirements: str | None = None

    def __post_init__(self) -> None:
        if self.position_id <= 0 or self.post_id <= 0:
            raise ValueError("Matching position and post IDs must be positive.")


@dataclass(frozen=True, slots=True)
class HardFilterDecision:
    """One hard-filter rule with persisted inputs and explanation."""

    rule: HardFilterRule
    inputs: dict[str, JsonValue]
    passed: bool
    explanation: str

    def as_json(self) -> dict[str, JsonValue]:
        """Return the stable JSON shape persisted in `matched_rules`."""
        return {
            "rule": self.rule.value,
            "inputs": self.inputs,
            "passed": self.passed,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class ComponentScore:
    """One bounded component result with all explanation inputs."""

    component: ScoreComponent
    rule: str
    inputs: dict[str, JsonValue]
    score: int
    maximum: int
    explanation: str

    def __post_init__(self) -> None:
        if self.maximum <= 0 or not 0 <= self.score <= self.maximum:
            raise ValueError("Component scores must be within their declared bounds.")
        if not self.rule.strip() or not self.explanation.strip():
            raise ValueError("Component rule and explanation cannot be empty.")

    def as_json(self) -> dict[str, JsonValue]:
        """Return the stable JSON shape persisted in `components`."""
        return {
            "component": self.component.value,
            "rule": self.rule,
            "inputs": self.inputs,
            "score": self.score,
            "maximum": self.maximum,
            "explanation": self.explanation,
        }


@dataclass(frozen=True, slots=True)
class MatchEvaluation:
    """Deterministic result for one position, preference profile, time, and version."""

    position_id: int
    post_id: int
    score_version: str
    input_hash: str
    preference_hash: str
    result_hash: str
    hard_filter_passed: bool
    score: int
    hard_filters: tuple[HardFilterDecision, ...]
    components: tuple[ComponentScore, ...]

    def __post_init__(self) -> None:
        if len(self.hard_filters) != 4 or len(self.components) != 6:
            raise ValueError("Match evaluations require every hard filter and score component.")
        if self.hard_filter_passed != all(item.passed for item in self.hard_filters):
            raise ValueError("Hard-filter summary does not match its decisions.")
        expected = sum(item.score for item in self.components) if self.hard_filter_passed else 0
        if self.score != expected or not 0 <= self.score <= 100:
            raise ValueError("Total score does not match the component and filter results.")


def preference_payload(values: PreferenceValues) -> dict[str, JsonValue]:
    """Return the stable preference representation shared by hashing and persistence."""
    return {
        "regions": list(values.regions),
        "education": values.education,
        "majors": list(values.majors),
        "job_keywords": list(values.job_keywords),
        "organization_types": list(values.organization_types),
        "exclusions": list(values.exclusions),
    }
