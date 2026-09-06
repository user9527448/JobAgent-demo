"""Unit checks for JAI-026 schedule identity and APScheduler policy."""

from datetime import UTC, date, datetime

import pytest
from apscheduler.jobstores.memory import MemoryJobStore  # type: ignore[import-untyped]
from pydantic import SecretStr

from jobagent.core import Settings
from jobagent.jobs import DAILY_PIPELINE_JOB_NAME, latest_due_slot, scheduled_slot_for_date
from jobagent.jobs.scheduler import build_scheduler


@pytest.fixture
def settings() -> Settings:
    return Settings(
        environment="test",
        database_url=SecretStr("postgresql+psycopg://jobagent:secret@localhost/jobagent_test"),
        scheduler_hour=8,
        scheduler_minute=0,
        scheduler_misfire_grace_seconds=21_600,
    )


def test_daily_slot_has_stable_utc_identity(settings: Settings) -> None:
    assert scheduled_slot_for_date(date(2026, 9, 6), settings) == datetime(
        2026,
        9,
        6,
        tzinfo=UTC,
    )
    assert latest_due_slot(datetime(2026, 9, 6, 0, 1, tzinfo=UTC), settings) == datetime(
        2026,
        9,
        6,
        tzinfo=UTC,
    )
    assert latest_due_slot(datetime(2026, 9, 5, 23, 59, tzinfo=UTC), settings) == datetime(
        2026,
        9,
        5,
        tzinfo=UTC,
    )


def test_latest_due_slot_rejects_naive_clock(settings: Settings) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        latest_due_slot(datetime(2026, 9, 6), settings)


def test_scheduler_registers_one_fixed_replaceable_job(settings: Settings) -> None:
    def target() -> None:
        return None

    scheduler = build_scheduler(
        settings,
        jobstore=MemoryJobStore(),
        job_target=target,
    )
    jobs = scheduler.get_jobs()

    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == DAILY_PIPELINE_JOB_NAME
    assert job.coalesce is True
    assert job.max_instances == 1
    assert job.misfire_grace_time == 21_600
    assert str(job.trigger.timezone) == "Asia/Shanghai"
    assert str(job.trigger.fields[5]) == "8"
    assert str(job.trigger.fields[6]) == "0"
