from datetime import UTC, datetime
from pathlib import Path

import pytest

from jobagent.extraction import (
    DeterministicFieldExtractor,
    ExtractionErrorCode,
    ExtractionPolicy,
    ExtractionResult,
    FieldName,
)
from jobagent.parsers import (
    PDF_MEDIA_TYPE,
    XLSX_MEDIA_TYPE,
    PageLocation,
    ParseRequest,
    ParseResult,
    ParseSource,
    ParseSourceType,
    ParseStatus,
    TextBlock,
    TextBlockKind,
    build_parser_registry,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "attachments"


def _text_result(text: str) -> ParseResult:
    source = ParseSource(
        source_type=ParseSourceType.DOCUMENT,
        source_id=1,
        source_name="notice.txt",
        media_type="text/plain",
    )
    return ParseResult(
        source=source,
        status=ParseStatus.PARSED,
        parser_name="test_text",
        blocks=(
            TextBlock(
                kind=TextBlockKind.PARAGRAPH,
                text=text,
                location=PageLocation(source=source, page_number=1),
            ),
        ),
    )


def _fixture_result(name: str, media_type: str) -> ParseResult:
    source = ParseSource(
        source_type=ParseSourceType.ATTACHMENT,
        source_id=1,
        source_name=name,
        media_type=media_type,
    )
    return build_parser_registry().parse(
        ParseRequest(source=source, content=(FIXTURE_DIR / name).read_bytes())
    )


def _values(result: ExtractionResult, field_name: FieldName) -> list[object]:
    return [field.normalized_value for field in result.fields if field.name is field_name]


@pytest.mark.parametrize(
    ("name", "expected_deadline", "expected_regions", "expected_headcounts"),
    [
        (
            "xlsx-basic-cn.xlsx",
            datetime(2026, 9, 1, 15, 59, 59, 999999, tzinfo=UTC),
            [("shanghai",)],
            [2],
        ),
        (
            "xlsx-english.xlsx",
            datetime(2026, 9, 8, 15, 59, 59, 999999, tzinfo=UTC),
            [("beijing",)],
            [],
        ),
        (
            "xlsx-multiple-sheets.xlsx",
            datetime(2026, 9, 15, 15, 59, 59, 999999, tzinfo=UTC),
            [],
            [1],
        ),
    ],
)
def test_dates_cover_committed_golden_formats(
    name: str,
    expected_deadline: datetime,
    expected_regions: list[tuple[str, ...]],
    expected_headcounts: list[int],
) -> None:
    parsed = _fixture_result(name, XLSX_MEDIA_TYPE)

    result = DeterministicFieldExtractor().extract(parsed)

    assert _values(result, FieldName.DEADLINE) == [expected_deadline]
    assert _values(result, FieldName.REGION) == expected_regions
    assert _values(result, FieldName.HEADCOUNT) == expected_headcounts
    assert all(field.raw_value for field in result.fields)
    assert all(field.evidence.quote for field in result.fields)


def test_text_rules_preserve_raw_values_normalized_values_and_page_evidence() -> None:
    parsed = _text_result(
        "\n".join(
            (
                "报名时间\uff1a2026年8月1日 09:00 至 2026年8月15日 17:30 北京时间",
                "工作地点\uff1a上海市\u3001江苏省",
                "招聘单位\uff1a示例 科技\uff08中国\uff09有限公司",
                "招聘人数\uff1a5人",
                "学历要求\uff1a本科及以上",
                "招聘类型\uff1a校园招聘",
                "报名链接\uff1ahttps://Example.com/apply?utm_source=fixture&id=7#top",
            )
        )
    )

    result = DeterministicFieldExtractor().extract(parsed)

    assert _values(result, FieldName.START_AT) == [datetime(2026, 8, 1, 1, 0, tzinfo=UTC)]
    assert _values(result, FieldName.DEADLINE) == [datetime(2026, 8, 15, 9, 30, tzinfo=UTC)]
    assert _values(result, FieldName.REGION) == [("shanghai", "jiangsu")]
    assert _values(result, FieldName.ORGANIZATION) == ["示例 科技(中国)有限公司"]
    assert _values(result, FieldName.HEADCOUNT) == [5]
    assert _values(result, FieldName.EDUCATION) == ["bachelor_or_above"]
    assert _values(result, FieldName.CATEGORY) == ["campus"]
    assert _values(result, FieldName.APPLY_URL) == ["https://example.com/apply?id=7"]
    assert all(isinstance(field.evidence.location, PageLocation) for field in result.fields)


def test_inverted_date_range_is_rejected_with_both_raw_values() -> None:
    parsed = _text_result("报名时间\uff1a2026-09-10 09:00 至 2026-09-01 17:00")

    result = DeterministicFieldExtractor().extract(parsed)

    assert not [
        field for field in result.fields if field.name in {FieldName.START_AT, FieldName.DEADLINE}
    ]
    assert [issue.code for issue in result.issues] == [ExtractionErrorCode.DATE_RANGE_INVERTED]
    assert result.issues[0].raw_values == ("2026-09-10 09:00", "2026-09-01 17:00")
    assert len(result.issues[0].evidence) == 2


def test_invalid_date_is_not_silently_emitted() -> None:
    parsed = _text_result("截止日期\uff1a2026年2月30日")

    result = DeterministicFieldExtractor().extract(parsed)

    assert not result.fields
    assert result.issues[0].code is ExtractionErrorCode.INVALID_DATE
    assert result.issues[0].raw_values == ("2026年2月30日",)


def test_explicit_timezone_offset_is_normalized_to_utc() -> None:
    parsed = _text_result("截止时间\uff1a2026-09-01 17:30 UTC+08:00")

    result = DeterministicFieldExtractor().extract(parsed)

    assert _values(result, FieldName.DEADLINE) == [datetime(2026, 9, 1, 9, 30, tzinfo=UTC)]


@pytest.mark.parametrize(
    "text",
    [
        "报名截止时间为2026年9月8日",
        "报名截止时间\uff1a\n2026年9月8日",
        "报名时间\uff1a\n即日起至2026年9月8日17:00止",
        "报名时间\uff1a自公告发布之日起至2026年9月8日17:00止",
    ],
)
def test_public_notice_deadline_connectors_keep_only_evidenced_date(text: str) -> None:
    result = DeterministicFieldExtractor().extract(_text_result(text))

    assert len(_values(result, FieldName.DEADLINE)) == 1
    assert not _values(result, FieldName.START_AT)
    assert not result.issues


def test_relative_application_url_requires_and_uses_explicit_base_url() -> None:
    parsed = _text_result("报名链接\uff1a/apply?id=2&utm_source=fixture")

    unsupported = DeterministicFieldExtractor().extract(parsed)
    supported = DeterministicFieldExtractor().extract(
        parsed,
        base_url="https://jobs.example.cn/notices/1",
    )

    assert not unsupported.fields
    assert unsupported.issues[0].code is ExtractionErrorCode.INVALID_URL
    assert _values(supported, FieldName.APPLY_URL) == ["https://jobs.example.cn/apply?id=2"]


def test_unsupported_values_remain_diagnostics_instead_of_guesses() -> None:
    parsed = _text_result("工作地点\uff1a火星基地\n招聘人数\uff1a若干\n学历要求\uff1a优秀即可")

    result = DeterministicFieldExtractor().extract(parsed)

    assert not result.fields
    assert [issue.code for issue in result.issues] == [
        ExtractionErrorCode.UNKNOWN_ENUM,
        ExtractionErrorCode.INVALID_HEADCOUNT,
        ExtractionErrorCode.UNKNOWN_ENUM,
    ]
    assert [issue.raw_values[0] for issue in result.issues] == ["火星基地", "若干", "优秀即可"]


def test_unlabeled_text_does_not_guess_critical_fields() -> None:
    parsed = _text_result("上海 示例单位 2026-09-01 https://example.com/apply 本科 5人")

    result = DeterministicFieldExtractor().extract(parsed)

    assert result.records == ()


def test_partial_ocr_output_can_be_processed_without_inventing_fields() -> None:
    parsed = _fixture_result("pdf-sparse.pdf", PDF_MEDIA_TYPE)

    result = DeterministicFieldExtractor().extract(parsed)

    assert result.records == ()


def test_policy_rejects_unknown_timezone() -> None:
    with pytest.raises(ValueError, match="valid IANA"):
        ExtractionPolicy(timezone="Mars/Olympus_Mons")
