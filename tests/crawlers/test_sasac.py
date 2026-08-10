"""Offline contract tests for the first JAI-011 production source adapter."""

import asyncio
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient
from jobagent.crawlers.sasac import (
    SasacRecruitmentAdapter,
    parse_sasac_detail,
    parse_sasac_list,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "sasac"
LIST_URL = "https://www.sasac.gov.cn/n2588035/n2588325/n2588350/index.html"


def test_list_discovers_keyword_matches_and_removes_duplicate_urls() -> None:
    items = parse_sasac_list(
        (FIXTURE_DIR / "list.html").read_bytes(),
        list_url=LIST_URL,
        include_keywords=("招聘", "应届毕业生"),
        exclude_keywords=("公示",),
    )

    assert [item.metadata["title"] for item in items] == [
        "某中央企业2027届校园招聘公告",
        "某集团公开招聘专业人才公告",
        "某研究院应届毕业生招聘公告",
    ]
    assert len({item.url for item in items}) == 3
    assert items[1].url.endswith("/c40000002/content.html")
    assert items[1].metadata["published_on"] == "2026-08-07"


@pytest.mark.parametrize(
    ("fixture_name", "title", "published_on"),
    [
        ("detail-campus.html", "某中央企业2027届校园招聘公告", date(2026, 8, 8)),
        ("detail-professional.html", "某集团公开招聘专业人才公告", date(2026, 8, 7)),
        ("detail-graduate.html", "某研究院应届毕业生招聘公告", date(2026, 8, 6)),
    ],
)
def test_three_detail_contract_samples(fixture_name: str, title: str, published_on: date) -> None:
    document = parse_sasac_detail(
        (FIXTURE_DIR / fixture_name).read_bytes(),
        detail_url="https://www.sasac.gov.cn/n2588035/n2588325/n2588350/c1/content.html",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == published_on
    assert document.published_at.tzinfo is not None
    assert title in (document.raw_text or "")
    assert document.raw_html is not None


def test_adapter_uses_catalog_keywords_cursor_and_shared_http_client() -> None:
    list_bytes = (FIXTURE_DIR / "list.html").read_bytes()
    detail_bytes = (FIXTURE_DIR / "detail-campus.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == LIST_URL:
            return httpx.Response(200, content=list_bytes, headers={"content-type": "text/html"})
        assert str(request.url).endswith("/c40000001/content.html")
        return httpx.Response(200, content=detail_bytes, headers={"content-type": "text/html"})

    entry = _entry()
    source = SourceDefinition(
        id=11,
        name=entry.name,
        base_url=entry.base_url,
        category=entry.category,
        adapter=entry.adapter,
        enabled=True,
    )
    policy = HttpSourcePolicy(
        source_id=source.id,
        user_agent="JOBAGENT/test",
        min_interval_seconds=0,
        max_attempts=1,
    )

    async def run_adapter() -> tuple[tuple[DiscoveredItem, ...], RawDocumentInput]:
        async with SourceHttpClient(policy, transport=httpx.MockTransport(handler)) as client:
            adapter = SasacRecruitmentAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-08-06"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == [
        "2026-08-08",
        "2026-08-07",
    ]
    assert document.title == "某中央企业2027届校园招聘公告"
    assert document.raw_html is not None


def test_unrecognized_list_and_missing_detail_title_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_sasac_list(b"<html><body>changed</body></html>", list_url=LIST_URL)
    assert list_error.value.code == "crawler.sasac_list_unrecognized"

    with pytest.raises(PermanentJobAgentError) as detail_error:
        parse_sasac_detail(
            b"<html><body>body only</body></html>",
            detail_url="https://www.sasac.gov.cn/n2588035/n2588325/n2588350/c1/content.html",
        )
    assert detail_error.value.code == "crawler.sasac_detail_title_missing"


def test_list_rejects_lookalike_detail_link_on_another_host() -> None:
    html = b"""
    <a href="https://evil.invalid/n2588350/c123/content.html">recruitment</a>
    <a href="/n2588350/c124/content.html">valid recruitment</a>
    """

    items = parse_sasac_list(html, list_url=LIST_URL)

    assert [item.url for item in items] == ["https://www.sasac.gov.cn/n2588350/c124/content.html"]


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="sasac-recruitment",
        name="国务院国资委公开招聘",
        official_owner="国务院国有资产监督管理委员会",
        category="state_owned",
        regions=("national",),
        base_url="https://www.sasac.gov.cn/",
        list_url=LIST_URL,
        adapter="sasac_recruitment",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=360,
        include_keywords=("招聘", "应届毕业生"),
        exclude_keywords=("公示",),
    )
