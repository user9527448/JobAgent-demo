"""Adapter for public Shanghai Firstjob graduate job-fair schedules."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from uuid import UUID
from zoneinfo import ZoneInfo

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import (
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)
from jobagent.crawlers.http import SourceHttpClient

_SHANGHAI = ZoneInfo("Asia/Shanghai")
_PUBLIC_FAIR_PATH = "/jobfair"


class ShanghaiFirstjobAdapter:
    """Collect public job-fair records without entering personal workflows."""

    def __init__(
        self,
        source: SourceDefinition,
        catalog_entry: SourceCatalogEntry,
        http_client: SourceHttpClient,
    ) -> None:
        if catalog_entry.adapter != source.adapter:
            raise PermanentJobAgentError(
                "Catalog adapter does not match the database source definition.",
                code="crawler.firstjob_adapter_mismatch",
                details={
                    "source_adapter": source.adapter,
                    "catalog_adapter": catalog_entry.adapter,
                },
            )
        self._catalog_entry = catalog_entry
        self._http_client = http_client

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Query the official public fair list and apply catalog filters."""
        response = await self._http_client.post_form_query(self._catalog_entry.list_url)
        items = parse_firstjob_list(
            response.response.content,
            public_base_url=self._catalog_entry.base_url,
            include_keywords=self._catalog_entry.include_keywords,
            exclude_keywords=self._catalog_entry.exclude_keywords,
        )
        return _after_cursor(items, cursor)

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Materialize the complete public schedule record returned at discovery."""
        return materialize_firstjob_fair(
            item,
            public_base_url=self._catalog_entry.base_url,
            official_owner=self._catalog_entry.official_owner,
        )


def parse_firstjob_list(
    payload: bytes,
    *,
    public_base_url: str,
    include_keywords: Sequence[str] = (),
    exclude_keywords: Sequence[str] = (),
) -> tuple[DiscoveredItem, ...]:
    """Parse the public read-only job-fair API into stable discovered items."""
    try:
        root = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise _unrecognized_list(public_base_url) from error
    if not isinstance(root, dict) or root.get("result") != "200":
        raise _unrecognized_list(public_base_url)
    data = root.get("data")
    records = data.get("resultList") if isinstance(data, dict) else None
    if not isinstance(records, list):
        raise _unrecognized_list(public_base_url)

    items: list[DiscoveredItem] = []
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise _unrecognized_list(public_base_url)
        fair_id = _normalize_uuid(
            _required_record_string(record, "ID", public_base_url),
            public_base_url,
        )
        title = _normalize_text(_required_record_string(record, "ZPHMC", public_base_url))
        starts_on = _parse_date(
            _required_record_string(record, "ZPSJ", public_base_url),
            public_base_url,
        )
        ends_on = _parse_date(
            _required_record_string(record, "ZPJSSJ", public_base_url),
            public_base_url,
        )
        if ends_on < starts_on:
            raise _unrecognized_list(public_base_url)
        if fair_id in seen_ids or not _keyword_match(title, include_keywords, exclude_keywords):
            continue
        seen_ids.add(fair_id)

        metadata: dict[str, JsonValue] = {
            "title": title,
            "fair_id": fair_id,
            "published_on": starts_on,
            "starts_on": starts_on,
            "ends_on": ends_on,
            "source_kind": "shanghai_firstjob_fair",
            "region": "shanghai",
        }
        poster_url = record.get("MHWZT")
        if isinstance(poster_url, str) and poster_url.strip():
            metadata["poster_url"] = _normalize_poster_url(
                poster_url,
                public_base_url,
            )
        items.append(
            DiscoveredItem(
                url=_fair_url(public_base_url, fair_id),
                metadata=metadata,
            )
        )
    return tuple(items)


def materialize_firstjob_fair(
    item: DiscoveredItem,
    *,
    public_base_url: str,
    official_owner: str,
) -> RawDocumentInput:
    """Create an immutable raw document from one complete public API record."""
    fair_id = _required_metadata_string(item, "fair_id")
    title = _required_metadata_string(item, "title")
    starts_on = _required_metadata_string(item, "starts_on")
    ends_on = _required_metadata_string(item, "ends_on")
    if not _is_allowed_fair_url(item.url, public_base_url, fair_id):
        raise PermanentJobAgentError(
            "Firstjob fair URL is outside the configured public source.",
            code="crawler.firstjob_detail_url_rejected",
            details={"detail_url": item.url},
        )
    published_at = datetime.strptime(starts_on, "%Y-%m-%d").replace(tzinfo=_SHANGHAI)
    raw_record: dict[str, JsonValue] = {
        "ID": fair_id,
        "ZPHMC": title,
        "ZPSJ": starts_on,
        "ZPJSSJ": ends_on,
    }
    poster_url = item.metadata.get("poster_url")
    if isinstance(poster_url, str):
        raw_record["MHWZT"] = poster_url

    metadata: dict[str, JsonValue] = {
        "source_kind": "shanghai_firstjob_fair",
        "official_owner": official_owner,
        "region": "shanghai",
        "fair_id": fair_id,
        "starts_on": starts_on,
        "ends_on": ends_on,
    }
    if isinstance(poster_url, str):
        metadata["poster_url"] = poster_url
    return RawDocumentInput(
        url=item.url,
        title=title,
        raw_text=json.dumps(raw_record, ensure_ascii=False, sort_keys=True),
        published_at=published_at,
        metadata=metadata,
    )


def _required_record_string(
    record: Mapping[object, object],
    field: str,
    source_url: str,
) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise _unrecognized_list(source_url)
    return value.strip()


def _required_metadata_string(item: DiscoveredItem, field: str) -> str:
    value = item.metadata.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PermanentJobAgentError(
            "Firstjob discovered item is missing required public metadata.",
            code="crawler.firstjob_item_metadata_invalid",
            details={"field": field, "detail_url": item.url},
        )
    return value.strip()


def _parse_date(value: str, source_url: str) -> str:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except ValueError as error:
        raise _unrecognized_list(source_url) from error


def _normalize_uuid(value: str, source_url: str) -> str:
    try:
        normalized = str(UUID(value))
    except ValueError as error:
        raise _unrecognized_list(source_url) from error
    if value.casefold() != normalized:
        raise _unrecognized_list(source_url)
    return normalized


def _normalize_poster_url(value: str, public_base_url: str) -> str:
    parsed = urlsplit(value.strip())
    configured_host = (urlsplit(public_base_url).hostname or "").lower()
    trusted_root = configured_host.removeprefix("www.")
    poster_host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path
        or not (poster_host == trusted_root or poster_host.endswith(f".{trusted_root}"))
    ):
        raise _unrecognized_list(public_base_url)
    return value.strip()


def _fair_url(public_base_url: str, fair_id: str) -> str:
    page_url = urljoin(public_base_url, _PUBLIC_FAIR_PATH)
    parsed = urlsplit(page_url)
    return urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            urlencode({"fair_id": fair_id}),
            "",
        )
    )


def _is_allowed_fair_url(url: str, public_base_url: str, fair_id: str) -> bool:
    parsed = urlsplit(url)
    configured = urlsplit(public_base_url)
    try:
        query = parse_qs(parsed.query, strict_parsing=True)
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
        and parsed.path == _PUBLIC_FAIR_PATH
        and query == {"fair_id": [fair_id]}
    )


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


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


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


def _unrecognized_list(source_url: str) -> PermanentJobAgentError:
    return PermanentJobAgentError(
        "Firstjob public job-fair response structure was not recognized.",
        code="crawler.firstjob_list_unrecognized",
        details={"source_url": source_url},
    )
