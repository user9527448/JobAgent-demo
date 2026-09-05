"""Deterministic source-stability metrics for bounded daily observations."""

from __future__ import annotations

from dataclasses import dataclass

from jobagent.crawlers.contracts import RawDocumentInput
from jobagent.crawlers.documents import (
    canonicalize_url,
    content_fingerprint,
    normalize_document_content,
)
from jobagent.extraction import DeterministicFieldExtractor, FieldName
from jobagent.parsers import (
    PageLocation,
    ParseResult,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    TextBlock,
    TextBlockKind,
)

_CORE_FIELDS = (
    "organization",
    "title",
    "region",
    "deadline",
    "source_link",
)


@dataclass(frozen=True, slots=True)
class SourceStabilityMetrics:
    """One source's bounded success, duplicate, and completeness observation."""

    source_key: str
    attempted: int
    succeeded: int
    failed: int
    duplicates: int
    complete_core_fields: int
    possible_core_fields: int
    core_field_counts: dict[str, int]

    def __post_init__(self) -> None:
        if not self.source_key.strip():
            raise ValueError("Source stability metrics require a source key.")
        if (
            min(
                self.attempted,
                self.succeeded,
                self.failed,
                self.duplicates,
                self.complete_core_fields,
                self.possible_core_fields,
            )
            < 0
        ):
            raise ValueError("Source stability counts cannot be negative.")
        if self.succeeded + self.failed != self.attempted:
            raise ValueError("Attempted details must equal succeeded plus failed details.")

    @property
    def success_rate(self) -> float:
        return _rate(self.succeeded, self.attempted)

    @property
    def duplicate_rate(self) -> float:
        return _rate(self.duplicates, self.succeeded)

    @property
    def core_field_completeness(self) -> float:
        return _rate(self.complete_core_fields, self.possible_core_fields)

    def to_dict(self) -> dict[str, object]:
        """Return a stable JSON-compatible metric representation."""
        return {
            "source_key": self.source_key,
            "attempted": self.attempted,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "success_rate": self.success_rate,
            "duplicates": self.duplicates,
            "duplicate_rate": self.duplicate_rate,
            "complete_core_fields": self.complete_core_fields,
            "possible_core_fields": self.possible_core_fields,
            "core_field_completeness": self.core_field_completeness,
            "core_field_counts": self.core_field_counts,
        }


def evaluate_source_stability(
    source_key: str,
    *,
    attempted: int,
    documents: tuple[RawDocumentInput, ...],
    failed: int,
) -> SourceStabilityMetrics:
    """Evaluate a bounded live batch without persisting source or applicant data."""
    if attempted != len(documents) + failed:
        raise ValueError("Attempted details must match documents plus failures.")
    duplicate_count = _duplicate_count(documents)
    field_counts = dict.fromkeys(_CORE_FIELDS, 0)
    extractor = DeterministicFieldExtractor()

    for index, document in enumerate(documents, start=1):
        extracted = extractor.extract(
            _parse_result(document, source_key=source_key, source_id=index),
            base_url=document.url,
        )
        names = {field.name for field in extracted.fields}
        field_counts["organization"] += int(
            FieldName.ORGANIZATION in names or _has_metadata_text(document, "organization")
        )
        field_counts["title"] += int(bool(document.title.strip()))
        field_counts["region"] += int(
            FieldName.REGION in names
            or _has_metadata_text(document, "region")
            or _has_metadata_text(document, "region_raw")
        )
        field_counts["deadline"] += int(FieldName.DEADLINE in names)
        field_counts["source_link"] += int(bool(canonicalize_url(document.url)))

    possible = len(documents) * len(_CORE_FIELDS)
    return SourceStabilityMetrics(
        source_key=source_key,
        attempted=attempted,
        succeeded=len(documents),
        failed=failed,
        duplicates=duplicate_count,
        complete_core_fields=sum(field_counts.values()),
        possible_core_fields=possible,
        core_field_counts=field_counts,
    )


def _duplicate_count(documents: tuple[RawDocumentInput, ...]) -> int:
    seen_urls: set[str] = set()
    seen_content: set[str] = set()
    duplicates = 0
    for document in documents:
        canonical_url = canonicalize_url(document.url)
        fingerprint = content_fingerprint(
            raw_html=document.raw_html,
            raw_text=document.raw_text,
        )
        if canonical_url in seen_urls or fingerprint in seen_content:
            duplicates += 1
        seen_urls.add(canonical_url)
        seen_content.add(fingerprint)
    return duplicates


def _has_metadata_text(document: RawDocumentInput, field: str) -> bool:
    value = document.metadata.get(field)
    return isinstance(value, str) and bool(value.strip())


def _parse_result(
    document: RawDocumentInput,
    *,
    source_key: str,
    source_id: int,
) -> ParseResult:
    source = ParseSource(
        source_type=ParseSourceType.DOCUMENT,
        source_id=source_id,
        source_name=f"{source_key}:{document.title}",
        media_type="text/plain",
    )
    text = (
        document.raw_text
        if document.raw_text is not None and document.raw_text.strip()
        else normalize_document_content(raw_html=document.raw_html, raw_text=None)
    )
    return ParseResult(
        source=source,
        status=ParseStatus.PARSED,
        parser_name="source_stability_text",
        blocks=(
            TextBlock(
                kind=TextBlockKind.PARAGRAPH,
                text=text,
                location=PageLocation(source=source, page_number=1),
            ),
        ),
    )


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0
