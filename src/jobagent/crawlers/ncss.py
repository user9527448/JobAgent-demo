"""Adapter for public NCSS graduate job listings and detail pages."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
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

_JOB_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{10,64}")
_DETAIL_PATH_PATTERN = re.compile(r"/student/jobs/([A-Za-z0-9_-]{10,64})/detail\.html$")
_SHANGHAI = ZoneInfo("Asia/Shanghai")
_LIST_PARAMETERS = {
    "jobType": "",
    "areaCode": "",
    "jobName": "",
    "monthPay": "",
    "industrySectors": "",
    "property": "",
    "categoryCode": "",
    "memberLevel": "",
    "recruitType": "",
    "offset": "1",
    "limit": "30",
    "keyUnits": "",
    "degreeCode": "",
    "sourcesName": "",
    "sourcesType": "",
}


class NcssJobsAdapter:
    """Collect public NCSS job records without using login or application actions."""

    def __init__(
        self,
        source: SourceDefinition,
        catalog_entry: SourceCatalogEntry,
        http_client: SourceHttpClient,
    ) -> None:
        if catalog_entry.adapter != source.adapter:
            raise PermanentJobAgentError(
                "Catalog adapter does not match the database source definition.",
                code="crawler.ncss_adapter_mismatch",
                details={
                    "source_adapter": source.adapter,
                    "catalog_adapter": catalog_entry.adapter,
                },
            )
        self._catalog_entry = catalog_entry
        self._http_client = http_client

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Read the same public GET query used by the official job-list page."""
        separator = "&" if urlsplit(self._catalog_entry.list_url).query else "?"
        query_url = f"{self._catalog_entry.list_url}{separator}{urlencode(_LIST_PARAMETERS)}"
        response = await self._http_client.get(query_url)
        items = parse_ncss_list(
            response.response.content,
            base_url=self._catalog_entry.base_url,
            include_keywords=self._catalog_entry.include_keywords,
            exclude_keywords=self._catalog_entry.exclude_keywords,
        )
        return _after_cursor(items, cursor)

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Fetch one public detail and retain both source HTML and visible evidence."""
        if not _is_allowed_detail_url(item.url, self._catalog_entry.base_url):
            raise PermanentJobAgentError(
                "NCSS detail URL is outside the configured public source.",
                code="crawler.ncss_detail_url_rejected",
                details={"detail_url": item.url},
            )
        response = await self._http_client.get(item.url)
        return parse_ncss_detail(
            response.response.content,
            detail_url=item.url,
            metadata=item.metadata,
            official_owner=self._catalog_entry.official_owner,
        )


def parse_ncss_list(
    payload: bytes,
    *,
    base_url: str,
    include_keywords: Sequence[str] = (),
    exclude_keywords: Sequence[str] = (),
) -> tuple[DiscoveredItem, ...]:
    """Parse the public JSON list into stable same-origin detail candidates."""
    try:
        root = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _unrecognized_list(base_url) from error
    data = root.get("data") if isinstance(root, dict) and root.get("flag") is True else None
    records = data.get("list") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise _unrecognized_list(base_url)

    items: list[DiscoveredItem] = []
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise _unrecognized_list(base_url)
        job_id = _required_string(record, "jobId", base_url)
        if _JOB_ID_PATTERN.fullmatch(job_id) is None:
            raise _unrecognized_list(base_url)
        title = _normalize_text(_required_string(record, "jobName", base_url))
        organization = _normalize_text(_required_string(record, "recName", base_url))
        if job_id in seen_ids or not _keyword_match(title, include_keywords, exclude_keywords):
            continue
        seen_ids.add(job_id)

        metadata: dict[str, JsonValue] = {
            "title": title,
            "organization": organization,
            "job_id": job_id,
            "source_kind": "ncss_jobs",
        }
        _copy_optional_text(record, metadata, "areaCodeName", "region_raw")
        _copy_optional_text(record, metadata, "degreeName", "education_raw")
        _copy_optional_text(record, metadata, "major", "major_raw")
        _copy_optional_positive_int(record, metadata, "headCount", "headcount")
        published_at = _timestamp(record.get("publishDate") or record.get("updateDate"))
        if published_at is not None:
            metadata["published_at"] = published_at.isoformat()
            metadata["published_on"] = published_at.date().isoformat()
        items.append(
            DiscoveredItem(
                url=urljoin(base_url, f"/student/jobs/{job_id}/detail.html"),
                metadata=metadata,
            )
        )
    return tuple(items)


def parse_ncss_detail(
    html: bytes,
    *,
    detail_url: str,
    metadata: Mapping[str, JsonValue],
    official_owner: str,
) -> RawDocumentInput:
    """Materialize a public NCSS detail while preserving list-field evidence."""
    job_id = _required_metadata_string(metadata, "job_id", detail_url)
    title = _required_metadata_string(metadata, "title", detail_url)
    organization = _required_metadata_string(metadata, "organization", detail_url)
    match = _DETAIL_PATH_PATTERN.fullmatch(urlsplit(detail_url).path)
    if match is None or match.group(1) != job_id:
        raise PermanentJobAgentError(
            "NCSS detail URL does not match its discovered job ID.",
            code="crawler.ncss_detail_url_rejected",
            details={"detail_url": detail_url},
        )

    soup = BeautifulSoup(html, "html.parser")
    visible = "\n".join(part.strip() for part in soup.stripped_strings if part.strip())
    if not visible or title not in visible:
        raise PermanentJobAgentError(
            "NCSS public detail body was missing or did not match the discovered job.",
            code="crawler.ncss_detail_unrecognized",
            details={"detail_url": detail_url},
        )
    evidence_lines = [f"招聘单位: {organization}", f"职位名称: {title}"]
    for key, label in (
        ("region_raw", "工作地点"),
        ("education_raw", "学历要求"),
        ("headcount", "招聘人数"),
    ):
        value = metadata.get(key)
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            evidence_lines.append(f"{label}: {value}")
    raw_text = "\n".join((*evidence_lines, visible))
    published_at = _iso_datetime(metadata.get("published_at"))
    return RawDocumentInput(
        url=_canonical_url(detail_url),
        title=title,
        raw_html=html.decode(soup.original_encoding or "utf-8", errors="replace"),
        raw_text=raw_text,
        published_at=published_at,
        metadata={
            "source_kind": "ncss_jobs",
            "official_owner": official_owner,
            "job_id": job_id,
            "organization": organization,
            **{
                key: value
                for key in ("region_raw", "education_raw", "major_raw", "headcount")
                if (value := metadata.get(key)) is not None
            },
        },
    )


def _required_string(record: Mapping[object, object], field: str, source_url: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise _unrecognized_list(source_url)
    return value.strip()


def _required_metadata_string(
    metadata: Mapping[str, JsonValue], field: str, detail_url: str
) -> str:
    value = metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PermanentJobAgentError(
            "NCSS discovered item is missing required public metadata.",
            code="crawler.ncss_item_metadata_invalid",
            details={"field": field, "detail_url": detail_url},
        )
    return value.strip()


def _copy_optional_text(
    record: Mapping[object, object],
    metadata: dict[str, JsonValue],
    source_field: str,
    target_field: str,
) -> None:
    value = record.get(source_field)
    if isinstance(value, str) and value.strip():
        metadata[target_field] = _normalize_text(value)


def _copy_optional_positive_int(
    record: Mapping[object, object],
    metadata: dict[str, JsonValue],
    source_field: str,
    target_field: str,
) -> None:
    value = record.get(source_field)
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        metadata[target_field] = value


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        return None
    try:
        parsed = datetime.fromtimestamp(value / 1000, tz=UTC).astimezone(_SHANGHAI)
    except (OverflowError, OSError, ValueError):
        return None
    return parsed


def _iso_datetime(value: JsonValue | None) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None and parsed.utcoffset() is not None else None


def _keyword_match(
    title: str, include_keywords: Sequence[str], exclude_keywords: Sequence[str]
) -> bool:
    normalized = title.casefold()
    if any(keyword.casefold() in normalized for keyword in exclude_keywords):
        return False
    return not include_keywords or any(
        keyword.casefold() in normalized for keyword in include_keywords
    )


def _is_allowed_detail_url(url: str, base_url: str) -> bool:
    parsed = urlsplit(url)
    configured = urlsplit(base_url)
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
        and _DETAIL_PATH_PATTERN.fullmatch(parsed.path) is not None
        and not parsed.query
    )


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def _after_cursor(
    items: Sequence[DiscoveredItem], cursor: CrawlCursor | None
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


def _unrecognized_list(source_url: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "NCSS public job-list response structure was not recognized.",
        code="crawler.ncss_list_unrecognized",
        details={"source_url": source_url},
    )
