"""Offline contract tests for the China Mobile public-announcement Adapter."""

import asyncio
import json
from datetime import date
from pathlib import Path

import httpx
import pytest

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.china_mobile import (
    ChinaMobileRecruitmentAdapter,
    parse_china_mobile_detail,
    parse_china_mobile_detail_data_url,
    parse_china_mobile_list,
    parse_china_mobile_list_data_url,
)
from jobagent.crawlers.contracts import DiscoveredItem, RawDocumentInput, SourceDefinition
from jobagent.crawlers.http import HttpSourcePolicy, SourceHttpClient

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "china_mobile"
BASE_URL = "https://job.10086.cn/"
LIST_URL = "https://job.10086.cn/personal/notice/"
LIST_DATA_URL = f"{LIST_URL}9000001_10001_20001.json"


def test_list_page_and_static_json_discover_filtered_announcements() -> None:
    data_url = parse_china_mobile_list_data_url(
        (FIXTURE_DIR / "list.html").read_bytes(),
        list_url=LIST_URL,
    )
    items = parse_china_mobile_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
        data_url=data_url,
        include_keywords=("招聘", "校招", "应届毕业生"),
        exclude_keywords=("升级公告", "维护公告", "实习"),
    )

    assert data_url == LIST_DATA_URL
    assert [item.metadata["article_id"] for item in items] == [70001, 70002, 70003]
    assert [item.metadata["published_on"] for item in items] == [
        "2026-08-27",
        "2026-08-26",
        "2026-08-25",
    ]
    assert items[0].metadata["organization"] == "合成移动甲公司"
    assert all(item.url.startswith(f"{BASE_URL}personal/notice/") for item in items)


@pytest.mark.parametrize(
    ("index", "stem", "title", "published_on"),
    [
        (0, "detail-campus", "合成移动甲公司2027届校园招聘公告", date(2026, 8, 27)),
        (1, "detail-social", "合成移动乙公司2026年社会招聘公告", date(2026, 8, 26)),
        (2, "detail-graduate", "合成移动丙研究院应届毕业生招聘公告", date(2026, 8, 25)),
    ],
)
def test_three_synthetic_detail_contract_samples(
    index: int,
    stem: str,
    title: str,
    published_on: date,
) -> None:
    item = _items()[index]
    detail_html = (FIXTURE_DIR / f"{stem}.html").read_bytes()
    data_url = parse_china_mobile_detail_data_url(
        detail_html,
        detail_url=item.url,
        base_url=BASE_URL,
    )
    document = parse_china_mobile_detail(
        (FIXTURE_DIR / f"{stem}.json").read_bytes(),
        detail_html=detail_html,
        detail_url=item.url,
        data_url=data_url,
        metadata=item.metadata,
        official_owner="中国移动通信集团有限公司",
    )

    assert document.title == title
    assert document.published_at is not None
    assert document.published_at.date() == published_on
    assert document.published_at.tzinfo is not None
    assert f"招聘单位: {item.metadata['organization']}" in (document.raw_text or "")
    assert "报名截止时间" in (document.raw_text or "")
    assert document.raw_html is not None
    assert document.metadata["article_id"] == item.metadata["article_id"]
    assert document.metadata["source_down_at"]


