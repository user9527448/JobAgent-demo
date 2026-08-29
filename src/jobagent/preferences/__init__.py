"""Single-user preference contracts and persistence."""

from jobagent.preferences.contracts import (
    EducationLevel,
    OrganizationType,
    PreferenceOperations,
    PreferenceSnapshot,
    PreferenceValues,
    RegionCode,
)
from jobagent.preferences.persistence import SqlAlchemyPreferenceRepository

__all__ = [
    "EducationLevel",
    "OrganizationType",
    "PreferenceOperations",
    "PreferenceSnapshot",
    "PreferenceValues",
    "RegionCode",
    "SqlAlchemyPreferenceRepository",
]
