"""JAI-020 deterministic validation and review-state checks."""

from datetime import UTC, datetime
from decimal import Decimal

from jobagent.extraction import (
    ExtractionMethod,
    ExtractionValidator,
    FieldName,
    MergedEvidence,
    MergedExtraction,
    MergedField,
    MergedPosition,
    ReviewStatus,
    ValidationCode,
    ValidationSeverity,
)
from jobagent.parsers import LineRangeLocation, ParseSource, ParseSourceType

SOURCE = ParseSource(
    source_type=ParseSourceType.DOCUMENT,
    source_id=19,
    source_name="announcement.txt",
    media_type="text/plain",
)
LOCATION = LineRangeLocation(SOURCE, start_line=1, end_line=3)


def test_complete_extraction_is_approved_and_recommendation_eligible() -> None:
    result = ExtractionValidator().validate(_complete_extraction())

    assert result.review_status is ReviewStatus.APPROVED
    assert result.recommendation_eligible is True
    assert result.findings == ()
    assert result.error_count == result.warning_count == 0


def test_missing_required_values_are_recorded_and_block_recommendations() -> None:
    merged = MergedExtraction(document_id=19, extraction_version="validation-missing-v1")

    result = ExtractionValidator().validate(merged)

    assert result.review_status is ReviewStatus.BLOCKED
    assert result.recommendation_eligible is False
    assert result.error_count == 4
    assert result.warning_count == 2
    assert {finding.code for finding in result.findings} == {
        ValidationCode.REQUIRED_FIELD_MISSING,
        ValidationCode.POSITION_MISSING,
    }
    assert all(finding.reason and len(finding.issue_key) == 64 for finding in result.findings)


def test_noncritical_missing_values_require_review_without_blocking() -> None:
    merged = MergedExtraction(
        document_id=19,
        extraction_version="validation-warning-v1",
        post_fields=(
            _field(FieldName.ORGANIZATION, "单位"),
            _field(FieldName.DEADLINE, datetime(2026, 9, 1, tzinfo=UTC)),
            _field(FieldName.APPLY_URL, "https://apply.example.invalid/jobs"),
        ),
        positions=(
            MergedPosition(
                record_key="position:1",
                fields=(_field(FieldName.EDUCATION, "bachelor"),),
            ),
        ),
    )

    result = ExtractionValidator().validate(merged)

    assert result.review_status is ReviewStatus.REVIEW_REQUIRED
    assert result.recommendation_eligible is True
    assert result.error_count == 0
    assert result.warning_count == 4
    assert all(item.severity is ValidationSeverity.WARNING for item in result.findings)


def test_invalid_date_url_and_enums_are_severe() -> None:
    merged = MergedExtraction(
        document_id=19,
        extraction_version="validation-invalid-v1",
        post_fields=(
            _field(FieldName.ORGANIZATION, "单位"),
            _field(FieldName.START_AT, datetime(2026, 9, 2, tzinfo=UTC)),
            _field(FieldName.DEADLINE, datetime(2026, 9, 1, tzinfo=UTC)),
            _field(FieldName.APPLY_URL, "ftp://apply.example.invalid/jobs"),
            _field(FieldName.REGION, ("unknown",)),
            _field(FieldName.CATEGORY, "unknown"),
        ),
        positions=(
            MergedPosition(
                record_key="position:1",
                fields=(
                    _field(FieldName.EDUCATION, "unknown"),
                    _field(FieldName.HEADCOUNT, 1),
                    _field(FieldName.REGION, ("beijing",)),
                ),
            ),
        ),
    )

    result = ExtractionValidator().validate(merged)

    assert result.review_status is ReviewStatus.BLOCKED
    assert result.recommendation_eligible is False
    assert {item.code for item in result.findings} == {
        ValidationCode.DATE_RANGE_INVALID,
        ValidationCode.URL_INVALID,
        ValidationCode.ENUM_INVALID,
    }
    assert result.error_count == 5


def test_malformed_url_becomes_a_finding_instead_of_escaping_validation() -> None:
    merged = _complete_extraction()
    fields = tuple(
        _field(FieldName.APPLY_URL, "https://[broken") if item.name is FieldName.APPLY_URL else item
        for item in merged.post_fields
    )

    result = ExtractionValidator().validate(
        MergedExtraction(
            document_id=merged.document_id,
            extraction_version="validation-malformed-url-v1",
            post_fields=fields,
            positions=merged.positions,
        )
    )

    assert result.review_status is ReviewStatus.BLOCKED
    assert [item.code for item in result.findings] == [ValidationCode.URL_INVALID]


def test_conflicts_have_field_specific_severity_and_stable_identity() -> None:
    merged = _complete_extraction(
        organization=_field(FieldName.ORGANIZATION, "甲单位", conflicting_value="乙单位"),
        region=_field(FieldName.REGION, ("beijing",), conflicting_value=("shanghai",)),
    )

    first = ExtractionValidator().validate(merged)
    second = ExtractionValidator().validate(merged)

    conflicts = [item for item in first.findings if item.code is ValidationCode.FIELD_CONFLICT]
    assert [(item.field_name, item.severity) for item in conflicts] == [
        (FieldName.ORGANIZATION, ValidationSeverity.ERROR),
        (FieldName.REGION, ValidationSeverity.WARNING),
    ]
    assert first.review_status is ReviewStatus.BLOCKED
    assert first.recommendation_eligible is False
    assert [item.issue_key for item in first.findings] == [
        item.issue_key for item in second.findings
    ]


def _complete_extraction(
    *,
    organization: MergedField | None = None,
    region: MergedField | None = None,
) -> MergedExtraction:
    return MergedExtraction(
        document_id=19,
        extraction_version="validation-complete-v1",
        post_fields=(
            organization or _field(FieldName.ORGANIZATION, "单位"),
            _field(FieldName.DEADLINE, datetime(2026, 9, 1, tzinfo=UTC)),
            _field(FieldName.APPLY_URL, "https://apply.example.invalid/jobs"),
            region or _field(FieldName.REGION, ("beijing",)),
            _field(FieldName.CATEGORY, "campus"),
        ),
        positions=(
            MergedPosition(
                record_key="position:1",
                fields=(
                    _field(FieldName.EDUCATION, "bachelor"),
                    _field(FieldName.HEADCOUNT, 1),
                    _field(FieldName.REGION, ("beijing",)),
                ),
            ),
        ),
    )


def _field(
    name: FieldName,
    value: datetime | int | str | tuple[str, ...],
    *,
    conflicting_value: datetime | int | str | tuple[str, ...] | None = None,
) -> MergedField:
    evidence = [
        MergedEvidence(
            field_name=name,
            raw_value=str(value),
            normalized_value=value,
            location=LOCATION,
            quote=str(value),
            method=ExtractionMethod.DETERMINISTIC,
            extractor_version="test-v1",
            confidence=Decimal("1.0000"),
            selected=True,
            conflict=False,
        )
    ]
    if conflicting_value is not None:
        evidence.append(
            MergedEvidence(
                field_name=name,
                raw_value=str(conflicting_value),
                normalized_value=conflicting_value,
                location=LineRangeLocation(SOURCE, start_line=4, end_line=4),
                quote=str(conflicting_value),
                method=ExtractionMethod.DETERMINISTIC,
                extractor_version="test-v1",
                confidence=Decimal("1.0000"),
                selected=False,
                conflict=True,
            )
        )
    return MergedField(name=name, normalized_value=value, evidence=tuple(evidence))
