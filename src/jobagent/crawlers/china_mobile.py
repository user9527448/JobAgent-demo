"""Adapter for public China Mobile recruitment announcements."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import (
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)
from jobagent.crawlers.http import SourceHttpClient

_LIST_DATA_PATTERN = re.compile(r'R1_L0_P0\s*=\s*\[\s*"(?P<filename>\d+_\d+_\d+\.json)"\s*\]\s*;')
_DETAIL_DATA_PATTERN = re.compile(
    r'R1_L0_P0\s*=\s*\[\s*"(?P<filename>\d+_\d+_\d+_detail_(?P<id>\d+)\.json)"\s*\]\s*;'
)
_DETAIL_PATH_PATTERN = re.compile(
    r"/personal/notice/index_detail_(?P<id>\d+)\.html$",
    re.IGNORECASE,
)
_LIST_DATA_PATH_PATTERN = re.compile(
    r"/personal/notice/\d+_\d+_\d+\.json$",
    re.IGNORECASE,
)
_DETAIL_DATA_PATH_PATTERN = re.compile(
    r"/personal/notice/\d+_\d+_\d+_detail_(?P<id>\d+)\.json$",
    re.IGNORECASE,
)
_SHANGHAI = ZoneInfo("Asia/Shanghai")


class ChinaMobileRecruitmentAdapter:
    """Collect public announcements without accessing accounts or applications."""

    def __init__(
        self,
        source: SourceDefinition,
        catalog_entry: SourceCatalogEntry,
        http_client: SourceHttpClient,
    ) -> None:
        if catalog_entry.adapter != source.adapter:
            raise PermanentJobAgentError(
                "Catalog adapter does not match the database source definition.",
                code="crawler.china_mobile_adapter_mismatch",
                details={
                    "source_adapter": source.adapter,
                    "catalog_adapter": catalog_entry.adapter,
                },
            )
        self._catalog_entry = catalog_entry
        self._http_client = http_client

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Read the announcement page and its declared same-origin public JSON."""
        page = await self._http_client.get(self._catalog_entry.list_url)
        data_url = parse_china_mobile_list_data_url(
            page.response.content,
            list_url=self._catalog_entry.list_url,
        )
        response = await self._http_client.get(data_url)
        items = parse_china_mobile_list(
            response.response.content,
            base_url=self._catalog_entry.base_url,
            data_url=data_url,
            include_keywords=self._catalog_entry.include_keywords,
            exclude_keywords=self._catalog_entry.exclude_keywords,
        )
        return _after_cursor(items, cursor)

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Read one public detail shell and its declared same-origin JSON."""
        article_id = _required_metadata_int(item.metadata, "article_id", item.url)
        if _detail_id(item.url, self._catalog_entry.base_url) != article_id:
            raise _detail_rejected(item.url)
        page = await self._http_client.get(item.url)
        data_url = parse_china_mobile_detail_data_url(
            page.response.content,
            detail_url=item.url,
            base_url=self._catalog_entry.base_url,
        )
        response = await self._http_client.get(data_url)
        return parse_china_mobile_detail(
            response.response.content,
            detail_html=page.response.content,
            detail_url=item.url,
            data_url=data_url,
            metadata=item.metadata,
            official_owner=self._catalog_entry.official_owner,
        )


def parse_china_mobile_list_data_url(html: bytes, *, list_url: str) -> str:
    """Resolve the public list JSON declared by the official announcement page."""
    text = html.decode("utf-8", errors="replace")
    match = _LIST_DATA_PATTERN.search(text)
    if match is None:
        raise PermanentJobAgentError(
            "China Mobile announcement page did not declare its public list data.",
            code="crawler.china_mobile_list_page_unrecognized",
            details={"list_url": list_url},
        )
    data_url = _canonical_url(urljoin(list_url, match.group("filename")))
    if not _is_allowed_url(data_url, list_url, _LIST_DATA_PATH_PATTERN):
        raise PermanentJobAgentError(
            "China Mobile list data URL was outside the public announcement path.",
            code="crawler.china_mobile_list_data_url_rejected",
            details={"data_url": data_url},
        )
    return data_url


def parse_china_mobile_list(
    payload: bytes,
    *,
    base_url: str,
    data_url: str,
    include_keywords: Sequence[str] = (),
    exclude_keywords: Sequence[str] = (),
) -> tuple[DiscoveredItem, ...]:
    """Parse the public static JSON list into same-origin detail candidates."""
    root = _json_mapping(payload, code="crawler.china_mobile_list_unrecognized", url=data_url)
    data = root.get("cData")
    records = data.get("list") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise _list_unrecognized(data_url)

    items: list[DiscoveredItem] = []
    seen_ids: set[int] = set()
    for record in records:
        if not isinstance(record, dict):
            raise _list_unrecognized(data_url)
        organization = _required_string(record, "text1", data_url)
        title = _normalize_text(_required_string(record, "text3", data_url))
        published_raw = _required_string(record, "text4", data_url)
        detail_href = record.get("detail_href")
        if not isinstance(detail_href, str) or not detail_href.strip():
            continue
        detail_url = _canonical_url(urljoin(base_url, detail_href.strip()))
        article_id = _detail_id(detail_url, base_url)
        if article_id is None:
            continue
        if article_id in seen_ids or not _keyword_match(
            title,
            include_keywords,
            exclude_keywords,
        ):
            continue
        seen_ids.add(article_id)
        published_at = _parse_datetime(published_raw, data_url)
        company_id = record.get("text2")
        metadata: dict[str, JsonValue] = {
            "article_id": article_id,
            "title": title,
            "organization": _normalize_text(organization),
            "published_at": published_at.isoformat(),
            "published_on": published_at.date().isoformat(),
            "source_kind": "china_mobile_recruitment",
            "list_data_url": data_url,
        }
        if isinstance(company_id, str) and company_id.strip():
            metadata["company_id"] = company_id.strip()
        items.append(DiscoveredItem(url=detail_url, metadata=metadata))
    return tuple(items)


def parse_china_mobile_detail_data_url(
    html: bytes,
    *,
    detail_url: str,
    base_url: str,
) -> str:
    """Resolve and validate the public detail JSON declared by one detail shell."""
    article_id = _detail_id(detail_url, base_url)
    if article_id is None:
        raise _detail_rejected(detail_url)
    text = html.decode("utf-8", errors="replace")
    match = _DETAIL_DATA_PATTERN.search(text)
    if match is None or int(match.group("id")) != article_id:
        raise PermanentJobAgentError(
            "China Mobile detail page did not declare matching public detail data.",
            code="crawler.china_mobile_detail_page_unrecognized",
            details={"detail_url": detail_url},
        )
    data_url = _canonical_url(urljoin(detail_url, match.group("filename")))
    data_match = _DETAIL_DATA_PATH_PATTERN.fullmatch(urlsplit(data_url).path)
    if (
        not _is_allowed_url(data_url, base_url, _DETAIL_DATA_PATH_PATTERN)
        or data_match is None
        or int(data_match.group("id")) != article_id
    ):
        raise PermanentJobAgentError(
            "China Mobile detail data URL was outside the public announcement path.",
            code="crawler.china_mobile_detail_data_url_rejected",
            details={"data_url": data_url},
        )
    return data_url


def parse_china_mobile_detail(
    payload: bytes,
    *,
    detail_html: bytes,
    detail_url: str,
    data_url: str,
    metadata: Mapping[str, JsonValue],
    official_owner: str,
) -> RawDocumentInput:
    """Materialize user-visible JSON fields without treating down-time as deadline."""
    article_id = _required_metadata_int(metadata, "article_id", detail_url)
    if _detail_id(detail_url, detail_url) != article_id:
        raise _detail_rejected(detail_url)
    root = _json_mapping(payload, code="crawler.china_mobile_detail_unrecognized", url=data_url)
    data = root.get("cData")
    content = data.get("content") if isinstance(data, dict) else None
    payload_id = data.get("articleId") if isinstance(data, dict) else None
    if not isinstance(content, dict) or payload_id != article_id:
        raise _detail_unrecognized(detail_url)

    organization = _normalize_text(_required_string(content, "text1", detail_url))
    title = _normalize_text(_required_string(content, "text3", detail_url))
    published_raw = _required_string(content, "text4", detail_url)
    body_html = _required_string(content, "text6", detail_url)
    expected_title = metadata.get("title")
    expected_organization = metadata.get("organization")
    if title != expected_title or organization != expected_organization:
        raise _detail_unrecognized(detail_url)

    body_evidence = _body_evidence(body_html, detail_url)
    if not body_evidence:
        raise _detail_unrecognized(detail_url)
    published_at = _parse_datetime(published_raw, detail_url)
    evidence_lines = [
        f"招聘单位: {organization}",
        f"公告标题: {title}",
        f"发布时间: {published_raw}",
        *body_evidence,
    ]
    attachments = _attachment_evidence(content, detail_url)
    evidence_lines.extend(attachments)

    document_metadata: dict[str, JsonValue] = {
        "source_kind": "china_mobile_recruitment",
        "official_owner": official_owner,
        "article_id": article_id,
        "organization": organization,
        "organization_evidence": organization,
        "detail_data_url": data_url,
    }
    company_id = metadata.get("company_id")
    if isinstance(company_id, str) and company_id.strip():
        document_metadata["company_id"] = company_id
    source_down_at = content.get("text5")
    if isinstance(source_down_at, str) and source_down_at.strip():
        document_metadata["source_down_at"] = source_down_at.strip()
    if attachments:
        document_metadata["attachment_count"] = len(attachments)

    return RawDocumentInput(
        url=_canonical_url(detail_url),
        title=title,
        raw_html=(
            detail_html.decode("utf-8", errors="replace")
            + "\n<!-- China Mobile public detail content -->\n"
            + body_html
        ),
        raw_text="\n".join(evidence_lines),
        published_at=published_at,
        metadata=document_metadata,
    )


def _json_mapping(payload: bytes, *, code: str, url: str) -> Mapping[str, object]:
    try:
        root: object = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PermanentJobAgentError(
            "China Mobile public JSON response was not recognized.",
            code=code,
            details={"url": url},
        ) from error
    if not isinstance(root, dict):
        raise PermanentJobAgentError(
            "China Mobile public JSON response was not recognized.",
            code=code,
            details={"url": url},
        )
    return root


def _required_string(record: Mapping[object, object], field: str, url: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PermanentJobAgentError(
            "China Mobile public response is missing a required field.",
            code="crawler.china_mobile_required_field_missing",
            details={"field": field, "url": url},
        )
    return value.strip()


def _required_metadata_int(
    metadata: Mapping[str, JsonValue],
    field: str,
    detail_url: str,
) -> int:
    value = metadata.get(field)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise PermanentJobAgentError(
            "China Mobile discovered item metadata was invalid.",
            code="crawler.china_mobile_item_metadata_invalid",
            details={"field": field, "detail_url": detail_url},
        )
    return value


def _parse_datetime(value: str, url: str) -> datetime:
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise PermanentJobAgentError(
            "China Mobile public timestamp was not recognized.",
            code="crawler.china_mobile_timestamp_invalid",
            details={"value": value, "url": url},
        ) from error
    return parsed.replace(tzinfo=_SHANGHAI)


def _attachment_evidence(content: Mapping[object, object], detail_url: str) -> list[str]:
    lines: list[str] = []
    for index in range(1, 6):
        path = content.get(f"attachment{index}")
        name = content.get(f"_attachment{index}OriginalFileName")
        if not isinstance(path, str) or not path.strip():
            continue
        attachment_url = _canonical_url(urljoin(detail_url, path.strip()))
        if not _is_allowed_attachment_url(attachment_url, detail_url):
            raise PermanentJobAgentError(
                "China Mobile attachment URL was outside the official source.",
                code="crawler.china_mobile_attachment_url_rejected",
                details={"attachment_url": attachment_url, "detail_url": detail_url},
            )
        filename = _normalize_text(name) if isinstance(name, str) and name.strip() else "附件"
        lines.append(f"附件: {filename} {attachment_url}")
    return lines


def _body_evidence(body_html: str, detail_url: str) -> list[str]:
    soup = BeautifulSoup(body_html, "html.parser")
    visible = "\n".join(part.strip() for part in soup.stripped_strings if part.strip())
    lines = [visible] if visible else []
    seen_images: set[str] = set()
    for image in soup.find_all("img"):
        source = image.get("src")
        if not isinstance(source, str) or not source.strip():
            continue
        image_url = _canonical_url(urljoin(detail_url, source.strip()))
        if not _is_allowed_attachment_url(image_url, detail_url):
            raise PermanentJobAgentError(
                "China Mobile body image URL was outside the official source.",
                code="crawler.china_mobile_body_image_url_rejected",
                details={"image_url": image_url, "detail_url": detail_url},
            )
        if image_url not in seen_images:
            seen_images.add(image_url)
            lines.append(f"正文图片: {image_url}")
    return lines


def _detail_id(url: str, base_url: str) -> int | None:
    if not _is_allowed_url(url, base_url, _DETAIL_PATH_PATTERN):
        return None
    match = _DETAIL_PATH_PATTERN.fullmatch(urlsplit(url).path)
    return int(match.group("id")) if match is not None else None


def _is_allowed_url(url: str, base_url: str, path_pattern: re.Pattern[str]) -> bool:
    parsed = urlsplit(url)
    configured = urlsplit(base_url)
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
        and path_pattern.fullmatch(parsed.path) is not None
        and not parsed.query
        and not parsed.fragment
    )


def _is_allowed_attachment_url(url: str, base_url: str) -> bool:
    parsed = urlsplit(url)
    configured = urlsplit(base_url)
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
        and parsed.path.startswith("/uploadBaseDir/content/")
        and not parsed.query
        and not parsed.fragment
    )


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def _keyword_match(
    title: str,
    include_keywords: Sequence[str],
    exclude_keywords: Sequence[str],
) -> bool:
    normalized = title.casefold()
    if any(keyword.casefold() in normalized for keyword in exclude_keywords):
        return False
    return not include_keywords or any(
        keyword.casefold() in normalized for keyword in include_keywords
    )


def _after_cursor(
    items: Sequence[DiscoveredItem],
    cursor: CrawlCursor | None,
) -> tuple[DiscoveredItem, ...]:
    if not cursor:
        return tuple(items)
    published_after = cursor.get("published_after")
    if not isinstance(published_after, str):
        return tuple(items)
    return tuple(
        item
        for item in items
        if isinstance(item.metadata.get("published_on"), str)
        and str(item.metadata["published_on"]) > published_after
    )


def _list_unrecognized(data_url: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "China Mobile public announcement-list data was not recognized.",
        code="crawler.china_mobile_list_unrecognized",
        details={"data_url": data_url},
    )


def _detail_unrecognized(detail_url: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "China Mobile public announcement detail was not recognized.",
        code="crawler.china_mobile_detail_unrecognized",
        details={"detail_url": detail_url},
    )


def _detail_rejected(detail_url: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "China Mobile detail URL was outside the public announcement path.",
        code="crawler.china_mobile_detail_url_rejected",
        details={"detail_url": detail_url},
    )
