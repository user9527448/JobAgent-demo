"""Offline contract tests for the Jiangsu public-exam source adapter."""

import asyncio
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient
from jobagent.crawlers.jiangsu import (
    JiangsuPersonnelExamAdapter,
    parse_jiangsu_detail,
    parse_jiangsu_list,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "jiangsu"
LIST_URL = "https://jshrss.jiangsu.gov.cn/col/col57253/index.html"


def test_list_discovers_relevant_same_origin_articles() -> None:
    items = parse_jiangsu_list(
        (FIXTURE_DIR / "list.html").read_bytes(),
        list_url=LIST_URL,
        include_keywords=("公务员", "事业单位", "三支一扶"),
        exclude_keywords=("成绩查询", "录用公示", "拟录用"),
    )

    assert [item.metadata["title"] for item in items] == [
        "江苏省2026年度考试录用公务员公告",
        "江苏省2026年省属事业单位统一公开招聘人员公告",
        "江苏省2026年高校毕业生“三支一扶”计划招募公告",
        "江苏省2026年度考试录用公务员专题",
    ]
    assert len({item.url for item in items}) == 4
    assert items[1].url.endswith("/art_93343_11743861.html")
    assert items[1].metadata["published_on"] == "2026-03-18"
    assert all("evil.invalid" not in item.url for item in items)


@pytest.mark.parametrize(
    ("fixture_name", "title", "published_on"),
    [
        ("detail-civil-service.html", "江苏省2026年度考试录用公务员公告", date(2025, 10, 31)),
        (
            "detail-institution.html",
            "江苏省2026年省属事业单位统一公开招聘人员公告",
            date(2026, 3, 18),
        ),
        (
            "detail-three-support.html",
            "江苏省2026年高校毕业生“三支一扶”计划招募公告",
            date(2026, 6, 8),
        ),
        ("detail-topic.html", "江苏省2026年度考试录用公务员专题", date(2025, 10, 31)),
    ],
)
def test_three_detail_contract_samples(
    fixture_name: str,
    title: str,
    published_on: date,
) -> None:
    document = parse_jiangsu_detail(
        (FIXTURE_DIR / fixture_name).read_bytes(),
        detail_url="https://jshrss.jiangsu.gov.cn/art/2026/1/1/art_1_2.html",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == published_on
    assert document.published_at.tzinfo is not None
    assert title in (document.raw_text or "")
    assert document.raw_html is not None
    assert document.metadata["region"] == "jiangsu"


def test_adapter_uses_catalog_cursor_and_shared_http_client() -> None:
    list_bytes = (FIXTURE_DIR / "list.html").read_bytes()
    detail_bytes = (FIXTURE_DIR / "detail-three-support.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == LIST_URL:
            return httpx.Response(200, content=list_bytes, headers={"content-type": "text/html"})
        assert str(request.url).endswith("/art_78504_11782596.html")
        return httpx.Response(200, content=detail_bytes, headers={"content-type": "text/html"})

    entry = _entry()
    source = SourceDefinition(
        id=12,
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
            adapter = JiangsuPersonnelExamAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-04-01"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == ["2026-06-08"]
    assert document.title == "江苏省2026年高校毕业生“三支一扶”计划招募公告"


def test_unrecognized_list_and_missing_detail_title_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_jiangsu_list(b"<html><body>changed</body></html>", list_url=LIST_URL)
    assert list_error.value.code == "crawler.jiangsu_list_unrecognized"

    with pytest.raises(PermanentJobAgentError) as detail_error:
        parse_jiangsu_detail(
            b"<html><body>body only</body></html>",
            detail_url="https://jshrss.jiangsu.gov.cn/art/2026/1/1/art_1_2.html",
        )
    assert detail_error.value.code == "crawler.jiangsu_detail_title_missing"


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="jiangsu-personnel-exam",
        name="江苏省人事考试网",
        official_owner="江苏省人力资源和社会保障厅",
        category="public_exam",
        regions=("jiangsu",),
        base_url="https://jshrss.jiangsu.gov.cn/",
        list_url=LIST_URL,
        adapter="jiangsu_personnel_exam",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=180,
        include_keywords=("公务员", "事业单位", "三支一扶"),
        exclude_keywords=("成绩查询", "录用公示", "拟录用"),
    )
