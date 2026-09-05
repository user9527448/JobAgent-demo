"""Deterministic metrics for bounded source-stability observations."""

from pathlib import Path

import pytest

from jobagent.crawlers.ncss import parse_ncss_detail, parse_ncss_list
from jobagent.crawlers.stability import evaluate_source_stability

FIXTURE_DIR = Path(__file__).parents[1] / "fixtures" / "ncss"
BASE_URL = "https://www.ncss.cn/"


def test_stability_metrics_count_success_duplicates_and_core_fields() -> None:
    items = parse_ncss_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
        include_keywords=("校招", "校园招聘", "应届", "毕业生"),
        exclude_keywords=("实习",),
    )
    fixtures = ("detail-software.html", "detail-data.html", "detail-mechanical.html")
    documents = tuple(
        parse_ncss_detail(
            (FIXTURE_DIR / fixture).read_bytes(),
            detail_url=item.url,
            metadata=item.metadata,
            official_owner="教育部学生服务与素质发展中心",
        )
        for item, fixture in zip(items, fixtures, strict=True)
    )

    result = evaluate_source_stability(
        "ncss-jobs",
        attempted=4,
        documents=(*documents, documents[0]),
        failed=0,
    )

    assert result.success_rate == 1.0
    assert result.duplicate_rate == 0.25
    assert result.core_field_completeness == 1.0
    assert result.duplicates == 1
    assert result.core_field_counts == {
        "organization": 4,
        "title": 4,
        "region": 4,
        "deadline": 4,
        "source_link": 4,
    }


def test_stability_metrics_require_attempted_accounting() -> None:
    with pytest.raises(ValueError, match="documents plus failures"):
        evaluate_source_stability(
            "ncss-jobs",
            attempted=2,
            documents=(),
            failed=1,
        )


def test_stability_metrics_accept_adapter_preserved_region_evidence() -> None:
    item = parse_ncss_list(
        (FIXTURE_DIR / "list.json").read_bytes(),
        base_url=BASE_URL,
    )[0]
    document = parse_ncss_detail(
        (FIXTURE_DIR / "detail-software.html").read_bytes(),
        detail_url=item.url,
        metadata=item.metadata,
        official_owner="教育部学生服务与素质发展中心",
    )
    metadata_only_region = type(document)(
        url=document.url,
        title=document.title,
        raw_html=document.raw_html,
        raw_text="招聘单位: 合成甲科技有限公司\n报名截止时间: 2026年9月10日",
        published_at=document.published_at,
        metadata={"region": "shanghai"},
    )

    result = evaluate_source_stability(
        "metadata-region",
        attempted=1,
        documents=(metadata_only_region,),
        failed=0,
    )

    assert result.core_field_counts["region"] == 1
    assert result.core_field_completeness == 1.0