def test_adapter_uses_only_public_get_pages_and_static_json() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        path = request.url.path
        if path == "/personal/notice/":
            fixture = "list.html"
        elif path.endswith("9000001_10001_20001.json"):
            fixture = "list.json"
        elif path.endswith("index_detail_70001.html"):
            fixture = "detail-campus.html"
        else:
            fixture = "detail-campus.json"
        return httpx.Response(200, content=(FIXTURE_DIR / fixture).read_bytes(), request=request)

    entry = _entry()
    source = SourceDefinition(
        id=17,
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
            adapter = ChinaMobileRecruitmentAdapter(source, entry, client)
            discovered = tuple(await adapter.discover({"published_after": "2026-08-26"}))
            document = await adapter.fetch_detail(discovered[0])
            return discovered, document

    items, document = asyncio.run(run_adapter())

    assert [item.metadata["published_on"] for item in items] == ["2026-08-27"]
    assert document.title == "合成移动甲公司2027届校园招聘公告"
    assert [request.method for request in requests] == ["GET", "GET", "GET", "GET"]
    assert requests[-1].url.path.endswith("_detail_70001.json")


def test_source_down_time_is_not_invented_as_application_deadline() -> None:
    item = _items()[0]
    detail_html = (FIXTURE_DIR / "detail-campus.html").read_bytes()
    payload = (
        (FIXTURE_DIR / "detail-campus.json")
        .read_bytes()
        .replace(
            "报名截止时间\uff1a2026年9月10日。".encode(),
            "报名安排另行通知。".encode(),
        )
    )
    document = parse_china_mobile_detail(
        payload,
        detail_html=detail_html,
        detail_url=item.url,
        data_url=f"{LIST_URL}9000001_10001_20001_detail_70001.json",
        metadata=item.metadata,
        official_owner="中国移动通信集团有限公司",
    )

    assert "报名截止时间" not in (document.raw_text or "")
    assert document.metadata["source_down_at"] == "2026-09-10 23:59:59"


def test_image_only_body_retains_official_image_evidence_without_ocr() -> None:
    item = _items()[0]
    detail_html = (FIXTURE_DIR / "detail-campus.html").read_bytes()
    image_body = '<div><img src="/uploadBaseDir/content/jpg/20260827/synthetic.jpg" alt=""></div>'
    fixture = json.loads((FIXTURE_DIR / "detail-campus.json").read_bytes())
    fixture["cData"]["content"]["text6"] = image_body
    payload = json.dumps(fixture, ensure_ascii=False).encode()
    document = parse_china_mobile_detail(
        payload,
        detail_html=detail_html,
        detail_url=item.url,
        data_url=f"{LIST_URL}9000001_10001_20001_detail_70001.json",
        metadata=item.metadata,
        official_owner="中国移动通信集团有限公司",
    )

    assert "正文图片: https://job.10086.cn/uploadBaseDir/content/jpg/" in (document.raw_text or "")
    assert "synthetic.jpg" in (document.raw_html or "")
    assert "报名截止时间" not in (document.raw_text or "")


def test_unrecognized_and_cross_origin_declarations_fail_visibly() -> None:
    with pytest.raises(PermanentJobAgentError) as list_error:
        parse_china_mobile_list_data_url(b"<html>changed</html>", list_url=LIST_URL)
    assert list_error.value.code == "crawler.china_mobile_list_page_unrecognized"

    detail_html = b'<script>R1_L0_P0=["900_1_2_detail_99999.json"];</script>'
    with pytest.raises(PermanentJobAgentError) as detail_error:
        parse_china_mobile_detail_data_url(
            detail_html,
            detail_url=f"{LIST_URL}index_detail_70001.html",
            base_url=BASE_URL,
        )
    assert detail_error.value.code == "crawler.china_mobile_detail_page_unrecognized"


def _items() -> tuple[DiscoveredItem, ...]:
    return parse_china_mobile_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
        data_url=LIST_DATA_URL,
        include_keywords=("招聘", "校招", "应届毕业生"),
        exclude_keywords=("升级公告", "维护公告", "实习"),
    )


def _entry() -> SourceCatalogEntry:
    return SourceCatalogEntry(
        key="china-mobile-recruitment",
        name="中国移动招聘",
        official_owner="中国移动通信集团有限公司",
        category="state_owned",
        regions=("national", "jiangsu", "zhejiang", "shanghai"),
        base_url=BASE_URL,
        list_url=LIST_URL,
        adapter="china_mobile_recruitment",
        implementation_status="active",
        enabled=True,
        crawl_interval_minutes=360,
        include_keywords=("招聘", "校招", "应届毕业生"),
        exclude_keywords=("升级公告", "维护公告", "实习"),
    )
