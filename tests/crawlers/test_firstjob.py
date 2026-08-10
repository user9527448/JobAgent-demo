"""Offline contract tests for Shanghai Firstjob public fair schedules."""

import asyncio
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.firstjob import (
    ShanghaiFirstjobAdapter,
    materialize_firstjob_fair,
    parse_firstjob_list,
)
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "firstjob"
BASE_URL = "https://www.firstjob.shec.edu.cn/"
LIST_URL = (
    "https://www.firstjob.shec.edu.cn/stu_backend/api/proxy/r/jd"
    "?cmd=com.awspaas.user.apps.app202406129280.mhcxzph"
)


def test_list_discovers_filtered_public_fairs_with_stable_urls() -> None:
    items = parse_firstjob_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        public_base_url=BASE_URL,
        include_keywords=("招聘会", "长三角"),
        exclude_keywords=("实习",),
    )

    assert [item.metadata["title"] for item in items] == [
        "2026年上海高校毕业生信息技术与软件服务行业网络招聘会",
        "2026年上海高职高专院校毕业生网络招聘会",
        "2026年长三角高校毕业生文科类网络招聘会",
    ]
    assert len({item.url for item in items}) == 3
    assert all(item.url.startswith(f"{BASE_URL}jobfair?fair_id=") for item in items)
    assert items[0].metadata["published_on"] == "2026-06-01"
    assert items[0].metadata["poster_url"] == (
        "https://www.firstjob.shec.edu.cn/stu_backend/api/public/posters/information.png"
    )


@pytest.mark.parametrize(
    ("fixture_name", "title", "starts_on"),
    [
        (
            "fair-information.json",
            "2026年上海高校毕业生信息技术与软件服务行业网络招聘会",
            date(2026, 6, 1),
        ),
        (
            "fair-vocational.json",
            "2026年上海高职高专院校毕业生网络招聘会",
            date(2026, 5, 18),
        ),
        (
            "fair-yangtze-delta.json",
            "2026年长三角高校毕业生文科类网络招聘会",
            date(2026, 4, 27),
        ),
    ],
)
def test_three_public_fair_contract_samples(
    fixture_name: str,
    title: str,
    starts_on: date,
) -> None:
    item = parse_firstjob_list(
        (FIXTURE_DIR / fixture_name).read_bytes(),
        public_base_url=BASE_URL,
    )[0]
    document = materialize_firstjob_fair(
        item,
        public_base_url=BASE_URL,
        official_owner="上海市学生事务中心",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == starts_on
    assert document.published_at.tzinfo is not None
    assert title in (document.raw_text or "")
    assert document.raw_html is None
    assert document.metadata["official_owner"] == "上海市学生事务中心"
    assert document.metadata["poster_url"] == item.metadata["poster_url"]


def test_adapter_uses_public_post_query_cursor_and_materialized_record() -> None:
    list_bytes = (FIXTURE_DIR / "list.json").read_bytes()
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert str(request.url) == LIST_URL
        return httpx.Response(200, content=list_bytes, headers={"content-type": "application/json"})

    entry = _entry()
    source = SourceDefinition(
        id=13,
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
            adapter = ShanghaiFirstjobAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-05-01"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == [
        "2026-06-01",
        "2026-05-18",
    ]
    assert document.title == "2026年上海高校毕业生信息技术与软件服务行业网络招聘会"
    assert len(requests) == 1
    assert requests[0].method == "POST"
    assert requests[0].headers["content-type"].startswith("application/x-www-form-urlencoded")


def test_unrecognized_response_and_rejected_detail_url_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_firstjob_list(b'{"result":"500"}', public_base_url=BASE_URL)
    assert list_error.value.code == "crawler.firstjob_list_unrecognized"

    item = parse_firstjob_list(
        (FIXTURE_DIR / "fair-information.json").read_bytes(),
        public_base_url=BASE_URL,
    )[0]
    rejected = DiscoveredItem(
        url=item.url.replace("www.firstjob.shec.edu.cn", "evil.invalid"),
        metadata=item.metadata,
    )
    with pytest.raises(PermanentJobAgentError) as detail_error:
        materialize_firstjob_fair(
            rejected,
            public_base_url=BASE_URL,
            official_owner="上海市学生事务中心",
        )
    assert detail_error.value.code == "crawler.firstjob_detail_url_rejected"


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="shanghai-firstjob",
        name="上海学生就业创业服务网",
        official_owner="上海市学生事务中心",
        category="campus",
        regions=("shanghai", "jiangsu", "zhejiang"),
        base_url=BASE_URL,
        list_url=LIST_URL,
        adapter="shanghai_firstjob",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=360,
        include_keywords=("招聘会", "长三角"),
        exclude_keywords=("实习",),
    )
