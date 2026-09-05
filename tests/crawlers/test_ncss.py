"""Offline contract tests for the NCSS public job source Adapter."""

import asyncio
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient
from jobagent.crawlers.ncss import NcssJobsAdapter, parse_ncss_detail, parse_ncss_list

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ncss"
BASE_URL = "https://www.ncss.cn/"
LIST_URL = "https://www.ncss.cn/student/jobs/jobslist/ajax/"


def test_list_discovers_filtered_public_jobs_with_stable_ids() -> None:
    items = parse_ncss_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
        include_keywords=("校招", "校园招聘", "应届", "毕业生"),
        exclude_keywords=("实习",),
    )

    assert [item.metadata["title"] for item in items] == [
        "2027届校园招聘软件工程师",
        "应届毕业生数据分析岗",
        "校招机械设计工程师",
    ]
    assert [item.metadata["published_on"] for item in items] == [
        "2026-08-24",
        "2026-08-23",
        "2026-08-22",
    ]
    assert len({item.url for item in items}) == 3
    assert items[0].metadata["organization"] == "合成甲科技有限公司"
    assert items[0].metadata["headcount"] == 5
    assert all(item.url.startswith(f"{BASE_URL}student/jobs/") for item in items)


@pytest.mark.parametrize(
    ("index", "fixture_name", "title", "published_on"),
    [
        (0, "detail-software.html", "2027届校园招聘软件工程师", date(2026, 8, 24)),
        (1, "detail-data.html", "应届毕业生数据分析岗", date(2026, 8, 23)),
        (2, "detail-mechanical.html", "校招机械设计工程师", date(2026, 8, 22)),
    ],
)
def test_three_synthetic_detail_contract_samples(
    index: int,
    fixture_name: str,
    title: str,
    published_on: date,
) -> None:
    item = parse_ncss_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
        include_keywords=("校招", "校园招聘", "应届", "毕业生"),
        exclude_keywords=("实习",),
    )[index]
    document = parse_ncss_detail(
        (FIXTURE_DIR / fixture_name).read_bytes(),
        detail_url=item.url,
        metadata=item.metadata,
        official_owner="教育部学生服务与素质发展中心",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == published_on
    assert document.published_at.tzinfo is not None
    assert f"招聘单位: {item.metadata['organization']}" in (document.raw_text or "")
    assert f"工作地点: {item.metadata['region_raw']}" in (document.raw_text or "")
    assert document.raw_html is not None
    assert document.metadata["job_id"] == item.metadata["job_id"]


def test_adapter_uses_public_get_query_cursor_and_detail() -> None:
    list_bytes = (FIXTURE_DIR / "list.json").read_bytes()
    detail_bytes = (FIXTURE_DIR / "detail-software.html").read_bytes()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/jobslist/ajax/"):
            return httpx.Response(200, content=list_bytes, request=request)
        return httpx.Response(200, content=detail_bytes, request=request)

    entry = _entry()
    source = SourceDefinition(
        id=14,
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
            adapter = NcssJobsAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-08-23"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == ["2026-08-24"]
    assert document.title == "2027届校园招聘软件工程师"
    assert requests[0].method == "GET"
    assert requests[0].url.params["limit"] == "30"
    assert requests[1].url.path.endswith("/SyntheticJob000001/detail.html")


def test_unrecognized_list_and_mismatched_detail_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_ncss_list(b'{"flag":false}', base_url=BASE_URL)
    assert list_error.value.code == "crawler.ncss_list_unrecognized"

    item = parse_ncss_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
    )[0]
    with pytest.raises(PermanentJobAgentError) as detail_error:
        parse_ncss_detail(
            (FIXTURE_DIR / "detail-software.html").read_bytes(),
            detail_url=item.url.replace("SyntheticJob000001", "SyntheticJob999999"),
            metadata=item.metadata,
            official_owner="教育部学生服务与素质发展中心",
        )
    assert detail_error.value.code == "crawler.ncss_detail_url_rejected"


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="ncss-jobs",
        name="国家大学生就业服务平台职位",
        official_owner="教育部学生服务与素质发展中心",
        category="campus",
        regions=("national",),
        base_url=BASE_URL,
        list_url=LIST_URL,
        adapter="ncss_jobs",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=360,
        include_keywords=("校招", "校园招聘", "应届", "毕业生"),
        exclude_keywords=("实习",),
    )
