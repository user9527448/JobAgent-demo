"""Deterministic checks for JAI-009 URL and content preparation."""

from datetime import UTC, datetime

import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers import (
    RawDocumentInput,
    canonicalize_url,
    content_fingerprint,
    normalize_document_content,
    prepare_raw_document,
)


def test_relative_url_is_resolved_and_tracking_parameters_are_removed() -> None:
    canonical = canonicalize_url(
        "../detail/./1?b=2&utm_source=newsletter&a=hello+world&GCLID=token#top",
        base_url="HTTPS://Example.COM:443/jobs/list/index.html",
    )

    assert canonical == "https://example.com/jobs/detail/1?a=hello+world&b=2"


def test_business_parameters_repeats_unicode_host_and_escapes_are_preserved() -> None:
    canonical = canonicalize_url(
        "https://例子.测试:443/a/%7euser/../job/?z=2&id=2&id=1&empty=&spm=tracking"
    )

    assert canonical == ("https://xn--fsqu00a.xn--0zwm56d/a/job/?empty=&id=1&id=2&z=2")


@pytest.mark.parametrize(
    "url",
    [
        "",
        "/relative/without/base",
        "ftp://example.invalid/file",
        "https://user:secret@example.invalid/jobs/1",
        "https://example.invalid:invalid/jobs/1",
    ],
)
def test_invalid_document_urls_raise_a_safe_domain_error(url: str) -> None:
    with pytest.raises(PermanentJobAgentError) as captured_error:
        canonicalize_url(url)

    assert captured_error.value.code == "crawler.document_url_invalid"
    assert "secret" not in captured_error.value.message


def test_normalized_html_and_text_share_the_same_semantic_fingerprint() -> None:
    raw_html = """
    <html>
      <head><title>Ignored title</title><style>.hidden { display: none; }</style></head>
      <body>招聘&nbsp; <strong>公&#x544a;</strong><script>secret()</script></body>
    </html>
    """
    raw_text = "  招聘\n\t公告  "

    assert normalize_document_content(raw_html=raw_html, raw_text=None) == "招聘 公告"
    assert content_fingerprint(raw_html=raw_html, raw_text=None) == content_fingerprint(
        raw_html=None,
        raw_text=raw_text,
    )


def test_raw_text_is_preferred_when_both_representations_are_available() -> None:
    assert (
        normalize_document_content(
            raw_html="<body>stale HTML</body>",
            raw_text="\uff26\uff52\uff45\uff53\uff48   text",
        )
        == "Fresh text"
    )


def test_content_change_produces_a_different_sha256() -> None:
    first = content_fingerprint(raw_html=None, raw_text="First announcement")
    second = content_fingerprint(raw_html=None, raw_text="Updated announcement")

    assert first != second
    assert len(first) == 64
    assert first == first.lower()


@pytest.mark.parametrize(
    ("raw_html", "raw_text"),
    [(None, None), ("<script>only ignored content</script>", None), (None, " \n ")],
)
def test_empty_visible_content_is_rejected(
    raw_html: str | None,
    raw_text: str | None,
) -> None:
    with pytest.raises(PermanentJobAgentError) as captured_error:
        content_fingerprint(raw_html=raw_html, raw_text=raw_text)

    assert captured_error.value.code == "crawler.document_content_empty"


def test_prepare_raw_document_preserves_source_evidence_and_metadata() -> None:
    published_at = datetime(2026, 8, 10, tzinfo=UTC)
    document = RawDocumentInput(
        url="/jobs/1?utm_medium=email",
        title="Original title",
        raw_html="<body>Original body</body>",
        published_at=published_at,
        etag='"revision-1"',
        last_modified="Mon, 10 Aug 2026 00:00:00 GMT",
    )

    prepared = prepare_raw_document(document, base_url="https://example.invalid/list/")

    assert prepared.canonical_url == "https://example.invalid/jobs/1"
    assert prepared.title == "Original title"
    assert prepared.raw_html == document.raw_html
    assert prepared.raw_text is None
    assert prepared.published_at is published_at
    assert prepared.etag == '"revision-1"'
    assert prepared.last_modified == "Mon, 10 Aug 2026 00:00:00 GMT"
