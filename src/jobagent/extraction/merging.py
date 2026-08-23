"""Deterministic body/attachment merging with explicit conflict evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Final

from jobagent.core.exceptions import JsonValue
from jobagent.extraction.contracts import ExtractedField, ExtractionResult, FieldName
from jobagent.extraction.llm_contracts import (
    LlmEvidenceFragment,
    LlmExtractionPayload,
    LlmFieldCandidate,
)
from jobagent.parsers import (
    EvidenceLocation,
    LineRangeLocation,
    PageLocation,
    ParseSource,
    ParseSourceType,
)

POST_FIELDS: Final = frozenset(
    {
        FieldName.START_AT,
        FieldName.DEADLINE,
        FieldName.REGION,
        FieldName.ORGANIZATION,
        FieldName.APPLY_URL,
        FieldName.CATEGORY,
    }
)
POSITION_FIELDS: Final = frozenset(
    {
        FieldName.REGION,
        FieldName.HEADCOUNT,
        FieldName.EDUCATION,
    }
)


class ExtractionMethod(StrEnum):
    """Stable evidence producer identifiers persisted with every candidate."""

    DETERMINISTIC = "deterministic"
    LLM = "llm"


class MergedEntityType(StrEnum):
    """Business entity types supported by field evidence persistence."""

    JOB_POST = "job_post"
    JOB_POSITION = "job_position"


@dataclass(frozen=True, slots=True)
class LlmMergeContribution:
    """One validated LLM payload bound back to its supplied parser fragments."""

    source: ParseSource
    fragments: tuple[LlmEvidenceFragment, ...]
    payload: LlmExtractionPayload
    extractor_version: str

    def __post_init__(self) -> None:
        if not self.extractor_version.strip():
            raise ValueError("LLM merge extractor version cannot be empty.")
        if not self.fragments:
            raise ValueError("LLM merge contribution requires evidence fragments.")
        if any(fragment.location.source != self.source for fragment in self.fragments):
            raise ValueError("LLM merge fragments cannot mix parser sources.")


@dataclass(frozen=True, slots=True)
class ExtractionMergeInput:
    """All evidenced extraction outputs for one immutable raw document version."""

    document_id: int
    extraction_version: str
    deterministic_results: tuple[ExtractionResult, ...] = ()
    llm_contributions: tuple[LlmMergeContribution, ...] = ()

    def __post_init__(self) -> None:
        if self.document_id <= 0:
            raise ValueError("Merged extraction document ID must be positive.")
        if not self.extraction_version.strip():
            raise ValueError("Merged extraction version cannot be empty.")
        if not self.deterministic_results and not self.llm_contributions:
            raise ValueError("Merged extraction requires at least one extraction result.")
        sources = [result.source for result in self.deterministic_results]
        sources.extend(contribution.source for contribution in self.llm_contributions)
        for source in sources:
            if (
                source.source_type is ParseSourceType.DOCUMENT
                and source.source_id != self.document_id
            ):
                raise ValueError("Document extraction source must match the merged document ID.")


@dataclass(frozen=True, slots=True)
class MergedEvidence:
    """One retained candidate, including whether precedence selected it."""

    field_name: FieldName
    raw_value: str
    normalized_value: datetime | int | str | tuple[str, ...]
    location: EvidenceLocation
    quote: str
    method: ExtractionMethod
    extractor_version: str
    confidence: Decimal
    selected: bool
    conflict: bool

    def __post_init__(self) -> None:
        if not self.raw_value.strip() or not self.quote.strip():
            raise ValueError("Merged evidence requires raw text and a quote.")
        if not self.extractor_version.strip():
            raise ValueError("Merged evidence extractor version cannot be empty.")
        if not Decimal(0) <= self.confidence <= Decimal(1):
            raise ValueError("Merged evidence confidence must be between zero and one.")


@dataclass(frozen=True, slots=True)
class MergedField:
    """One selected normalized value plus every supporting/conflicting candidate."""

    name: FieldName
    normalized_value: datetime | int | str | tuple[str, ...]
    evidence: tuple[MergedEvidence, ...]

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("Merged fields require evidence.")
        selected = tuple(item for item in self.evidence if item.selected)
        if len(selected) != 1:
            raise ValueError("Merged fields require exactly one selected candidate.")
        if selected[0].field_name is not self.name:
            raise ValueError("Merged field evidence name must match its field.")
        if selected[0].normalized_value != self.normalized_value:
            raise ValueError("Merged field value must match its selected evidence.")

    @property
    def has_conflict(self) -> bool:
        """Return whether at least one retained candidate disagrees with the winner."""
        return any(item.conflict for item in self.evidence)


@dataclass(frozen=True, slots=True)
class MergedPosition:
    """One source record that can safely materialize a partial position entity."""

    record_key: str
    fields: tuple[MergedField, ...]

    def __post_init__(self) -> None:
        if not self.record_key.strip() or not self.fields:
            raise ValueError("Merged positions require a stable key and fields.")
        names = [merged.name for merged in self.fields]
        if len(names) != len(set(names)) or any(name not in POSITION_FIELDS for name in names):
            raise ValueError("Merged position fields must be unique position fields.")


@dataclass(frozen=True, slots=True)
class MergedExtraction:
    """Stable versioned business values and all field-level evidence."""

    document_id: int
    extraction_version: str
    post_fields: tuple[MergedField, ...] = ()
    positions: tuple[MergedPosition, ...] = ()
    result_hash: str = field(init=False)

    def __post_init__(self) -> None:
        if self.document_id <= 0 or not self.extraction_version.strip():
            raise ValueError("Merged extraction identity is invalid.")
        names = [merged.name for merged in self.post_fields]
        if len(names) != len(set(names)) or any(name not in POST_FIELDS for name in names):
            raise ValueError("Merged post fields must be unique announcement fields.")
        object.__setattr__(self, "result_hash", _result_hash(self))


@dataclass(frozen=True, slots=True)
class _Candidate:
    field_name: FieldName
    raw_value: str
    normalized_value: datetime | int | str | tuple[str, ...]
    location: EvidenceLocation
    quote: str
    method: ExtractionMethod
    extractor_version: str
    confidence: Decimal


class ExtractionMerger:
    """Apply documented precedence without discarding contradictory evidence."""

    def merge(self, merge_input: ExtractionMergeInput) -> MergedExtraction:
        """Return stable announcement/position values for one document version."""
        post_candidates: dict[FieldName, list[_Candidate]] = {}
        position_candidates: dict[str, dict[FieldName, list[_Candidate]]] = {}

        for result in merge_input.deterministic_results:
            for record_index, record in enumerate(result.records):
                record_candidates = [
                    _rule_candidate(field, result.extractor_version) for field in record.fields
                ]
                _collect_post_candidates(post_candidates, record_candidates)
                if any(
                    item.field_name in POSITION_FIELDS - {FieldName.REGION}
                    for item in record_candidates
                ):
                    key = _record_key(result.source, record.location, record_index)
                    _collect_position_candidates(position_candidates, key, record_candidates)

        for contribution in merge_input.llm_contributions:
            grouped: dict[int, list[_Candidate]] = {}
            for candidate in contribution.payload.candidates:
                located = _llm_candidate(candidate, contribution)
                if located is None:
                    continue
                fragment_index, merged_candidate = located
                grouped.setdefault(fragment_index, []).append(merged_candidate)
                _collect_post_candidates(post_candidates, [merged_candidate])
            for fragment_index, candidates in grouped.items():
                if any(
                    item.field_name in POSITION_FIELDS - {FieldName.REGION} for item in candidates
                ):
                    fragment = contribution.fragments[fragment_index]
                    key = _record_key(contribution.source, fragment.location, fragment_index)
                    _collect_position_candidates(position_candidates, key, candidates)

        post_fields = tuple(
            _merge_candidates(name, candidates, entity_type=MergedEntityType.JOB_POST)
            for name, candidates in sorted(post_candidates.items(), key=lambda item: item[0].value)
        )
        positions = tuple(
            MergedPosition(
                record_key=key,
                fields=tuple(
                    _merge_candidates(name, candidates, entity_type=MergedEntityType.JOB_POSITION)
                    for name, candidates in sorted(grouped.items(), key=lambda item: item[0].value)
                ),
            )
            for key, grouped in sorted(position_candidates.items())
        )
        return MergedExtraction(
            document_id=merge_input.document_id,
            extraction_version=merge_input.extraction_version,
            post_fields=post_fields,
            positions=positions,
        )


def _collect_post_candidates(
    target: dict[FieldName, list[_Candidate]], candidates: list[_Candidate]
) -> None:
    for candidate in candidates:
        if candidate.field_name in POST_FIELDS:
            target.setdefault(candidate.field_name, []).append(candidate)


def _collect_position_candidates(
    target: dict[str, dict[FieldName, list[_Candidate]]],
    key: str,
    candidates: list[_Candidate],
) -> None:
    grouped = target.setdefault(key, {})
    for candidate in candidates:
        if candidate.field_name in POSITION_FIELDS:
            grouped.setdefault(candidate.field_name, []).append(candidate)


def _rule_candidate(field: ExtractedField, extractor_version: str) -> _Candidate:
    return _Candidate(
        field_name=field.name,
        raw_value=field.raw_value,
        normalized_value=field.normalized_value,
        location=field.evidence.location,
        quote=field.evidence.quote,
        method=ExtractionMethod.DETERMINISTIC,
        extractor_version=extractor_version,
        confidence=Decimal("1.0000"),
    )


def _llm_candidate(
    candidate: LlmFieldCandidate,
    contribution: LlmMergeContribution,
) -> tuple[int, _Candidate] | None:
    normalized = _validated_llm_value(candidate)
    if normalized is None:
        return None
    for index, fragment in enumerate(contribution.fragments):
        if candidate.evidence_quote in fragment.text:
            return index, _Candidate(
                field_name=candidate.name,
                raw_value=candidate.raw_value,
                normalized_value=normalized,
                location=fragment.location,
                quote=candidate.evidence_quote,
                method=ExtractionMethod.LLM,
                extractor_version=contribution.extractor_version,
                confidence=Decimal("0.6000"),
            )
    return None


def _validated_llm_value(
    candidate: LlmFieldCandidate,
) -> datetime | int | str | tuple[str, ...] | None:
    value = candidate.normalized_value
    if candidate.name in {FieldName.START_AT, FieldName.DEADLINE}:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(UTC)
    if candidate.name is FieldName.HEADCOUNT:
        return (
            value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None
        )
    if candidate.name is FieldName.REGION:
        if isinstance(value, str) and value:
            return (value,)
        if (
            isinstance(value, list)
            and value
            and all(isinstance(item, str) and item for item in value)
        ):
            return tuple(value)
        return None
    return value if isinstance(value, str) and value else None


def _merge_candidates(
    name: FieldName,
    candidates: list[_Candidate],
    *,
    entity_type: MergedEntityType,
) -> MergedField:
    unique = {_candidate_key(candidate): candidate for candidate in candidates}
    ordered = sorted(unique.values(), key=lambda item: _precedence_key(item, entity_type))
    winner = ordered[0]
    winner_key = _normalized_key(winner.normalized_value)
    conflict = any(_normalized_key(item.normalized_value) != winner_key for item in ordered[1:])
    evidence = tuple(
        MergedEvidence(
            field_name=item.field_name,
            raw_value=item.raw_value,
            normalized_value=item.normalized_value,
            location=item.location,
            quote=item.quote,
            method=item.method,
            extractor_version=item.extractor_version,
            confidence=item.confidence,
            selected=index == 0,
            conflict=conflict and _normalized_key(item.normalized_value) != winner_key,
        )
        for index, item in enumerate(ordered)
    )
    return MergedField(name=name, normalized_value=winner.normalized_value, evidence=evidence)


def _precedence_key(candidate: _Candidate, entity_type: MergedEntityType) -> tuple[object, ...]:
    method_rank = 0 if candidate.method is ExtractionMethod.DETERMINISTIC else 1
    is_document = candidate.location.source.source_type is ParseSourceType.DOCUMENT
    if entity_type is MergedEntityType.JOB_POST:
        source_rank = 0 if is_document else 1
    else:
        source_rank = 1 if is_document else 0
    return (
        method_rank,
        source_rank,
        candidate.location.source.source_id,
        _location_key(candidate.location),
        candidate.raw_value,
        _normalized_key(candidate.normalized_value),
    )


def _candidate_key(candidate: _Candidate) -> tuple[object, ...]:
    return (
        candidate.field_name,
        candidate.raw_value,
        _normalized_key(candidate.normalized_value),
        candidate.location.source.source_type,
        candidate.location.source.source_id,
        _location_key(candidate.location),
        candidate.quote,
        candidate.method,
        candidate.extractor_version,
    )


def _record_key(source: ParseSource, location: EvidenceLocation, index: int) -> str:
    return f"{source.source_type.value}:{source.source_id}:{_location_key(location)}:{index}"


def _location_key(location: EvidenceLocation) -> str:
    if isinstance(location, PageLocation):
        return f"page:{location.page_number}"
    if isinstance(location, LineRangeLocation):
        return f"lines:{location.start_line}-{location.end_line}"
    return f"sheet:{location.sheet_name}:cells:{location.start_cell}-{location.end_cell}"


def normalized_json_value(value: datetime | int | str | tuple[str, ...]) -> JsonValue:
    """Convert one normalized value to stable JSON-compatible persistence data."""
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if isinstance(value, tuple):
        return list(value)
    return value


def _normalized_key(value: datetime | int | str | tuple[str, ...]) -> str:
    return json.dumps(normalized_json_value(value), ensure_ascii=False, sort_keys=True)


def _result_hash(result: MergedExtraction) -> str:
    payload = {
        "document_id": result.document_id,
        "extraction_version": result.extraction_version,
        "post_fields": [_field_payload(item) for item in result.post_fields],
        "positions": [
            {
                "record_key": position.record_key,
                "fields": [_field_payload(item) for item in position.fields],
            }
            for position in result.positions
        ],
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _field_payload(merged: MergedField) -> dict[str, JsonValue]:
    return {
        "name": merged.name.value,
        "normalized_value": normalized_json_value(merged.normalized_value),
        "evidence": [
            {
                "raw_value": item.raw_value,
                "normalized_value": normalized_json_value(item.normalized_value),
                "source_type": item.location.source.source_type.value,
                "source_id": item.location.source.source_id,
                "location": _location_key(item.location),
                "quote": item.quote,
                "method": item.method.value,
                "extractor_version": item.extractor_version,
                "confidence": str(item.confidence),
                "selected": item.selected,
                "conflict": item.conflict,
            }
            for item in merged.evidence
        ],
    }
