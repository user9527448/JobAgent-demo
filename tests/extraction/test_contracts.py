from datetime import UTC, datetime, timedelta, timezone

import pytest

from jobagent.extraction import (
    ExtractedField,
    ExtractionEvidence,
    ExtractionRecord,
    ExtractionResult,
    FieldName,
)
from jobagent.parsers import PageLocation, ParseSource, ParseSourceType


def _source(source_id: int = 1) -> ParseSource:
    return ParseSource(
        source_type=ParseSourceType.ATTACHMENT,
        source_id=source_id,
        source_name=f"source-{source_id}.pdf",
        media_type="application/pdf",
    )


def test_extracted_field_requires_raw_normalized_and_evidence() -> None:
    source = _source()
    evidence = ExtractionEvidence(
        location=PageLocation(source=source, page_number=2),
        quote="截止日期\uff1a2026-09-01",
    )

    extracted = ExtractedField(
        name=FieldName.DEADLINE,
        raw_value="2026-09-01",
        normalized_value=datetime(2026, 9, 1, 15, 59, 59, 999999, tzinfo=UTC),
        evidence=evidence,
        rule_id="date.label.deadline",
    )

    assert extracted.raw_value == "2026-09-01"
    assert isinstance(extracted.normalized_value, datetime)
    assert extracted.normalized_value.tzinfo is UTC
    assert isinstance(extracted.evidence.location, PageLocation)
    assert extracted.evidence.location.page_number == 2


def test_date_fields_reject_naive_datetimes() -> None:
    source = _source()

    with pytest.raises(ValueError, match="timezone-aware"):
        ExtractedField(
            name=FieldName.START_AT,
            raw_value="2026-09-01",
            normalized_value=datetime(2026, 9, 1),
            evidence=ExtractionEvidence(
                location=PageLocation(source=source, page_number=1),
                quote="2026-09-01",
            ),
            rule_id="date.test",
        )


def test_date_fields_reject_non_utc_normalized_datetimes() -> None:
    source = _source()

    with pytest.raises(ValueError, match="must use UTC"):
        ExtractedField(
            name=FieldName.DEADLINE,
            raw_value="2026-09-01 17:00 +08:00",
            normalized_value=datetime(
                2026,
                9,
                1,
                17,
                tzinfo=timezone(timedelta(hours=8)),
            ),
            evidence=ExtractionEvidence(
                location=PageLocation(source=source, page_number=1),
                quote="2026-09-01 17:00 +08:00",
            ),
            rule_id="date.test",
        )


def test_extraction_result_rejects_mixed_sources() -> None:
    source = _source(1)
    other = _source(2)
    record = ExtractionRecord(
        location=PageLocation(source=source, page_number=1),
        fields=(
            ExtractedField(
                name=FieldName.HEADCOUNT,
                raw_value="2",
                normalized_value=2,
                evidence=ExtractionEvidence(
                    location=PageLocation(source=source, page_number=1),
                    quote="2",
                ),
                rule_id="headcount.test",
            ),
        ),
    )

    with pytest.raises(ValueError, match="cannot mix"):
        ExtractionResult(source=other, records=(record,))
