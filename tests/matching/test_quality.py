"""JAI-025 fixed-fixture Top 20 quality comparison."""

from pathlib import Path

import pytest

from jobagent.matching import (
    CURRENT_SCORE_VERSION,
    LEGACY_SCORE_VERSION,
    compare_quality,
    load_quality_review_set,
)

FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "matching_quality" / "review-set.json"


def test_review_set_contains_sixty_sanitized_explicit_labels() -> None:
    review_set = load_quality_review_set(FIXTURE_PATH)

    assert review_set.schema_version == "jai-025-review-set-v1"
    assert len(review_set.cases) == 60
    assert sum(case.label == "relevant" for case in review_set.cases) == 30
    assert all(
        case.match_input.source_url
        and case.match_input.source_url.startswith("https://example.invalid/jai-025/")
        for case in review_set.cases
    )
    assert all(case.reason_category and case.rationale for case in review_set.cases)


def test_v2_removes_obvious_top_20_false_positives_and_improves_recall() -> None:
    comparison = compare_quality(load_quality_review_set(FIXTURE_PATH))

    assert comparison.baseline.score_version == LEGACY_SCORE_VERSION
    assert comparison.candidate.score_version == CURRENT_SCORE_VERSION
    assert comparison.baseline.true_positive_count == 15
    assert comparison.baseline.false_positive_count == 5
    assert comparison.baseline.miss_count == 15
    assert comparison.baseline.precision_at_k == 0.75
    assert comparison.baseline.recall_at_k == 0.5
    assert {item.reason_category for item in comparison.baseline.false_positives} == {
        "requirements_context_false_positive"
    }
    assert comparison.candidate.true_positive_count == 20
    assert comparison.candidate.false_positive_count == 0
    assert comparison.candidate.miss_count == 10
    assert comparison.candidate.precision_at_k == 1.0
    assert comparison.candidate.recall_at_k == 0.666667
    assert comparison.as_json()["precision_at_k_delta"] == 0.25
    assert comparison.as_json()["recall_at_k_delta"] == 0.166667


def test_ranking_and_serialized_comparison_are_deterministic() -> None:
    review_set = load_quality_review_set(FIXTURE_PATH)

    first = compare_quality(review_set)
    second = compare_quality(review_set)

    assert first == second
    assert first.as_json() == second.as_json()
    assert [item.rank for item in first.candidate.top_items] == list(range(1, 21))


@pytest.mark.parametrize("top_k", [0, 61])
def test_top_k_must_fit_the_review_set(top_k: int) -> None:
    with pytest.raises(ValueError, match="Top-K"):
        compare_quality(load_quality_review_set(FIXTURE_PATH), top_k=top_k)
