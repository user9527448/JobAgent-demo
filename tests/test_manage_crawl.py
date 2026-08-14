"""Checks for the JAI-012 manual crawl command surface."""

import pytest
from scripts.manage_crawl import _build_parser


@pytest.mark.parametrize(
    ("arguments", "command", "identifier"),
    [
        (["run", "--source-id", "7"], "run", 7),
        (["show", "--run-id", "11"], "show", 11),
        (["retry", "--run-id", "11"], "retry", 11),
    ],
)
def test_manual_crawl_commands_parse_positive_identifiers(
    arguments: list[str],
    command: str,
    identifier: int,
) -> None:
    args = _build_parser().parse_args(arguments)

    assert args.command == command
    assert getattr(args, "source_id", getattr(args, "run_id", None)) == identifier


def test_manual_crawl_command_rejects_nonpositive_identifier() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(["show", "--run-id", "0"])
