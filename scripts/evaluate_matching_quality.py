"""Evaluate the committed JAI-025 review set without network or database access."""

from __future__ import annotations

import json
from pathlib import Path

from jobagent.matching import compare_quality, load_quality_review_set

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = PROJECT_ROOT / "tests" / "fixtures" / "matching_quality" / "review-set.json"


def main() -> int:
    comparison = compare_quality(load_quality_review_set(FIXTURE_PATH))
    print(json.dumps(comparison.as_json(), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
