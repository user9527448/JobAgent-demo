"""Tests for the bootstrap command-line entry point."""

import pytest

from jobagent.cli import BOOTSTRAP_MESSAGE, main


def test_main_prints_bootstrap_message(capsys: pytest.CaptureFixture[str]) -> None:
    """The command should provide a stable installation success message."""
    main()

    captured = capsys.readouterr()
    assert captured.out == f"{BOOTSTRAP_MESSAGE}\n"
