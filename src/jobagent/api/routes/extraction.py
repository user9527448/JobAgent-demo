"""Manual extraction quality-control operations."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field

from jobagent.api.dependencies import get_reparse_service
from jobagent.core.exceptions import PermanentJobAgentError, TransientJobAgentError
from jobagent.extraction import ExtractionWriteResult, ReparseOperations

router = APIRouter()


class ReparseRequest(BaseModel):
    """Explicit rule/extraction version for an idempotent reparse."""

    extraction_version: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )


class ReparseResponse(BaseModel):
    """Persisted extraction and validation outcome."""

    post_id: int
    position_ids: list[int]
    version: int
    extraction_version: str
    result_hash: str
    write_status: str
    previous_post_id: int | None
    review_status: str
    recommendation_eligible: bool
    validation_version: str
    validation_error_count: int
    validation_warning_count: int

    @classmethod
    def from_result(cls, result: ExtractionWriteResult) -> ReparseResponse:
        return cls(
            post_id=result.post_id,
            position_ids=list(result.position_ids),
            version=result.version,
            extraction_version=result.extraction_version,
            result_hash=result.result_hash,
            write_status=result.status.value,
            previous_post_id=result.previous_post_id,
            review_status=result.review_status.value,
            recommendation_eligible=result.recommendation_eligible,
            validation_version=result.validation_version,
            validation_error_count=result.validation_error_count,
            validation_warning_count=result.validation_warning_count,
        )


@router.post(
    "/documents/{document_id}/reparse",
    response_model=ReparseResponse,
)
async def reparse_document(
    document_id: Annotated[int, Path(gt=0)],
    request: ReparseRequest,
    service: Annotated[ReparseOperations, Depends(get_reparse_service)],
) -> ReparseResponse:
    """Reparse one immutable stored document with an explicit version."""
    try:
        result = await service.reparse(document_id, request.extraction_version)
    except PermanentJobAgentError as error:
        response_status = (
            status.HTTP_404_NOT_FOUND
            if error.code == "reparse.document_not_found"
            else status.HTTP_422_UNPROCESSABLE_CONTENT
        )
        raise HTTPException(status_code=response_status, detail=error.to_dict()) from error
    except TransientJobAgentError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error.to_dict(),
        ) from error
    return ReparseResponse.from_result(result)
