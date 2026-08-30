"""Deterministic matching contracts, engine, and recomputation persistence."""

from .contracts import (
    ComponentScore,
    HardFilterDecision,
    HardFilterRule,
    JobMatchInput,
    MatchEvaluation,
    ScoreComponent,
)
from .engine import CURRENT_SCORE_VERSION, DeterministicMatchingEngine, education_rank
from .persistence import MatchingRecomputeResult, RecomputeStatus, SqlAlchemyMatchingService

__all__ = [
    "CURRENT_SCORE_VERSION",
    "ComponentScore",
    "DeterministicMatchingEngine",
    "HardFilterDecision",
    "HardFilterRule",
    "JobMatchInput",
    "MatchEvaluation",
    "MatchingRecomputeResult",
    "RecomputeStatus",
    "ScoreComponent",
    "SqlAlchemyMatchingService",
    "education_rank",
]
