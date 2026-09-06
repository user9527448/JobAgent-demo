"""Unit checks for durable pipeline contracts."""

from datetime import UTC, date, datetime

import pytest

from jobagent.jobs import (
    DispatchStatus,
    PipelineExecutionResult,
    PipelineRunSnapshot,
    PipelineStage,
    PipelineStatus,
    PipelineTrigger,
    StageOutcome,
    StageStatus,
)


def test_pipeline_snapshot_serializes_safe_operator_state() -> None:
    scheduled_for = datetime(2026, 9, 6, tzinfo=UTC)
    snapshot = PipelineRunSnapshot(
        id=7,
        job_name="daily",
        scheduled_for=scheduled_for,
        report_date=date(2026, 9, 6),
        timezone="Asia/Shanghai",
        trigger=PipelineTrigger.MAKEUP,
        status=PipelineStatus.RUNNING,
        current_stage=PipelineStage.EXTRACTION,
        started_at=scheduled_for,
        finished_at=None,
        error_code=None,
        error_message=None,
    )

    payload = PipelineExecutionResult(DispatchStatus.EXECUTED, snapshot).as_json()

    assert payload["dispatch_status"] == "executed"
    assert payload["run"] == {
        "id": 7,
        "job_name": "daily",
        "scheduled_for": "2026-09-06T00:00:00+00:00",
        "report_date": "2026-09-06",
        "timezone": "Asia/Shanghai",
        "trigger": "makeup",
        "status": "running",
        "current_stage": "extraction",
        "started_at": "2026-09-06T00:00:00+00:00",
        "finished_at": None,
        "error_code": None,
        "error_message": None,
    }


def test_stage_outcome_rejects_nonterminal_success_state() -> None:
    with pytest.raises(ValueError, match="succeeded or partial"):
        StageOutcome(StageStatus.RUNNING, {})
