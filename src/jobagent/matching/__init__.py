"""Deterministic matching contracts, engine, and recomputation persistence."""

from .contracts import (
    ComponentScore,
    HardFilterDecision,
    HardFilterRule,
    JobMatchInput,
    MatchEvaluation,
    ScoreComponent,
)
from .engine import (
    CURRENT_SCORE_VERSION,
    LEGACY_SCORE_VERSION,
    SUPPORTED_SCORE_VERSIONS,
    DeterministicMatchingEngine,
    education_rank,
)
from .persistence import MatchingRecomputeResult, RecomputeStatus, SqlAlchemyMatchingService
from .quality import (
    QualityComparison,
    QualityReviewCase,
    QualityReviewSet,
    QualityVersionReview,
    RankedQualityCase,
    RelevanceLabel,
    compare_quality,
    load_quality_review_set,
)

__all__ = [
    "CURRENT_SCORE_VERSION",
    "LEGACY_SCORE_VERSION",
    "SUPPORTED_SCORE_VERSIONS",
    "ComponentScore",
    "DeterministicMatchingEngine",
    "HardFilterDecision",
    "HardFilterRule",
    "JobMatchInput",
    "MatchEvaluation",
    "MatchingRecomputeResult",
    "QualityComparison",
    "QualityReviewCase",
    "QualityReviewSet",
    "QualityVersionReview",
    "RankedQualityCase",
    "RecomputeStatus",
    "RelevanceLabel",
    "ScoreComponent",
    "SqlAlchemyMatchingService",
    "compare_quality",
    "education_rank",
    "load_quality_review_set",
]
