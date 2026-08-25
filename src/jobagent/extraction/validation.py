"""Deterministic quality validation for merged recruitment entities."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Final
from urllib.parse import urlsplit

from jobagent.extraction.contracts import FieldName
from jobagent.extraction.dictionaries import (
    CATEGORY_ALIASES,
    EDUCATION_ALIASES,
    REGION_ALIASES,
)
from jobagent.extraction.merging import (
    MergedEntityType,
    MergedExtraction,
    MergedField,
    MergedPosition,
)

VALIDATION_VERSION: Final = "validation-v1"

_REGION_VALUES: Final = frozenset(value for value, _aliases in REGION_ALIASES)
_EDUCATION_VALUES: Final = frozenset(value for value, _aliases in EDUCATION_ALIASES)
_CATEGORY_VALUES: Final = frozenset(value for value, _aliases in CATEGORY_ALIASES)
_SEVERE_CONFLICT_FIELDS: Final = frozenset(
    {
        FieldName.ORGANIZATION,
        FieldName.DEADLINE,
        FieldName.APPLY_URL,
        FieldName.EDUCATION,
    }
)


class ValidationSeverity(StrEnum):
    """Stable severity levels persisted for every quality finding."""

    WARNING = "warning"
    ERROR = "error"


class ReviewStatus(StrEnum):
    """Review state derived only from persisted validation findings."""

    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"
    BLOCKED = "blocked"


class ValidationCode(StrEnum):
    """Machine-readable quality failure reasons."""

    REQUIRED_FIELD_MISSING = "validation.required_field_missing"
    POSITION_MISSING = "validation.position_missing"
    DATE_RANGE_INVALID = "validation.date_range_invalid"
    URL_INVALID = "validation.url_invalid"
    ENUM_INVALID = "validation.enum_invalid"
    FIELD_CONFLICT = "validation.field_conflict"


@dataclass(frozen=True, slots=True)
class ValidationFinding:
    """One safe reason that an entity is blocked or requires review."""

    code: ValidationCode
    severity: ValidationSeverity
    entity_type: MergedEntityType
    entity_key: str
    reason: str
    field_name: FieldName | None = None

    def __post_init__(self) -> None:
        if not self.entity_key.strip() or not self.reason.strip():
            raise ValueError("Validation findings require an entity key and reason.")

    @property
    def issue_key(self) -> str:
        """Return a stable identity suitable for idempotent persistence."""
        identity = "|".join(
            (
                self.code.value,
                self.entity_type.value,
                self.entity_key,
                "" if self.field_name is None else self.field_name.value,
            )
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Complete deterministic review outcome for one merged extraction."""

    validation_version: str
    review_status: ReviewStatus
    recommendation_eligible: bool
    findings: tuple[ValidationFinding, ...] = ()

    @property
    def error_count(self) -> int:
        return sum(item.severity is ValidationSeverity.ERROR for item in self.findings)

    @property
    def warning_count(self) -> int:
        return sum(item.severity is ValidationSeverity.WARNING for item in self.findings)


class ExtractionValidator:
    """Validate required values and evidenced conflicts without guessing data."""

    def validate(self, merged: MergedExtraction) -> ValidationResult:
        findings: list[ValidationFinding] = []
        post_fields = {field.name: field for field in merged.post_fields}

        findings.extend(
            _finding(
                ValidationCode.REQUIRED_FIELD_MISSING,
                ValidationSeverity.ERROR,
                MergedEntityType.JOB_POST,
                "post",
                f"Required announcement field '{field_name.value}' is missing.",
                field_name,
            )
            for field_name in (
                FieldName.ORGANIZATION,
                FieldName.DEADLINE,
                FieldName.APPLY_URL,
            )
            if field_name not in post_fields
        )

        findings.extend(
            _finding(
                ValidationCode.REQUIRED_FIELD_MISSING,
                ValidationSeverity.WARNING,
                MergedEntityType.JOB_POST,
                "post",
                f"Recommended announcement field '{field_name.value}' is missing.",
                field_name,
            )
            for field_name in (FieldName.REGION, FieldName.CATEGORY)
            if field_name not in post_fields
        )

        _validate_date_range(post_fields, findings)
        _validate_url(post_fields, findings)
        _validate_post_enums(post_fields, findings)
        _validate_conflicts(
            MergedEntityType.JOB_POST,
            "post",
            tuple(post_fields.values()),
            findings,
        )

        if not merged.positions:
            findings.append(
                _finding(
                    ValidationCode.POSITION_MISSING,
                    ValidationSeverity.ERROR,
                    MergedEntityType.JOB_POST,
                    "post",
                    "At least one evidenced position record is required.",
                )
            )
        for position in merged.positions:
            _validate_position(position, findings)

        ordered = tuple(sorted(findings, key=_finding_sort_key))
        has_error = any(item.severity is ValidationSeverity.ERROR for item in ordered)
        if has_error:
            status = ReviewStatus.BLOCKED
        elif ordered:
            status = ReviewStatus.REVIEW_REQUIRED
        else:
            status = ReviewStatus.APPROVED
        return ValidationResult(
            validation_version=VALIDATION_VERSION,
            review_status=status,
            recommendation_eligible=not has_error,
            findings=ordered,
        )


