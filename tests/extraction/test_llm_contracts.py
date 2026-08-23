"""Strict contract tests for optional LLM extraction."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jobagent.extraction import (
    LlmEvidenceFragment,
    LlmExtractionPayload,
    LlmExtractionRequest,
    LlmFieldCandidate,
    LlmUsage,
)
from jobagent.parsers import LineRangeLocation, ParseSource, ParseSourceType


def _source(source_id: int = 17) -> ParseSource:
    return ParseSource(
        source_type=ParseSourceType.DOCUMENT,
        source_id=source_id,
        source_name="announcement.html",
        media_type="text/html",
    )


def test_json_schema_forbids_unknown_payload_and_candidate_properties() -> None:
    schema = LlmExtractionPayload.model_json_schema()

    assert schema["additionalProperties"] is False
    candidate_schema = schema["$defs"]["LlmFieldCandidate"]
    assert candidate_schema["additionalProperties"] is False
    assert set(candidate_schema["required"]) == {
        "name",
        "raw_value",
        "normalized_value",
        "evidence_quote",
    }


def test_candidate_rejects_unknown_properties_and_boolean_integer_values() -> None:
    with pytest.raises(ValidationError):
        LlmFieldCandidate.model_validate(
            {
                "name": "headcount",
                "raw_value": "10人",
                "normalized_value": True,
                "evidence_quote": "招聘人数: 10人",
                "unexpected": "not allowed",
            }
        )

    with pytest.raises(ValidationError):
        LlmFieldCandidate.model_validate(
            {
                "name": "region",
                "raw_value": "不限地区",
                "normalized_value": [],
                "evidence_quote": "工作地点: 不限地区",
            }
        )


def test_request_requires_nonempty_fragments_from_one_parser_source() -> None:
    source = _source()
    other_source = _source(18)

    with pytest.raises(ValueError, match="cannot mix"):
        LlmExtractionRequest(
            task_id="task-1",
            source=source,
            fragments=(
                LlmEvidenceFragment(
                    location=LineRangeLocation(other_source, start_line=1, end_line=1),
                    text="招聘人数: 10人",
                ),
            ),
        )

    with pytest.raises(ValueError, match="at least one"):
        LlmExtractionRequest(task_id="task-2", source=source, fragments=())


def test_usage_rejects_negative_or_inconsistent_provider_counts() -> None:
    with pytest.raises(ValueError, match="negative"):
        LlmUsage(input_tokens=-1)
    with pytest.raises(ValueError, match="below"):
        LlmUsage(input_tokens=4, output_tokens=3, total_tokens=6)
