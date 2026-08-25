"""Checks for the JAI-020 manual reparse command surface."""

import pytest
from scripts.manage_extraction import _build_parser


def test_manual_reparse_command_requires_document_and_version() -> None:
    args = _build_parser().parse_args(
        [
            "reparse",
            "--document-id",
            "19",
            "--extraction-version",
            "rules-v2",
        ]
    )

    assert args.command == "reparse"
    assert args.document_id == 19
    assert args.extraction_version == "rules-v2"


def test_manual_reparse_command_rejects_nonpositive_document() -> None:
    with pytest.raises(SystemExit):
        _build_parser().parse_args(
            [
                "reparse",
                "--document-id",
                "0",
                "--extraction-version",
                "rules-v2",
            ]
        )
