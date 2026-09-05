"""Offline contract tests for Shanghai public-institution notices."""

import asyncio
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient
from jobagent.crawlers.shanghai_rsj import (
    ShanghaiPublicInstitutionAdapter,
    parse_shanghai_public_institution_detail,
    parse_shanghai_public_institution_list,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "shanghai_rsj"
BASE_URL = "https://rsj.sh.gov.cn/"
LIST_URL = "https://rsj.sh.gov.cn/tsydwgkzp_17406/index.html"


def test_list_discovers_only_recruitment_announcements() -> None:
    items = parse_shanghai_public_institution_list(
        (FIXTURE_DIR / "list.html").read_bytes(),
        list_url=LIST_URL,
        include_keywords=("事业单位", "公开招聘", "招聘公告"),
        exclude_keywords=("拟聘", "录用公示"),
    )

    assert [item.metadata["title"] for item in items] == [
        "合成甲事业单位公开招聘公告",
        "合成乙研究院招聘公告",
        "合成丙公共服务中心工作人员公开招聘公告",
    ]
    assert [item.metadata["published_on"] for item in items] == [
        "2026-08-25",
        "2026-08-24",
        "2026-08-23",
    ]
    assert all("/tzpgg_17408/" in item.url for item in items)
    assert all("evil.invalid" not in item.url for item in items)


@pytest.mark.parametrize(
    ("fixture_name", "detail_path", "title", "published_on"),
    [
        (
            "detail-museum.html",
            "/tzpgg_17408/20260825/t0035_9000001.html",
            "合成甲事业单位公开招聘公告",
            date(2026, 8, 25),
        ),
        (
            "detail-research.html",
            "/tzpgg_17408/20260824/0123456789abcdef0123456789abcdef.html",
            "合成乙研究院招聘公告",
            date(2026, 8, 24),
        ),
        (
            "detail-service.html",
            "/tzpgg_17408/20260823/t0035_9000003.html",
            "合成丙公共服务中心工作人员公开招聘公告",
            date(2026, 8, 23),
        ),
    ],
)
def test_three_synthetic_detail_contract_samples(
    fixture_name: str,
    detail_path: str,
    title: str,
    published_on: date,
) -> None:
    document = parse_shanghai_public_institution_detail(
        (FIXTURE_DIR / fixture_name).read_bytes(),
        detail_url=f"{BASE_URL.rstrip('/')}{detail_path}",
        official_owner="上海市人力资源和社会保障局",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == published_on
    assert document.published_at.tzinfo is not None
    assert title in (document.raw_text or "")
    assert document.raw_html is not None
    assert document.metadata["region"] == "shanghai"
    organization = document.metadata["organization"]
    assert isinstance(organization, str)
    assert organization in title
    assert document.metadata["organization_evidence"] == title


def test_adapter_uses_catalog_cursor_and_shared_http_client() -> None:
    list_bytes = (FIXTURE_DIR / "list.html").read_bytes()
    detail_bytes = (FIXTURE_DIR / "detail-museum.html").read_bytes()

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == LIST_URL:
            return httpx.Response(200, content=list_bytes, request=request)
        return httpx.Response(200, content=detail_bytes, request=request)

    entry = _entry()
    source = SourceDefinition(
        id=15,
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
            adapter = ShanghaiPublicInstitutionAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-08-24"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == ["2026-08-25"]
    assert document.title == "合成甲事业单位公开招聘公告"


def test_unrecognized_list_and_missing_detail_title_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_shanghai_public_institution_list(b"<html>changed</html>", list_url=LIST_URL)
    assert list_error.value.code == "crawler.shanghai_rsj_list_unrecognized"

    with pytest.raises(PermanentJobAgentError) as detail_error:
        parse_shanghai_public_institution_detail(
            b"<html><body>body only</body></html>",
            detail_url=f"{BASE_URL}tzpgg_17408/20260825/t0035_9000001.html",
            official_owner="上海市人力资源和社会保障局",
        )
    assert detail_error.value.code == "crawler.shanghai_rsj_detail_title_missing"


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="shanghai-public-institution",
        name="上海市人社局事业单位公开招聘",
        official_owner="上海市人力资源和社会保障局",
        category="public_exam",
        regions=("shanghai",),
        base_url=BASE_URL,
        list_url=LIST_URL,
        adapter="shanghai_public_institution",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=180,
        include_keywords=("事业单位", "公开招聘", "招聘公告"),
        exclude_keywords=("拟聘", "录用公示"),
    )
