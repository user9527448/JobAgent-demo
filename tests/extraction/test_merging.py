"""Deterministic precedence and conflict-retention tests for JAI-019."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from jobagent.extraction import (
    ExtractedField,
    ExtractionEvidence,
    ExtractionMergeInput,
    ExtractionMerger,
    ExtractionMethod,
    ExtractionRecord,
    ExtractionResult,
    FieldName,
    LlmEvidenceFragment,
    LlmExtractionPayload,
    LlmFieldCandidate,
    LlmMergeContribution,
    normalized_json_value,
)
from jobagent.parsers import (
    CellRangeLocation,
    LineRangeLocation,
    ParseSource,
    ParseSourceType,
)


def _source(source_type: ParseSourceType, source_id: int) -> ParseSource:
    return ParseSource(
        source_type=source_type,
        source_id=source_id,
        source_name="announcement.html" if source_type is ParseSourceType.DOCUMENT else "jobs.xlsx",
        media_type="text/html"
        if source_type is ParseSourceType.DOCUMENT
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _field(
    name: FieldName,
    raw_value: str,
    normalized_value: datetime | int | str | tuple[str, ...],
    location: LineRangeLocation | CellRangeLocation,
) -> ExtractedField:
    return ExtractedField(
        name=name,
        raw_value=raw_value,
        normalized_value=normalized_value,
        evidence=ExtractionEvidence(location=location, quote=raw_value),
        rule_id=f"test.{name.value}",
    )


def _result(
    source: ParseSource,
    location: LineRangeLocation | CellRangeLocation,
    *fields: ExtractedField,
) -> ExtractionResult:
    return ExtractionResult(
        source=source,
        records=(ExtractionRecord(location=location, fields=fields),),
        extractor_version="deterministic-test-v1",
    )


def test_body_wins_post_conflict_while_attachment_materializes_position() -> None:
    document = _source(ParseSourceType.DOCUMENT, 10)
    attachment = _source(ParseSourceType.ATTACHMENT, 20)
    body_location = LineRangeLocation(document, start_line=3, end_line=4)
    row_location = CellRangeLocation(attachment, "岗位表", "A2", "C2")
    body = _result(
        document,
        body_location,
        _field(FieldName.ORGANIZATION, "示例单位", "示例单位", body_location),
        _field(FieldName.REGION, "北京", ("CN-11",), body_location),
    )
    table = _result(
        attachment,
        row_location,
        _field(FieldName.REGION, "上海", ("CN-31",), row_location),
        _field(FieldName.HEADCOUNT, "6人", 6, row_location),
        _field(FieldName.EDUCATION, "本科及以上", "bachelor_or_above", row_location),
    )

    merged = ExtractionMerger().merge(
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            deterministic_results=(table, body),
        )
    )

    post_fields = {field.name: field for field in merged.post_fields}
    assert post_fields[FieldName.ORGANIZATION].normalized_value == "示例单位"
    assert post_fields[FieldName.REGION].normalized_value == ("CN-11",)
    assert post_fields[FieldName.REGION].has_conflict is True
    assert [item.selected for item in post_fields[FieldName.REGION].evidence] == [True, False]
    assert post_fields[FieldName.REGION].evidence[1].conflict is True

    assert len(merged.positions) == 1
    position_fields = {field.name: field for field in merged.positions[0].fields}
    assert position_fields[FieldName.REGION].normalized_value == ("CN-31",)
    assert position_fields[FieldName.HEADCOUNT].normalized_value == 6
    assert position_fields[FieldName.EDUCATION].normalized_value == "bachelor_or_above"
    assert all(
        evidence.location.source.source_type is ParseSourceType.ATTACHMENT
        for field in position_fields.values()
        for evidence in field.evidence
    )


def test_deterministic_attachment_beats_llm_document_but_both_evidence_remains() -> None:
    document = _source(ParseSourceType.DOCUMENT, 10)
    attachment = _source(ParseSourceType.ATTACHMENT, 20)
    row_location = CellRangeLocation(attachment, "岗位表", "A2", "A2")
    rule = _result(
        attachment,
        row_location,
        _field(FieldName.ORGANIZATION, "规则单位", "规则单位", row_location),
    )
    fragment_location = LineRangeLocation(document, start_line=1, end_line=1)
    llm = LlmMergeContribution(
        source=document,
        fragments=(
            LlmEvidenceFragment(
                location=fragment_location,
                text="招聘主体可能写作: 模型单位",
            ),
        ),
        payload=LlmExtractionPayload(
            candidates=[
                LlmFieldCandidate(
                    name=FieldName.ORGANIZATION,
                    raw_value="模型单位",
                    normalized_value="模型单位",
                    evidence_quote="招聘主体可能写作: 模型单位",
                )
            ]
        ),
        extractor_version="llm:model:prompt-v1",
    )

    merged = ExtractionMerger().merge(
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            deterministic_results=(rule,),
            llm_contributions=(llm,),
        )
    )

    organization = next(
        field for field in merged.post_fields if field.name is FieldName.ORGANIZATION
    )
    assert organization.normalized_value == "规则单位"
    assert organization.has_conflict is True
    assert [item.method for item in organization.evidence] == [
        ExtractionMethod.DETERMINISTIC,
        ExtractionMethod.LLM,
    ]


def test_invalid_llm_semantics_are_not_materialized() -> None:
    document = _source(ParseSourceType.DOCUMENT, 10)
    location = LineRangeLocation(document, start_line=1, end_line=1)
    llm = LlmMergeContribution(
        source=document,
        fragments=(LlmEvidenceFragment(location=location, text="招聘人数: 很多"),),
        payload=LlmExtractionPayload(
            candidates=[
                LlmFieldCandidate(
                    name=FieldName.HEADCOUNT,
                    raw_value="很多",
                    normalized_value="many",
                    evidence_quote="招聘人数: 很多",
                )
            ]
        ),
        extractor_version="llm-v1",
    )

    merged = ExtractionMerger().merge(
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            llm_contributions=(llm,),
        )
    )

    assert merged.post_fields == ()
    assert merged.positions == ()


def test_merge_hash_and_selection_are_independent_of_input_order_and_duplicates() -> None:
    document = _source(ParseSourceType.DOCUMENT, 10)
    attachment = _source(ParseSourceType.ATTACHMENT, 20)
    body_location = LineRangeLocation(document, start_line=5, end_line=5)
    attachment_location = CellRangeLocation(attachment, "岗位表", "B2", "B2")
    body = _result(
        document,
        body_location,
        _field(
            FieldName.DEADLINE,
            "2026-09-01",
            datetime(2026, 9, 1, 15, 59, 59, tzinfo=UTC),
            body_location,
        ),
    )
    attachment_result = _result(
        attachment,
        attachment_location,
        _field(
            FieldName.DEADLINE,
            "2026/09/02",
            datetime(2026, 9, 2, 15, 59, 59, tzinfo=UTC),
            attachment_location,
        ),
    )
    merger = ExtractionMerger()

    first = merger.merge(
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            deterministic_results=(body, attachment_result, body),
        )
    )
    second = merger.merge(
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            deterministic_results=(attachment_result, body),
        )
    )

    assert first == second
    assert first.result_hash == second.result_hash
    assert len(first.post_fields[0].evidence) == 2
    serialized_deadline = normalized_json_value(first.post_fields[0].normalized_value)
    assert isinstance(serialized_deadline, str)
    assert serialized_deadline.endswith("Z")


def test_merge_input_rejects_wrong_document_source() -> None:
    wrong_document = _source(ParseSourceType.DOCUMENT, 99)
    location = LineRangeLocation(wrong_document, start_line=1, end_line=1)
    result = _result(
        wrong_document,
        location,
        _field(FieldName.CATEGORY, "校园招聘", "campus", location),
    )

    with pytest.raises(ValueError, match="must match"):
        ExtractionMergeInput(
            document_id=10,
            extraction_version="merge-v1",
            deterministic_results=(result,),
        )
