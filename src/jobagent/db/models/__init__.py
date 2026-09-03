"""Public ORM model registry imported by Alembic and repositories."""

from jobagent.db.models.base import Base, UTCDateTime
from jobagent.db.models.entities import (
    Attachment,
    CrawlRun,
    DailyReportSnapshot,
    FieldEvidence,
    JobPosition,
    JobPost,
    MatchResult,
    RawDocument,
    Source,
    UserPreference,
    ValidationIssue,
)

__all__ = [
    "Attachment",
    "Base",
    "CrawlRun",
    "DailyReportSnapshot",
    "FieldEvidence",
    "JobPosition",
    "JobPost",
    "MatchResult",
    "RawDocument",
    "Source",
    "UTCDateTime",
    "UserPreference",
    "ValidationIssue",
]
