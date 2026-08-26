"""Evidence-preserving deterministic extraction from parser intermediates."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, timezone
from typing import Final
from urllib.parse import urljoin
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jobagent.core.exceptions import PermanentJobAgentError
from jobagent.crawlers.documents import canonicalize_url
from jobagent.extraction.contracts import (
    ExtractedField,
    ExtractionErrorCode,
    ExtractionEvidence,
    ExtractionIssue,
    ExtractionRecord,
    ExtractionResult,
    FieldName,
)
from jobagent.extraction.dictionaries import (
    normalize_category,
    normalize_education,
    normalize_regions,
)
from jobagent.parsers import ParseResult, TableBlock, TextBlock

EXTRACTOR_VERSION: Final = "deterministic-v1"

_DATE_PATTERN: Final = re.compile(
    r"(?P<year>20\d{2})\s*(?:年|[-/.])\s*"
    r"(?P<month>1[0-2]|0?[1-9])\s*(?:月|[-/.])\s*"
    r"(?P<day>3[01]|[12]\d|0?[1-9])(?!\d)(?:\s*日)?"
    r"(?:[ T\s]+(?P<hour>[01]?\d|2[0-3])"
    r"(?:[:\uff1a时](?P<minute>[0-5]\d))"
    r"(?:[:\uff1a分](?P<second>[0-5]\d))?\s*(?:秒)?)?"
    r"(?:\s*(?P<timezone>(?:UTC|GMT)?[+-](?:0?\d|1[0-4])(?::?[0-5]\d)?|"
    r"Asia/Shanghai|北京时间|中国标准时间|UTC|GMT|Z))?",
    re.IGNORECASE,
)
_HEADCOUNT_PATTERN: Final = re.compile(r"^(?P<count>[1-9]\d*)\s*(?:人|名|个)?$")
_URL_PATTERN: Final = re.compile(
    r"https?://[^\s<>\"'\uff0c\u3002\uff1b;]+|/[^\s<>\"'\uff0c\u3002\uff1b;]+",
    re.I,
)

_RANGE_LABELS: Final = (
    "报名时间",
    "报名日期",
    "申请时间",
    "application period",
    "registration period",
)
_RELATIVE_RANGE_START_PATTERN: Final = re.compile(
    r"(?:即日起|自(?:本)?公告发布之日(?:起)?|自发布之日(?:起)?)\s*(?:至|到)",
    re.IGNORECASE,
)
_TEXT_LABELS: Final[dict[FieldName, tuple[str, ...]]] = {
    FieldName.START_AT: ("报名开始时间", "报名开始", "开始日期", "start date", "application start"),
    FieldName.DEADLINE: (
        "报名截止时间",
        "报名截止",
        "截止日期",
        "截止时间",
        "application deadline",
        "application date",
        "closing date",
    ),
    FieldName.REGION: ("工作地点", "招聘地区", "地区", "location", "work location"),
    FieldName.ORGANIZATION: ("招聘单位", "用人单位", "单位", "organization", "employer"),
    FieldName.APPLY_URL: (
        "报名链接",
        "报名网址",
        "申请链接",
        "投递链接",
        "apply url",
        "application url",
        "registration url",
    ),
    FieldName.HEADCOUNT: ("招聘人数", "计划招聘", "人数", "headcount", "number"),
    FieldName.EDUCATION: ("学历要求", "学历", "education", "qualification"),
    FieldName.CATEGORY: ("招聘类型", "招聘类别", "类别", "recruitment type", "category"),
}
_TABLE_HEADERS: Final[dict[FieldName, frozenset[str]]] = {
    FieldName.START_AT: frozenset(
        {"报名开始时间", "报名开始", "开始日期", "startdate", "applicationstart"}
    ),
    FieldName.DEADLINE: frozenset(
        {
            "报名截止时间",
            "报名截止",
            "截止日期",
            "截止时间",
            "applicationdeadline",
            "applicationdate",
            "closingdate",
        }
    ),
    FieldName.REGION: frozenset({"工作地点", "招聘地区", "地区", "location", "worklocation"}),
    FieldName.ORGANIZATION: frozenset({"招聘单位", "用人单位", "单位", "organization", "employer"}),
    FieldName.APPLY_URL: frozenset(
        {
            "报名链接",
            "报名网址",
            "申请链接",
            "投递链接",
            "applyurl",
            "applicationurl",
            "registrationurl",
        }
    ),
    FieldName.HEADCOUNT: frozenset({"招聘人数", "人数", "headcount", "number"}),
    FieldName.EDUCATION: frozenset({"学历要求", "学历", "education", "qualification"}),
    FieldName.CATEGORY: frozenset({"招聘类型", "招聘类别", "类别", "recruitmenttype", "category"}),
}


@dataclass(frozen=True, slots=True)
class ExtractionPolicy:
    """Configuration for deterministic time and URL normalization."""

    timezone: str = "Asia/Shanghai"

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as error:
            raise ValueError("Extraction timezone must be a valid IANA identifier.") from error


class DeterministicFieldExtractor:
    """Extract only directly evidenced values from parser blocks."""

    def __init__(self, policy: ExtractionPolicy | None = None) -> None:
        self._policy = policy or ExtractionPolicy()
        self._timezone = ZoneInfo(self._policy.timezone)

    def extract(self, result: ParseResult, *, base_url: str | None = None) -> ExtractionResult:
        """Return deterministic fields without merging blocks or persisting evidence."""
        records: list[ExtractionRecord] = []
        for block in result.blocks:
            if isinstance(block, TextBlock):
                record = self._extract_text(block, base_url=base_url)
                if record is not None:
                    records.append(record)
            elif isinstance(block, TableBlock):
                records.extend(self._extract_table(block, base_url=base_url))
        return ExtractionResult(
            source=result.source,
            records=tuple(records),
            extractor_version=EXTRACTOR_VERSION,
        )

    def _extract_text(
        self,
        block: TextBlock,
        *,
        base_url: str | None,
    ) -> ExtractionRecord | None:
        fields: list[ExtractedField] = []
        issues: list[ExtractionIssue] = []
        consumed_date_spans: set[tuple[int, int]] = set()

        for label_match in _iter_labels(block.text, _RANGE_LABELS):
            value_start = _label_value_start(block.text, label_match)
            if value_start is None:
                continue
            window_end = _value_window_end(block.text, value_start)
            matches = list(_DATE_PATTERN.finditer(block.text, value_start, window_end))
            if len(matches) < 2:
                if matches:
                    evidence = _text_evidence(block, label_match.start(), matches[0].end())
                    relative_prefix = block.text[value_start : matches[0].start()]
                    if _RELATIVE_RANGE_START_PATTERN.search(relative_prefix) is not None:
                        outcome = self._date_field(
                            FieldName.DEADLINE,
                            matches[0].group(0),
                            evidence,
                            rule_id="date.range.relative_start.deadline",
                        )
                        if isinstance(outcome, ExtractedField):
                            fields.append(outcome)
                        else:
                            issues.append(outcome)
                        consumed_date_spans.add(matches[0].span())
                        continue
                    issues.append(
                        ExtractionIssue(
                            code=ExtractionErrorCode.AMBIGUOUS_DATE_RANGE,
                            message="A date-range label requires both a start and a deadline.",
                            raw_values=(matches[0].group(0).strip(),),
                            evidence=(evidence,),
                        )
                    )
                    consumed_date_spans.add(matches[0].span())
                continue
            start_match, deadline_match = matches[:2]
            range_evidence = _text_evidence(block, label_match.start(), deadline_match.end())
            start = self._date_field(
                FieldName.START_AT,
                start_match.group(0),
                range_evidence,
                rule_id="date.range.start",
            )
            deadline = self._date_field(
                FieldName.DEADLINE,
                deadline_match.group(0),
                range_evidence,
                rule_id="date.range.deadline",
            )
            for outcome in (start, deadline):
                if isinstance(outcome, ExtractedField):
                    fields.append(outcome)
                else:
                    issues.append(outcome)
            consumed_date_spans.update((start_match.span(), deadline_match.span()))

        for field_name in (FieldName.START_AT, FieldName.DEADLINE):
            for label_match in _iter_labels(block.text, _TEXT_LABELS[field_name]):
                value_start = _label_value_start(block.text, label_match)
                if value_start is None:
                    continue
                window_end = _value_window_end(block.text, value_start)
                date_match = _DATE_PATTERN.search(block.text, value_start, window_end)
                if date_match is None or date_match.span() in consumed_date_spans:
                    continue
                evidence = _text_evidence(block, label_match.start(), date_match.end())
                outcome = self._date_field(
                    field_name,
                    date_match.group(0),
                    evidence,
                    rule_id=f"date.label.{field_name.value}",
                )
                if isinstance(outcome, ExtractedField):
                    fields.append(outcome)
                else:
                    issues.append(outcome)
                consumed_date_spans.add(date_match.span())

        for field_name in (
            FieldName.REGION,
            FieldName.ORGANIZATION,
            FieldName.APPLY_URL,
            FieldName.HEADCOUNT,
            FieldName.EDUCATION,
            FieldName.CATEGORY,
        ):
            for label_match, raw_value, value_span in _labeled_values(
                block.text, _TEXT_LABELS[field_name]
            ):
                evidence = _text_evidence(block, label_match.start(), value_span[1])
                normalized_outcome = self._normalize_field(
                    field_name,
                    raw_value,
                    evidence,
                    base_url=base_url,
                    rule_id=f"text.label.{field_name.value}",
                )
                if normalized_outcome is None:
                    continue
                if isinstance(normalized_outcome, ExtractedField):
                    fields.append(normalized_outcome)
                else:
                    issues.append(normalized_outcome)

        fields = _deduplicate_fields(fields)
        fields, date_issues = _reject_inverted_dates(fields)
        issues.extend(date_issues)
        if not fields and not issues:
            return None
        return ExtractionRecord(location=block.location, fields=tuple(fields), issues=tuple(issues))

    def _extract_table(
        self,
        block: TableBlock,
        *,
        base_url: str | None,
    ) -> list[ExtractionRecord]:
        headers = tuple(_header_field(cell.value) for cell in block.rows[0])
        records: list[ExtractionRecord] = []
        for row in block.rows[1:]:
            fields: list[ExtractedField] = []
            issues: list[ExtractionIssue] = []
            for field_name, cell in zip(headers, row, strict=False):
                if field_name is None or not cell.value.strip():
                    continue
                evidence = ExtractionEvidence(location=cell.location, quote=cell.value)
                if field_name in {FieldName.START_AT, FieldName.DEADLINE}:
                    field_outcome: ExtractedField | ExtractionIssue | None = self._date_field(
                        field_name,
                        cell.value,
                        evidence,
                        rule_id=f"table.header.{field_name.value}",
                    )
                else:
                    field_outcome = self._normalize_field(
                        field_name,
                        cell.value,
                        evidence,
                        base_url=base_url,
                        rule_id=f"table.header.{field_name.value}",
                    )
                if field_outcome is None:
                    continue
                if isinstance(field_outcome, ExtractedField):
                    fields.append(field_outcome)
                else:
                    issues.append(field_outcome)
            fields, date_issues = _reject_inverted_dates(fields)
            issues.extend(date_issues)
            if fields or issues:
                records.append(
                    ExtractionRecord(
                        location=row[0].location,
                        fields=tuple(fields),
                        issues=tuple(issues),
                    )
                )
        return records

    def _date_field(
        self,
        field_name: FieldName,
        raw_value: str,
        evidence: ExtractionEvidence,
        *,
        rule_id: str,
    ) -> ExtractedField | ExtractionIssue:
        raw_value = raw_value.strip()
        try:
            normalized = _parse_datetime(
                raw_value,
                field_name=field_name,
                default_timezone=self._timezone,
            )
        except ValueError:
            return ExtractionIssue(
                code=ExtractionErrorCode.INVALID_DATE,
                message="The evidenced date value is invalid or unsupported.",
                raw_values=(raw_value,),
                evidence=(evidence,),
                field_name=field_name,
            )
        return ExtractedField(
            name=field_name,
            raw_value=raw_value,
            normalized_value=normalized,
            evidence=evidence,
            rule_id=rule_id,
        )

    def _normalize_field(
        self,
        field_name: FieldName,
        raw_value: str,
        evidence: ExtractionEvidence,
        *,
        base_url: str | None,
        rule_id: str,
    ) -> ExtractedField | ExtractionIssue | None:
        raw_value = raw_value.strip()
        normalized: int | str | tuple[str, ...] | None
        if field_name is FieldName.REGION:
            normalized = normalize_regions(raw_value)
            if normalized is None:
                return _unknown_enum(field_name, raw_value, evidence)
        elif field_name is FieldName.ORGANIZATION:
            normalized = " ".join(unicodedata.normalize("NFKC", raw_value).split())
        elif field_name is FieldName.APPLY_URL:
            url_match = _URL_PATTERN.search(raw_value)
            if url_match is None:
                return ExtractionIssue(
                    code=ExtractionErrorCode.INVALID_URL,
                    message="The evidenced application URL is invalid or unsupported.",
                    raw_values=(raw_value,),
                    evidence=(evidence,),
                    field_name=field_name,
                )
            candidate = url_match.group(0)
            if candidate.startswith("/") and base_url is None:
                return ExtractionIssue(
                    code=ExtractionErrorCode.INVALID_URL,
                    message="A relative application URL requires an evidenced base URL.",
                    raw_values=(candidate,),
                    evidence=(evidence,),
                    field_name=field_name,
                )
            try:
                normalized = canonicalize_url(urljoin(base_url or "", candidate))
            except PermanentJobAgentError:
                return ExtractionIssue(
                    code=ExtractionErrorCode.INVALID_URL,
                    message="The evidenced application URL is invalid or unsupported.",
                    raw_values=(candidate,),
                    evidence=(evidence,),
                    field_name=field_name,
                )
            raw_value = candidate
        elif field_name is FieldName.HEADCOUNT:
            match = _HEADCOUNT_PATTERN.fullmatch(raw_value)
            if match is None:
                return ExtractionIssue(
                    code=ExtractionErrorCode.INVALID_HEADCOUNT,
                    message="The evidenced headcount is not one positive exact integer.",
                    raw_values=(raw_value,),
                    evidence=(evidence,),
                    field_name=field_name,
                )
            normalized = int(match.group("count"))
        elif field_name is FieldName.EDUCATION:
            normalized = normalize_education(raw_value)
            if normalized is None:
                return _unknown_enum(field_name, raw_value, evidence)
        elif field_name is FieldName.CATEGORY:
            normalized = normalize_category(raw_value)
            if normalized is None:
                return _unknown_enum(field_name, raw_value, evidence)
        else:
            return None
        return ExtractedField(
            name=field_name,
            raw_value=raw_value,
            normalized_value=normalized,
            evidence=evidence,
            rule_id=rule_id,
        )


def _parse_datetime(
    raw_value: str,
    *,
    field_name: FieldName,
    default_timezone: ZoneInfo,
) -> datetime:
    match = _DATE_PATTERN.search(raw_value.strip())
    if match is None:
        raise ValueError("unsupported date")
    parsed_date = date(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
    )
    hour = match.group("hour")
    if hour is None:
        parsed_time = time.min if field_name is FieldName.START_AT else time.max
    else:
        parsed_time = time(
            int(hour),
            int(match.group("minute")),
            int(match.group("second") or 0),
        )
    source_timezone = _parse_timezone(match.group("timezone"), default_timezone)
    return datetime.combine(parsed_date, parsed_time, source_timezone).astimezone(UTC)


def _parse_timezone(raw_value: str | None, default_timezone: ZoneInfo) -> timezone | ZoneInfo:
    if raw_value is None or not raw_value.strip():
        return default_timezone
    value = raw_value.strip().casefold()
    if value in {"z", "utc", "gmt"}:
        return UTC
    if value in {"asia/shanghai", "北京时间", "中国标准时间"}:
        return ZoneInfo("Asia/Shanghai")
    value = value.removeprefix("utc").removeprefix("gmt")
    sign = 1 if value[0] == "+" else -1
    offset = value[1:]
    if ":" in offset:
        hours_text, minutes_text = offset.split(":", maxsplit=1)
    elif len(offset) > 2:
        hours_text, minutes_text = offset[:-2], offset[-2:]
    else:
        hours_text, minutes_text = offset, "0"
    delta = timedelta(hours=int(hours_text), minutes=int(minutes_text))
    if delta > timedelta(hours=14):
        raise ValueError("invalid timezone offset")
    return timezone(sign * delta)


def _header_field(raw_header: str) -> FieldName | None:
    key = _header_key(raw_header)
    for field_name, aliases in _TABLE_HEADERS.items():
        if key in aliases:
            return field_name
    return None


def _header_key(raw_header: str) -> str:
    return "".join(
        character.casefold()
        for character in unicodedata.normalize("NFKC", raw_header)
        if character.isalnum()
    )


def _iter_labels(text: str, labels: tuple[str, ...]) -> list[re.Match[str]]:
    pattern = re.compile(
        "|".join(re.escape(label) for label in sorted(labels, key=len, reverse=True)), re.I
    )
    return list(pattern.finditer(text))


def _value_window_end(text: str, start: int) -> int:
    endings = [
        position
        for marker in ("\n", "\r", "\uff1b", ";")
        if (position := text.find(marker, start)) >= 0
    ]
    return min(endings) if endings else min(len(text), start + 240)


def _label_value_start(text: str, label_match: re.Match[str]) -> int | None:
    value_start = label_match.end()
    while value_start < len(text) and text[value_start] in " \t":
        value_start += 1
    if value_start >= len(text) or text[value_start] not in ":\uff1a为":
        return None
    value_start += 1
    while value_start < len(text) and text[value_start] in " \t\r\n":
        value_start += 1
    return value_start


def _labeled_values(
    text: str,
    labels: tuple[str, ...],
) -> list[tuple[re.Match[str], str, tuple[int, int]]]:
    values: list[tuple[re.Match[str], str, tuple[int, int]]] = []
    for label_match in _iter_labels(text, labels):
        value_start = _label_value_start(text, label_match)
        if value_start is None:
            continue
        value_end = _value_window_end(text, value_start)
        raw_value = text[value_start:value_end].strip()
        if raw_value:
            stripped_start = text.find(raw_value, value_start, value_end)
            values.append(
                (label_match, raw_value, (stripped_start, stripped_start + len(raw_value)))
            )
    return values


def _text_evidence(block: TextBlock, start: int, end: int) -> ExtractionEvidence:
    return ExtractionEvidence(location=block.location, quote=block.text[start:end].strip())


def _unknown_enum(
    field_name: FieldName,
    raw_value: str,
    evidence: ExtractionEvidence,
) -> ExtractionIssue:
    return ExtractionIssue(
        code=ExtractionErrorCode.UNKNOWN_ENUM,
        message="The evidenced value is outside the deterministic normalization dictionary.",
        raw_values=(raw_value,),
        evidence=(evidence,),
        field_name=field_name,
    )


def _reject_inverted_dates(
    fields: list[ExtractedField],
) -> tuple[list[ExtractedField], list[ExtractionIssue]]:
    starts = [field for field in fields if field.name is FieldName.START_AT]
    deadlines = [field for field in fields if field.name is FieldName.DEADLINE]
    if not starts or not deadlines:
        return fields, []
    inverted = [
        (start, deadline)
        for start in starts
        for deadline in deadlines
        if isinstance(start.normalized_value, datetime)
        and isinstance(deadline.normalized_value, datetime)
        and start.normalized_value > deadline.normalized_value
    ]
    if not inverted:
        return fields, []
    date_fields = starts + deadlines
    issue = ExtractionIssue(
        code=ExtractionErrorCode.DATE_RANGE_INVERTED,
        message="The evidenced application start is later than its deadline.",
        raw_values=tuple(field.raw_value for field in date_fields),
        evidence=tuple(field.evidence for field in date_fields),
    )
    return [
        field for field in fields if field.name not in {FieldName.START_AT, FieldName.DEADLINE}
    ], [issue]


def _deduplicate_fields(fields: list[ExtractedField]) -> list[ExtractedField]:
    unique: list[ExtractedField] = []
    keys: set[tuple[object, ...]] = set()
    for field in fields:
        key = (
            field.name,
            field.raw_value,
            field.normalized_value,
            field.evidence.location,
            field.evidence.quote,
        )
        if key not in keys:
            keys.add(key)
            unique.append(field)
    return unique
