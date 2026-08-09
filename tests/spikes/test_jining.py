"""Offline regression tests for the first real-source vertical Spike."""

from datetime import date, datetime
from pathlib import Path

import pytest

from jobagent.spikes.jining import (
    TARGET_DETAIL_PATH,
    SpikeParseError,
    extract_pdf_pages,
    parse_detail,
    parse_list,
)

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "jining"
TARGET_URL = f"https://hrss.jining.gov.cn{TARGET_DETAIL_PATH}"


def test_list_discovers_target_announcement() -> None:
    discovered = parse_list((FIXTURE_DIR / "list.html").read_bytes())

    target = next(item for item in discovered if item.url == TARGET_URL)
    assert target.title == "2026年度济宁市属事业单位公开招聘初级综合类岗位人员公告"
    assert target.published_on == date(2026, 1, 22)
    assert len(discovered) >= 20


def test_detail_extracts_body_and_pdf_links() -> None:
    detail = parse_detail((FIXTURE_DIR / "detail.html").read_bytes(), detail_url=TARGET_URL)

    assert detail.title == "2026年度济宁市属事业单位公开招聘初级综合类岗位人员公告"
    assert detail.published_at == datetime(2026, 1, 22, 11, 17)
    assert "一、招聘条件" in detail.body_text
    assert len(detail.attachments) == 3
    assert detail.attachments[0].file_name.endswith("岗位汇总表.pdf")
    assert "filename=566c19e3bedd4043b7786ffb15540704.pdf" in detail.attachments[0].url


def test_pdf_extracts_page_level_text() -> None:
    pages = extract_pdf_pages((FIXTURE_DIR / "positions.pdf").read_bytes())

    assert [page.page_number for page in pages] == [1, 2, 3, 4]
    assert "2026年度济宁市属事业单位公开招聘初级综合类人员岗位汇总表" in pages[0].text
    assert "党校教师1" in pages[0].text
    assert all(page.text for page in pages)


def test_list_without_cdata_items_fails_clearly() -> None:
    with pytest.raises(SpikeParseError, match="No announcement links"):
        parse_list(b"<html><body>No records</body></html>")


def test_detail_without_required_metadata_fails_clearly() -> None:
    with pytest.raises(SpikeParseError, match="ArticleTitle"):
        parse_detail(b"<html><body></body></html>", detail_url=TARGET_URL)
