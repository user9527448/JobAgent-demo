from __future__ import annotations

import json
import shutil
from pathlib import Path

from jobagent.parsers import evaluate_golden_fixtures
from jobagent.parsers.runtime import build_parser_registry

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "attachments"


def test_committed_attachment_golden_batch_matches_offline() -> None:
    report = evaluate_golden_fixtures(FIXTURE_DIR, build_parser_registry())

    assert report.total == 10
    assert report.matched == 10
    assert report.success_rate == 1.0
    assert report.differences == ()
    assert report.to_dict()["differences"] == []


def test_evaluator_reports_case_level_expected_and_actual_differences(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "attachments"
    shutil.copytree(FIXTURE_DIR, fixture_dir)
    manifest_path = fixture_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["cases"][0]["expected"]["status"] = "failed"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = evaluate_golden_fixtures(fixture_dir, build_parser_registry())

    assert report.total == 10
    assert report.matched == 9
    assert report.success_rate == 0.9
    assert len(report.differences) == 1
    difference = report.differences[0]
    assert difference.case_id == "pdf-basic"
    assert difference.expected["status"] == "failed"
    assert difference.actual["status"] == "parsed"
