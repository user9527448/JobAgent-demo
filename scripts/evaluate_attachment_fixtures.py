"""Evaluate committed attachment fixtures without network access."""

from __future__ import annotations

import json
from pathlib import Path

from jobagent.parsers.regression import evaluate_golden_fixtures
from jobagent.parsers.runtime import build_parser_registry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "attachments"


def main() -> int:
    """Print a stable JSON report and fail when any fixture differs."""
    report = evaluate_golden_fixtures(FIXTURE_DIR, build_parser_registry())
    print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not report.differences else 1


if __name__ == "__main__":
    raise SystemExit(main())
