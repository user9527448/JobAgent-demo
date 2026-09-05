"""JAI-023 deterministic hard-filter and component-score boundaries."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from jobagent.matching import (
    CURRENT_SCORE_VERSION,
    LEGACY_SCORE_VERSION,
    ComponentScore,
    DeterministicMatchingEngine,
    HardFilterDecision,
    HardFilterRule,
    JobMatchInput,
    MatchEvaluation,
    ScoreComponent,
)
from jobagent.preferences import EducationLevel, PreferenceValues

NOW = datetime(2026, 8, 30, 2, 0, tzinfo=UTC)


def test_identical_input_preferences_time_and_version_are_byte_stable() -> None:
    engine = DeterministicMatchingEngine()
    match_input = _complete_input()
    preferences = _matching_preferences()

    first = engine.evaluate(match_input, preferences, evaluated_at=NOW)
    same_in_shanghai = engine.evaluate(
        match_input,
        preferences,
        evaluated_at=NOW.astimezone(timezone(timedelta(hours=8))),
    )

    assert first == same_in_shanghai
    assert first.score_version == CURRENT_SCORE_VERSION
    assert first.score == 100
    assert first.hard_filter_passed is True
    assert len(first.result_hash) == 64
    assert sum(component.maximum for component in first.components) == 100


@pytest.mark.parametrize(
    ("candidate", "requirement", "passed"),
    [
        ("bachelor", "bachelor_or_above", True),
        ("bachelor", "master", False),
        ("doctorate", "master_or_above", True),
        (None, "doctorate", True),
        ("associate", None, True),
        ("no_requirement", "doctorate", True),
    ],
)
def test_education_hard_filter_uses_explicit_rank_only(
    candidate: EducationLevel | None,
    requirement: EducationLevel | None,
    passed: bool,
) -> None:
    result = DeterministicMatchingEngine().evaluate(
        replace(_complete_input(), education=requirement),
        replace(_matching_preferences(), education=candidate),
        evaluated_at=NOW,
    )

    decision = _hard_filter(result, HardFilterRule.EDUCATION)
    assert decision.passed is passed
    assert result.score == (100 if passed else 0)


def test_deadline_at_evaluation_instant_is_closed_and_missing_is_not_guessed() -> None:
    engine = DeterministicMatchingEngine()
    expired = engine.evaluate(
        replace(_complete_input(), deadline=NOW),
        _matching_preferences(),
        evaluated_at=NOW,
    )
    missing = engine.evaluate(
        replace(_complete_input(), deadline=None),
        _matching_preferences(),
        evaluated_at=NOW,
    )

    assert _hard_filter(expired, HardFilterRule.DEADLINE).passed is False
    assert expired.score == 0
    assert _hard_filter(missing, HardFilterRule.DEADLINE).passed is True
    assert _component(missing, ScoreComponent.DEADLINE_URGENCY).score == 0
    assert _component(missing, ScoreComponent.INFORMATION_COMPLETENESS).score == 4


def test_urgency_buckets_include_exact_boundaries() -> None:
    engine = DeterministicMatchingEngine()
    cases = (
        (timedelta(hours=72), 5),
        (timedelta(hours=72, microseconds=1), 4),
        (timedelta(days=7), 4),
        (timedelta(days=7, microseconds=1), 2),
        (timedelta(days=14), 2),
        (timedelta(days=14, microseconds=1), 1),
    )

    for remaining, expected in cases:
        result = engine.evaluate(
            replace(_complete_input(), deadline=NOW + remaining),
            _matching_preferences(),
            evaluated_at=NOW,
        )
        assert _component(result, ScoreComponent.DEADLINE_URGENCY).score == expected


def test_exclusions_use_nfkc_casefolded_substring_matching() -> None:
    fullwidth_sales = "".join(chr(ord(character) + 0xFEE0) for character in "sales")
    exclusion = f"  {fullwidth_sales} "
    result = DeterministicMatchingEngine().evaluate(
        replace(_complete_input(), requirements="Overseas SALES rotation"),
        replace(_matching_preferences(), exclusions=(exclusion,)),
        evaluated_at=NOW,
    )

    decision = _hard_filter(result, HardFilterRule.EXCLUSION)
    assert decision.passed is False
    assert decision.inputs["matched_terms"] == [exclusion]
    assert result.score == 0


def test_validation_ineligibility_is_an_explicit_hard_filter() -> None:
    result = DeterministicMatchingEngine().evaluate(
        replace(_complete_input(), recommendation_eligible=False),
        _matching_preferences(),
        evaluated_at=NOW,
    )

    assert _hard_filter(result, HardFilterRule.VALIDATION_ELIGIBILITY).passed is False
    assert result.score == 0


def test_empty_preferences_are_neutral_and_never_filter_everything() -> None:
    result = DeterministicMatchingEngine().evaluate(
        _complete_input(),
        PreferenceValues(),
        evaluated_at=NOW,
    )

    assert result.hard_filter_passed is True
    assert _component(result, ScoreComponent.REGION).score == 25
    assert _component(result, ScoreComponent.JOB_DIRECTION).score == 35
    assert _component(result, ScoreComponent.MAJOR).score == 20
    assert _component(result, ScoreComponent.ORGANIZATION_TYPE).score == 10


def test_nonmatching_preferences_zero_only_the_relevant_components() -> None:
    preferences = PreferenceValues(
        regions=("beijing",),
        education="bachelor",
        majors=("chemistry",),
        job_keywords=("finance",),
        organization_types=("private",),
    )
    result = DeterministicMatchingEngine().evaluate(
        _complete_input(),
        preferences,
        evaluated_at=NOW,
    )

    assert result.hard_filter_passed is True
    assert result.score == 10
    assert [
        _component(result, component).score
        for component in (
            ScoreComponent.REGION,
            ScoreComponent.JOB_DIRECTION,
            ScoreComponent.MAJOR,
            ScoreComponent.ORGANIZATION_TYPE,
        )
    ] == [0, 0, 0, 0]
    assert _component(result, ScoreComponent.DEADLINE_URGENCY).score == 5
    assert _component(result, ScoreComponent.INFORMATION_COMPLETENESS).score == 5


def test_v1_remains_replayable_while_v2_ignores_requirement_only_direction_terms() -> None:
    match_input = replace(
        _complete_input(),
        position_name="Legal Counsel",
        department="Legal Affairs",
        major="Law",
        requirements="Review contracts for Python services; no engineering duties.",
    )
    preferences = _matching_preferences()
    engine = DeterministicMatchingEngine()

    legacy = engine.evaluate(
        match_input,
        preferences,
        evaluated_at=NOW,
        score_version=LEGACY_SCORE_VERSION,
    )
    current = engine.evaluate(match_input, preferences, evaluated_at=NOW)

    assert legacy.score == 85
    assert _component(legacy, ScoreComponent.JOB_DIRECTION).score == 30
    assert current.score == 45
    assert _component(current, ScoreComponent.JOB_DIRECTION).score == 0
    assert _component(current, ScoreComponent.JOB_DIRECTION).rule == (
        "job-keyword-direct-fields-v2"
    )


def test_national_region_matches_any_explicit_region_preference() -> None:
    result = DeterministicMatchingEngine().evaluate(
        replace(_complete_input(), region="national"),
        replace(_matching_preferences(), regions=("beijing",)),
        evaluated_at=NOW,
    )

    assert _component(result, ScoreComponent.REGION).score == 25


def test_naive_times_and_unknown_versions_fail_before_scoring() -> None:
    engine = DeterministicMatchingEngine()
    with pytest.raises(ValueError, match="timezone"):
        engine.evaluate(
            _complete_input(), _matching_preferences(), evaluated_at=datetime(2026, 8, 30)
        )
    with pytest.raises(ValueError, match="Unsupported score version"):
        engine.evaluate(
            _complete_input(),
            _matching_preferences(),
            evaluated_at=NOW,
            score_version="unknown-v2",
        )


def test_each_component_persists_rule_inputs_score_and_explanation() -> None:
    result = DeterministicMatchingEngine().evaluate(
        _complete_input(),
        _matching_preferences(),
        evaluated_at=NOW,
    )

    payloads = [component.as_json() for component in result.components]
    assert all(
        set(payload) == {"component", "rule", "inputs", "score", "maximum", "explanation"}
        for payload in payloads
    )
    assert all(payload["inputs"] for payload in payloads)
    assert all(payload["explanation"] for payload in payloads)


def _complete_input() -> JobMatchInput:
    return JobMatchInput(
        position_id=7,
        post_id=5,
        recommendation_eligible=True,
        organization="Example State Group",
        organization_type="state_owned",
        region="shanghai",
        deadline=NOW + timedelta(days=2),
        title="2026 Campus Recruitment",
        source_url="https://example.invalid/jobs/7",
        position_name="Python Engineer",
        department="Data Platform",
        education="bachelor_or_above",
        major="Computer Science",
        requirements="Build data services",
    )


def _matching_preferences() -> PreferenceValues:
    return PreferenceValues(
        regions=("shanghai",),
        education="bachelor",
        majors=("computer science",),
        job_keywords=("python",),
        organization_types=("state_owned",),
    )


def _hard_filter(result: MatchEvaluation, rule: HardFilterRule) -> HardFilterDecision:
    return next(item for item in result.hard_filters if item.rule is rule)


def _component(result: MatchEvaluation, component: ScoreComponent) -> ComponentScore:
    return next(item for item in result.components if item.component is component)