def _validate_date_range(
    fields: dict[FieldName, MergedField],
    findings: list[ValidationFinding],
) -> None:
    start = fields.get(FieldName.START_AT)
    deadline = fields.get(FieldName.DEADLINE)
    if (
        start is not None
        and deadline is not None
        and isinstance(start.normalized_value, datetime)
        and isinstance(deadline.normalized_value, datetime)
        and start.normalized_value > deadline.normalized_value
    ):
        findings.append(
            _finding(
                ValidationCode.DATE_RANGE_INVALID,
                ValidationSeverity.ERROR,
                MergedEntityType.JOB_POST,
                "post",
                "Application start is later than the deadline.",
                FieldName.DEADLINE,
            )
        )


def _validate_url(
    fields: dict[FieldName, MergedField],
    findings: list[ValidationFinding],
) -> None:
    field = fields.get(FieldName.APPLY_URL)
    if field is None:
        return
    value = field.normalized_value
    try:
        parsed = urlsplit(value) if isinstance(value, str) else None
        hostname = None if parsed is None else parsed.hostname
        if parsed is not None:
            _validated_port = parsed.port
    except ValueError:
        parsed = None
        hostname = None
    if (
        parsed is None
        or parsed.scheme not in {"http", "https"}
        or hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        findings.append(
            _finding(
                ValidationCode.URL_INVALID,
                ValidationSeverity.ERROR,
                MergedEntityType.JOB_POST,
                "post",
                "Application URL must be an absolute HTTP(S) URL without user information.",
                FieldName.APPLY_URL,
            )
        )


def _validate_post_enums(
    fields: dict[FieldName, MergedField],
    findings: list[ValidationFinding],
) -> None:
    category = fields.get(FieldName.CATEGORY)
    if category is not None and category.normalized_value not in _CATEGORY_VALUES:
        findings.append(_enum_finding(MergedEntityType.JOB_POST, "post", FieldName.CATEGORY))
    region = fields.get(FieldName.REGION)
    if region is not None and not _valid_regions(region.normalized_value):
        findings.append(_enum_finding(MergedEntityType.JOB_POST, "post", FieldName.REGION))


def _validate_position(
    position: MergedPosition,
    findings: list[ValidationFinding],
) -> None:
    fields = {field.name: field for field in position.fields}
    for field_name, severity in (
        (FieldName.EDUCATION, ValidationSeverity.ERROR),
        (FieldName.HEADCOUNT, ValidationSeverity.WARNING),
        (FieldName.REGION, ValidationSeverity.WARNING),
    ):
        if field_name not in fields:
            findings.append(
                _finding(
                    ValidationCode.REQUIRED_FIELD_MISSING,
                    severity,
                    MergedEntityType.JOB_POSITION,
                    position.record_key,
                    f"Position field '{field_name.value}' is missing.",
                    field_name,
                )
            )
    education = fields.get(FieldName.EDUCATION)
    if education is not None and education.normalized_value not in _EDUCATION_VALUES:
        findings.append(
            _enum_finding(
                MergedEntityType.JOB_POSITION,
                position.record_key,
                FieldName.EDUCATION,
            )
        )
    region = fields.get(FieldName.REGION)
    if region is not None and not _valid_regions(region.normalized_value):
        findings.append(
            _enum_finding(
                MergedEntityType.JOB_POSITION,
                position.record_key,
                FieldName.REGION,
            )
        )
    _validate_conflicts(
        MergedEntityType.JOB_POSITION,
        position.record_key,
        tuple(fields.values()),
        findings,
    )


def _validate_conflicts(
    entity_type: MergedEntityType,
    entity_key: str,
    fields: tuple[MergedField, ...],
    findings: list[ValidationFinding],
) -> None:
    for field in fields:
        if not field.has_conflict:
            continue
        severity = (
            ValidationSeverity.ERROR
            if field.name in _SEVERE_CONFLICT_FIELDS
            else ValidationSeverity.WARNING
        )
        findings.append(
            _finding(
                ValidationCode.FIELD_CONFLICT,
                severity,
                entity_type,
                entity_key,
                f"Field '{field.name.value}' has contradictory evidenced values.",
                field.name,
            )
        )


def _valid_regions(value: object) -> bool:
    return (
        isinstance(value, tuple)
        and bool(value)
        and all(isinstance(item, str) and item in _REGION_VALUES for item in value)
    )


def _enum_finding(
    entity_type: MergedEntityType,
    entity_key: str,
    field_name: FieldName,
) -> ValidationFinding:
    return _finding(
        ValidationCode.ENUM_INVALID,
        ValidationSeverity.ERROR,
        entity_type,
        entity_key,
        f"Field '{field_name.value}' is outside the supported normalized dictionary.",
        field_name,
    )


def _finding(
    code: ValidationCode,
    severity: ValidationSeverity,
    entity_type: MergedEntityType,
    entity_key: str,
    reason: str,
    field_name: FieldName | None = None,
) -> ValidationFinding:
    return ValidationFinding(
        code=code,
        severity=severity,
        entity_type=entity_type,
        entity_key=entity_key,
        reason=reason,
        field_name=field_name,
    )


def _finding_sort_key(item: ValidationFinding) -> tuple[str, ...]:
    return (
        item.severity.value,
        item.entity_type.value,
        item.entity_key,
        "" if item.field_name is None else item.field_name.value,
        item.code.value,
    )
