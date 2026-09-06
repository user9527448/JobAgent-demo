"""Operator CLI parsing checks for JAI-026."""

import argparse
from datetime import date

import pytest

from jobagent.jobs.cli import _build_parser, _iso_date, _positive_id


def test_scheduler_cli_accepts_start_makeup_and_show() -> None:
    parser = _build_parser()

    assert parser.parse_args(["start"]).command == "start"
    makeup = parser.parse_args(["makeup", "--date", "2026-09-06"])
    assert makeup.command == "makeup"
    assert makeup.date == date(2026, 9, 6)
    show = parser.parse_args(["show", "--run-id", "7"])
    assert show.command == "show"
    assert show.run_id == 7


@pytest.mark.parametrize("value", ["2026/09/06", "invalid"])
def test_scheduler_cli_rejects_invalid_dates(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="YYYY-MM-DD"):
        _iso_date(value)


@pytest.mark.parametrize("value", ["0", "-1"])
def test_scheduler_cli_rejects_nonpositive_ids(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="positive"):
        _positive_id(value)
