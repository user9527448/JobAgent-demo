"""Single-user preference read/update endpoints."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from typing import Annotated, Self

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

from jobagent.api.dependencies import get_preference_service
from jobagent.core import PermanentJobAgentError, TransientJobAgentError
from jobagent.preferences import (
    EducationLevel,
    OrganizationType,
    PreferenceOperations,
    PreferenceSnapshot,
    PreferenceValues,
    RegionCode,
)

router = APIRouter()
PreferenceText = Annotated[str, StringConstraints(min_length=1, max_length=100)]


class PreferenceFields(BaseModel):
    """Validated full preference document; every empty list means unrestricted."""

    regions: list[RegionCode] = Field(default_factory=list, max_length=35)
    education: EducationLevel | None = None
    majors: list[PreferenceText] = Field(default_factory=list, max_length=50)
    job_keywords: list[PreferenceText] = Field(default_factory=list, max_length=50)
    organization_types: list[OrganizationType] = Field(default_factory=list, max_length=5)
    exclusions: list[PreferenceText] = Field(default_factory=list, max_length=50)

    @field_validator("majors", "job_keywords", "exclusions", mode="before")
    @classmethod
    def normalize_text_items(cls, value: object) -> object:
        """Normalize Unicode and insignificant whitespace at the API boundary."""
        if not isinstance(value, list):
            return value
        return [
            " ".join(unicodedata.normalize("NFKC", item).split()) if isinstance(item, str) else item
            for item in value
        ]

    @model_validator(mode="after")
    def remove_duplicates(self) -> Self:
        """Keep deterministic source order while removing duplicate preferences."""
        self.regions = list(dict.fromkeys(self.regions))
        self.majors = _unique_text(self.majors)
        self.job_keywords = _unique_text(self.job_keywords)
        self.organization_types = list(dict.fromkeys(self.organization_types))
        self.exclusions = _unique_text(self.exclusions)
        return self

    def to_values(self) -> PreferenceValues:
        return PreferenceValues(
            regions=tuple(self.regions),
            education=self.education,
            majors=tuple(self.majors),
            job_keywords=tuple(self.job_keywords),
            organization_types=tuple(self.organization_types),
            exclusions=tuple(self.exclusions),
        )


class PreferenceUpdateRequest(PreferenceFields):
    """Full replacement request with an explicit downstream recomputation signal."""

    trigger_recompute: bool = True


class PreferenceResponse(PreferenceFields):
    """Persisted profile state and audit metadata."""

    recompute_required: bool
    recompute_requested_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_snapshot(cls, snapshot: PreferenceSnapshot) -> PreferenceResponse:
        return cls(
            regions=list(snapshot.values.regions),
            education=snapshot.values.education,
            majors=list(snapshot.values.majors),
            job_keywords=list(snapshot.values.job_keywords),
            organization_types=list(snapshot.values.organization_types),
            exclusions=list(snapshot.values.exclusions),
            recompute_required=snapshot.recompute_required,
            recompute_requested_at=snapshot.recompute_requested_at,
            created_at=snapshot.created_at,
            updated_at=snapshot.updated_at,
        )


@router.get("", response_model=PreferenceResponse)
async def read_preferences(
    service: Annotated[PreferenceOperations, Depends(get_preference_service)],
) -> PreferenceResponse:
    """Read the singleton profile."""
    try:
        snapshot = await service.get()
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _preference_http_error(error) from error
    return PreferenceResponse.from_snapshot(snapshot)


@router.put("", response_model=PreferenceResponse)
async def update_preferences(
    request: PreferenceUpdateRequest,
    service: Annotated[PreferenceOperations, Depends(get_preference_service)],
) -> PreferenceResponse:
    """Replace the singleton profile and optionally request full recomputation."""
    try:
        snapshot = await service.replace(
            request.to_values(),
            trigger_recompute=request.trigger_recompute,
        )
    except (PermanentJobAgentError, TransientJobAgentError) as error:
        raise _preference_http_error(error) from error
    return PreferenceResponse.from_snapshot(snapshot)


def _unique_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = unicodedata.normalize("NFKC", value).casefold()
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _preference_http_error(
    error: PermanentJobAgentError | TransientJobAgentError,
) -> HTTPException:
    response_status = (
        status.HTTP_503_SERVICE_UNAVAILABLE
        if isinstance(error, TransientJobAgentError)
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    return HTTPException(status_code=response_status, detail=error.to_dict())
