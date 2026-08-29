"""Stable contracts for the single-user preference profile."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol, TypeAlias

RegionCode: TypeAlias = Literal[
    "national",
    "beijing",
    "tianjin",
    "hebei",
    "shanxi",
    "inner_mongolia",
    "liaoning",
    "jilin",
    "heilongjiang",
    "shanghai",
    "jiangsu",
    "zhejiang",
    "anhui",
    "fujian",
    "jiangxi",
    "shandong",
    "henan",
    "hubei",
    "hunan",
    "guangdong",
    "guangxi",
    "hainan",
    "chongqing",
    "sichuan",
    "guizhou",
    "yunnan",
    "tibet",
    "shaanxi",
    "gansu",
    "qinghai",
    "ningxia",
    "xinjiang",
    "hong_kong",
    "macau",
    "taiwan",
]
EducationLevel: TypeAlias = Literal[
    "no_requirement",
    "doctorate",
    "master_or_above",
    "master",
    "bachelor_or_above",
    "bachelor",
    "associate_or_above",
    "associate",
    "secondary_vocational",
    "high_school",
]
OrganizationType: TypeAlias = Literal[
    "government",
    "public_institution",
    "state_owned",
    "private",
    "foreign_enterprise",
]


@dataclass(frozen=True, slots=True)
class PreferenceValues:
    """Validated values whose empty collections mean no restriction."""

    regions: tuple[RegionCode, ...] = ()
    education: EducationLevel | None = None
    majors: tuple[str, ...] = ()
    job_keywords: tuple[str, ...] = ()
    organization_types: tuple[OrganizationType, ...] = ()
    exclusions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PreferenceSnapshot:
    """Persisted preference state returned by reads and updates."""

    values: PreferenceValues
    recompute_required: bool
    recompute_requested_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PreferenceOperations(Protocol):
    """Read/update boundary consumed by the HTTP API."""

    async def get(self) -> PreferenceSnapshot:
        """Return the singleton profile."""

    async def replace(
        self,
        values: PreferenceValues,
        *,
        trigger_recompute: bool,
    ) -> PreferenceSnapshot:
        """Replace all preference values and optionally request recomputation."""
