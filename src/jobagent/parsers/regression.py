"""Offline golden-fixture evaluation for attachment parser results."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

from jobagent.core.exceptions import JsonValue
from jobagent.parsers.contracts import (
    CellRangeLocation,
    LineRangeLocation,
    PageLocation,
    ParseRequest,
    ParseResult,
    ParseSource,
    ParseSourceType,
    TableBlock,
    TextBlock,
)
from jobagent.parsers.registry import ParserRegistry

GOLDEN_MANIFEST_NAME: Final = "manifest.json"


@dataclass(frozen=True, slots=True)
class GoldenDifference:
    """One fixture whose actual intermediate result differs from its expectation."""

    case_id: str
    expected: dict[str, JsonValue]
    actual: dict[str, JsonValue]

    def to_dict(self) -> dict[str, JsonValue]:
        return {"case_id": self.case_id, "expected": self.expected, "actual": self.actual}


@dataclass(frozen=True, slots=True)
class GoldenReport:
    """Deterministic aggregate and per-case differences for one fixture batch."""

    total: int
    matched: int
    differences: tuple[GoldenDifference, ...]

    @property
    def success_rate(self) -> float:
        return self.matched / self.total if self.total else 0.0

    def to_dict(self) -> dict[str, JsonValue]:
        return {
            "total": self.total,
            "matched": self.matched,
            "success_rate": self.success_rate,
            "differences": [difference.to_dict() for difference in self.differences],
        }


def evaluate_golden_fixtures(fixture_dir: Path, registry: ParserRegistry) -> GoldenReport:
    """Parse every declared local fixture and compare its normalized full blocks."""
    cases = _load_manifest(fixture_dir / GOLDEN_MANIFEST_NAME)
    differences: list[GoldenDifference] = []
    for source_id, case in enumerate(cases, start=1):
        case_id = _required_string(case, "id")
        fixture_name = _required_string(case, "file")
        media_type = _required_string(case, "media_type")
        expected = case.get("expected")
        if not isinstance(expected, dict):
            raise ValueError(f"Golden case '{case_id}' requires an expected object.")
        fixture_path = fixture_dir / fixture_name
        if fixture_path.parent != fixture_dir or not fixture_path.is_file():
            raise ValueError(f"Golden case '{case_id}' references an invalid fixture path.")
        source = ParseSource(
            source_type=ParseSourceType.ATTACHMENT,
            source_id=source_id,
            source_name=fixture_name,
            media_type=media_type,
        )
        actual = serialize_parse_result(
            registry.parse(ParseRequest(source=source, content=fixture_path.read_bytes()))
        )
        expected_json = expected
        if actual != expected_json:
            differences.append(
                GoldenDifference(case_id=case_id, expected=expected_json, actual=actual)
            )
    return GoldenReport(
        total=len(cases),
        matched=len(cases) - len(differences),
        differences=tuple(differences),
    )


def serialize_parse_result(result: ParseResult) -> dict[str, JsonValue]:
    """Normalize a parser result without unstable source IDs or library metadata."""
    return {
        "status": result.status.value,
        "parser_name": result.parser_name,
        "issues": [issue.code.value for issue in result.issues],
        "blocks": [_serialize_block(block) for block in result.blocks],
    }


def _serialize_block(block: TextBlock | TableBlock) -> dict[str, JsonValue]:
    if isinstance(block, TextBlock):
        return {
            "type": "text",
            "kind": block.kind.value,
            "text": block.text,
            "location": _serialize_location(block.location),
        }
    return {
        "type": "table",
        "location": _serialize_location(block.location),
        "rows": [
            [{"value": cell.value, "location": _serialize_location(cell.location)} for cell in row]
            for row in block.rows
        ],
    }


def _serialize_location(
    location: PageLocation | LineRangeLocation | CellRangeLocation,
) -> dict[str, JsonValue]:
    if isinstance(location, PageLocation):
        return {"type": "page", "page_number": location.page_number}
    if isinstance(location, LineRangeLocation):
        return {
            "type": "lines",
            "start_line": location.start_line,
            "end_line": location.end_line,
        }
    return {
        "type": "cells",
        "sheet_name": location.sheet_name,
        "start_cell": location.start_cell,
        "end_cell": location.end_cell,
    }


def _load_manifest(path: Path) -> list[dict[str, JsonValue]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Golden manifest is missing or invalid JSON.") from error
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("Golden manifest requires a cases list.")
    cases = payload["cases"]
    if len(cases) < 10:
        raise ValueError("Golden manifest requires at least ten cases.")
    if any(not isinstance(case, dict) for case in cases):
        raise ValueError("Every golden case must be an object.")
    return cast(list[dict[str, JsonValue]], cases)


def _required_string(case: dict[str, JsonValue], key: str) -> str:
    value = case.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Golden case requires a non-empty '{key}'.")
    return value.strip()
