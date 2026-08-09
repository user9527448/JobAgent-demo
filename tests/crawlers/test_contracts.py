"""Checks for adapter contract value-object invariants."""

import pytest

from jobagent.crawlers import RawDocumentInput


def test_raw_document_requires_source_content() -> None:
    with pytest.raises(ValueError, match="HTML or text"):
        RawDocumentInput(url="https://example.invalid/1", title="Missing content")
