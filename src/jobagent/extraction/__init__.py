"""Deterministic, traceable recruitment field extraction."""

from jobagent.extraction.contracts import (
    ExtractedField,
    ExtractionErrorCode,
    ExtractionEvidence,
    ExtractionIssue,
    ExtractionRecord,
    ExtractionResult,
    FieldName,
    NormalizedValue,
)
from jobagent.extraction.dictionaries import (
    CATEGORY_ALIASES,
    EDUCATION_ALIASES,
    REGION_ALIASES,
    normalize_category,
    normalize_education,
    normalize_regions,
)
from jobagent.extraction.rules import (
    EXTRACTOR_VERSION,
    DeterministicFieldExtractor,
    ExtractionPolicy,
)

__all__ = [
    "CATEGORY_ALIASES",
    "EDUCATION_ALIASES",
    "EXTRACTOR_VERSION",
    "REGION_ALIASES",
    "DeterministicFieldExtractor",
    "ExtractedField",
    "ExtractionErrorCode",
    "ExtractionEvidence",
    "ExtractionIssue",
    "ExtractionPolicy",
    "ExtractionRecord",
    "ExtractionResult",
    "FieldName",
    "NormalizedValue",
    "normalize_category",
    "normalize_education",
    "normalize_regions",
]
