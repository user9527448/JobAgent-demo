"""Typed deterministic extraction results with mandatory source evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TypeAlias

from jobagent.parsers import EvidenceLocation, ParseSource


class FieldName(StrEnum):
    """Stable normalized fields produced by deterministic extraction."""

    START_AT = "start_at"
    DEADLINE = "deadline"
    REGION = "region"
    ORGANIZATION = "organization"
    APPLY_URL = "apply_url"
    HEADCOUNT = "headcount"
    EDUCATION = "education"
    CATEGORY = "category"


class ExtractionErrorCode(StrEnum):
    """Stable diagnostics for rejected or ambiguous source values."""

    INVALID_DATE = "extraction.invalid_date"
    DATE_RANGE_INVERTED = "extraction.date_range_inverted"
    AMBIGUOUS_DATE_RANGE = "extraction.ambiguous_date_range"
    INVALID_URL = "extraction.invalid_url"
    INVALID_HEADCOUNT = "extraction.invalid_headcount"
    UNKNOWN_ENUM = "extraction.unknown_enum"


NormalizedValue: TypeAlias = datetime | int | str | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExtractionEvidence:
    """Exact source coordinates and quote supporting one extracted value."""

    location: EvidenceLocation
    quote: str

    def __post_init__(self) -> None:
        if not self.quote.strip():
            raise ValueError("Extraction evidence quote cannot be empty.")


@dataclass(frozen=True, slots=True)
class ExtractedField:
    """One raw source value paired with its deterministic normalized value."""

    name: FieldName
    raw_value: str
    normalized_value: NormalizedValue
    evidence: ExtractionEvidence
    rule_id: str

    def __post_init__(self) -> None:
        if not self.raw_value.strip():
            raise ValueError("Extracted raw values cannot be empty.")
        if not self.rule_id.strip():
            raise ValueError("Extraction rule ID cannot be empty.")
        if self.name in {FieldName.START_AT, FieldName.DEADLINE}:
            if not isinstance(self.normalized_value, datetime):
                raise TypeError("Normalized date fields must be datetime values.")
            if self.normalized_value.tzinfo is None:
                raise ValueError("Normalized date fields must be timezone-aware.")
            if self.normalized_value.utcoffset() is None:
                raise ValueError("Normalized date fields must have a UTC offset.")
            if self.normalized_value.utcoffset() != timedelta(0):
                raise ValueError("Normalized date fields must use UTC.")
        elif self.name is FieldName.HEADCOUNT:
            if not isinstance(self.normalized_value, int) or self.normalized_value <= 0:
                raise ValueError("Normalized headcount must be a positive integer.")
        elif self.name is FieldName.REGION:
            if not isinstance(self.normalized_value, tuple) or not self.normalized_value:
                raise ValueError("Normalized regions must be a non-empty tuple.")
            if any(not isinstance(value, str) or not value for value in self.normalized_value):
                raise ValueError("Every normalized region code must be non-empty text.")
        elif not isinstance(self.normalized_value, str) or not self.normalized_value:
            raise ValueError("Normalized text fields cannot be empty.")


@dataclass(frozen=True, slots=True)
class ExtractionIssue:
    """A safe rejection that retains the unsupported source value and evidence."""

    code: ExtractionErrorCode
    message: str
    raw_values: tuple[str, ...]
    evidence: tuple[ExtractionEvidence, ...]
    field_name: FieldName | None = None

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Extraction issue message cannot be empty.")
        if not self.raw_values or any(not value.strip() for value in self.raw_values):
            raise ValueError("Extraction issues must retain non-empty raw values.")
        if not self.evidence:
            raise ValueError("Extraction issues must retain source evidence.")


@dataclass(frozen=True, slots=True)
class ExtractionRecord:
    """Fields and diagnostics extracted from one text block or table row."""

    location: EvidenceLocation
    fields: tuple[ExtractedField, ...] = ()
    issues: tuple[ExtractionIssue, ...] = ()

    def __post_init__(self) -> None:
        if not self.fields and not self.issues:
            raise ValueError("Extraction records cannot be empty.")
        source = self.location.source
        for extracted in self.fields:
            if extracted.evidence.location.source != source:
                raise ValueError("Extracted fields cannot mix parser sources.")
        for issue in self.issues:
            if any(evidence.location.source != source for evidence in issue.evidence):
                raise ValueError("Extraction issues cannot mix parser sources.")


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    """Deterministic fields grouped by their original parser block or row."""

    source: ParseSource
    records: tuple[ExtractionRecord, ...] = ()
    extractor_version: str = "deterministic-v1"

    def __post_init__(self) -> None:
        if not self.extractor_version.strip():
            raise ValueError("Extractor version cannot be empty.")
        if any(record.location.source != self.source for record in self.records):
            raise ValueError("Extraction records cannot mix parser sources.")

    @property
    def fields(self) -> tuple[ExtractedField, ...]:
        """Return all fields in stable source order."""
        return tuple(field for record in self.records for field in record.fields)

    @property
    def issues(self) -> tuple[ExtractionIssue, ...]:
        """Return all diagnostics in stable source order."""
        return tuple(issue for record in self.records for issue in record.issues)
