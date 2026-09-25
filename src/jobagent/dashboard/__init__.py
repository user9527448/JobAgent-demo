"""Read-only evidence aggregation for the product dashboard."""

from .contracts import (
    BriefingSnapshot,
    DashboardOperations,
    DeliveryEvidence,
    DeliveryEvidenceState,
    PipelineRunEvidence,
    ReportEvidence,
    ReportItemEvidence,
    ScheduleEvidence,
    StageEvidence,
)
from .persistence import SqlAlchemyDashboardService

__all__ = [
    "BriefingSnapshot",
    "DashboardOperations",
    "DeliveryEvidence",
    "DeliveryEvidenceState",
    "PipelineRunEvidence",
    "ReportEvidence",
    "ReportItemEvidence",
    "ScheduleEvidence",
    "SqlAlchemyDashboardService",
    "StageEvidence",
]
