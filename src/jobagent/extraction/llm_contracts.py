"""Strict, evidence-bound contracts for optional LLM extraction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Protocol, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from jobagent.extraction.contracts import FieldName
from jobagent.parsers import EvidenceLocation, ParseSource

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
NonEmptyTextList = Annotated[list[NonEmptyText], Field(min_length=1)]
LlmNormalizedValue: TypeAlias = NonEmptyText | StrictInt | NonEmptyTextList


class LlmFieldCandidate(BaseModel):
    """One model-proposed field that still requires downstream reconciliation."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    name: FieldName
    raw_value: NonEmptyText
    normalized_value: LlmNormalizedValue
    evidence_quote: NonEmptyText


class LlmExtractionPayload(BaseModel):
    """The only accepted structured provider output."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    candidates: list[LlmFieldCandidate] = Field(default_factory=list, max_length=100)


@dataclass(frozen=True, slots=True)
class LlmEvidenceFragment:
    """One bounded parser fragment supplied to the model as untrusted data."""

    location: EvidenceLocation
    text: str

    def __post_init__(self) -> None:
        if not self.text.strip():
            raise ValueError("LLM evidence fragment text cannot be empty.")


@dataclass(frozen=True, slots=True)
class LlmExtractionRequest:
    """One logical extraction task with traceable, single-source input."""

    task_id: str
    source: ParseSource
    fragments: tuple[LlmEvidenceFragment, ...]

    def __post_init__(self) -> None:
        if not self.task_id.strip():
            raise ValueError("LLM extraction task ID cannot be empty.")
        if not self.fragments:
            raise ValueError("LLM extraction requires at least one evidence fragment.")
        if any(fragment.location.source != self.source for fragment in self.fragments):
            raise ValueError("LLM extraction fragments cannot mix parser sources.")


@dataclass(frozen=True, slots=True)
class LlmProviderRequest:
    """Provider-neutral request carrying the strict output schema."""

    model: str
    prompt_version: str
    instructions: str
    input_text: str
    output_schema: dict[str, object]
    max_output_tokens: int

    def __post_init__(self) -> None:
        if not self.model.strip() or not self.prompt_version.strip():
            raise ValueError("LLM model and prompt version cannot be empty.")
        if not self.instructions.strip() or not self.input_text.strip():
            raise ValueError("LLM instructions and input cannot be empty.")
        if self.max_output_tokens <= 0:
            raise ValueError("LLM max output tokens must be positive.")


@dataclass(frozen=True, slots=True)
class LlmUsage:
    """Provider-reported token usage for one successful HTTP response."""

    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.input_tokens, self.output_tokens, self.total_tokens) < 0:
            raise ValueError("LLM token usage cannot be negative.")
        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("LLM total tokens cannot be below input plus output tokens.")


@dataclass(frozen=True, slots=True)
class LlmProviderResponse:
    """Raw provider text and usage, before business-safe validation."""

    output_text: str
    usage: LlmUsage

    def __post_init__(self) -> None:
        if not self.output_text.strip():
            raise ValueError("LLM provider output text cannot be empty.")


class LlmProvider(Protocol):
    """Replaceable provider boundary used by the extraction service."""

    name: str

    async def complete(self, request: LlmProviderRequest) -> LlmProviderResponse:
        """Return one raw structured-output response or raise a safe provider error."""


class LlmCallStatus(StrEnum):
    """Stable result state recorded for every logical extraction request."""

    COMPLETED = "completed"
    INVALID_OUTPUT = "invalid_output"
    PROVIDER_ERROR = "provider_error"
    QUEUED_BUDGET = "queued_budget"


@dataclass(frozen=True, slots=True)
class LlmCallRecord:
    """Auditable model, prompt, usage, cost, attempt, and status metadata."""

    task_id: str
    provider: str
    model: str
    prompt_version: str
    status: LlmCallStatus
    attempts: int
    usage: LlmUsage
    estimated_cost_usd: Decimal
    started_at: datetime
    finished_at: datetime
    error_code: str | None = None

    def __post_init__(self) -> None:
        if not self.task_id.strip() or not self.provider.strip():
            raise ValueError("LLM call task and provider cannot be empty.")
        if not self.model.strip() or not self.prompt_version.strip():
            raise ValueError("LLM call model and prompt version cannot be empty.")
        if self.attempts < 0:
            raise ValueError("LLM call attempts cannot be negative.")
        if self.estimated_cost_usd < 0:
            raise ValueError("LLM call cost cannot be negative.")
        if self.started_at.tzinfo is None or self.finished_at.tzinfo is None:
            raise ValueError("LLM call timestamps must be timezone-aware.")
        if self.finished_at < self.started_at:
            raise ValueError("LLM call finish cannot precede its start.")


@dataclass(frozen=True, slots=True)
class LlmPendingTask:
    """A budget-blocked request retained for a later worker run."""

    request: LlmExtractionRequest
    queued_at: datetime
    reason: str = "daily_budget_exhausted"


@dataclass(frozen=True, slots=True)
class LlmExtractionOutcome:
    """Validated candidates or a non-business result state and its call record."""

    record: LlmCallRecord
    payload: LlmExtractionPayload | None = None

    def __post_init__(self) -> None:
        if self.record.status is LlmCallStatus.COMPLETED and self.payload is None:
            raise ValueError("Completed LLM extraction requires a validated payload.")
        if self.record.status is not LlmCallStatus.COMPLETED and self.payload is not None:
            raise ValueError("Non-completed LLM extraction cannot expose a payload.")


class LlmCallRecorder(Protocol):
    """Pluggable sink for logical call metadata without defining DB persistence."""

    async def record(self, record: LlmCallRecord) -> None:
        """Record one logical extraction outcome."""


class LlmPendingQueue(Protocol):
    """Pluggable queue for requests blocked by the daily budget."""

    async def enqueue(self, task: LlmPendingTask) -> None:
        """Retain one request for a later run."""
