"""Adapter for public Jiangsu personnel-exam announcements and schedules."""

from __future__ import annotations

import re
from collections.abc import Sequence
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup, Tag

from jobagent.core.exceptions import JsonValue, PermanentJobAgentError
from jobagent.crawlers.catalog import SourceCatalogEntry
from jobagent.crawlers.contracts import (
    CrawlCursor,
    DiscoveredItem,
    RawDocumentInput,
    SourceDefinition,
)
from jobagent.crawlers.http import SourceHttpClient

_DATE_PATTERN = re.compile(r"(?P<year>20\d{2})[年./-](?P<month>\d{1,2})[月./-](?P<day>\d{1,2})日?")
_ARTICLE_PATH_PATTERN = re.compile(
    r"/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.html$",
    re.IGNORECASE,
)
_TOPIC_PATH_PATTERN = re.compile(r"/col/col\d+/index\.html$", re.IGNORECASE)
_SHANGHAI = ZoneInfo("Asia/Shanghai")


class JiangsuPersonnelExamAdapter:
    """Collect public notices without entering registration or query systems."""

    def __init__(
        self,
        source: SourceDefinition,
        catalog_entry: SourceCatalogEntry,
        http_client: SourceHttpClient,
    ) -> None:
        if catalog_entry.adapter != source.adapter:
            raise PermanentJobAgentError(
                "Catalog adapter does not match the database source definition.",
                code="crawler.jiangsu_adapter_mismatch",
                details={
                    "source_adapter": source.adapter,
                    "catalog_adapter": catalog_entry.adapter,
                },
            )
        self._catalog_entry = catalog_entry
        self._http_client = http_client

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Fetch the official public index and filter announcement titles."""
        response = await self._http_client.get(self._catalog_entry.list_url)
        items = parse_jiangsu_list(
            response.response.content,
            list_url=self._catalog_entry.list_url,
            include_keywords=self._catalog_entry.include_keywords,
            exclude_keywords=self._catalog_entry.exclude_keywords,
        )
        return _after_cursor(items, cursor)

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Fetch one same-origin public article and retain its source content."""
        if not _is_allowed_detail_url(item.url, self._catalog_entry.list_url):
            raise PermanentJobAgentError(
                "Jiangsu detail URL is outside the configured public source.",
                code="crawler.jiangsu_detail_url_rejected",
                details={"detail_url": item.url},
            )
        response = await self._http_client.get(item.url)
        return parse_jiangsu_detail(response.response.content, detail_url=item.url)


def parse_jiangsu_list(
    html: bytes,
    *,
    list_url: str,
    include_keywords: Sequence[str] = (),
    exclude_keywords: Sequence[str] = (),
) -> tuple[DiscoveredItem, ...]:
    """Discover same-origin public article links using stable URL semantics."""
    soup = BeautifulSoup(html, "html.parser")
    candidates: list[DiscoveredItem] = []
    seen_urls: set[str] = set()
    recognized_links = False

    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        url = _normalize_discovered_url(urljoin(list_url, href), list_url)
        if not _is_allowed_detail_url(url, list_url):
            continue
        recognized_links = True

        title_attribute = anchor.get("title")
        raw_title = (
            title_attribute
            if isinstance(title_attribute, str) and title_attribute.strip()
            else anchor.get_text(" ", strip=True)
        )
        title = _normalize_title(raw_title)
        if not title or url in seen_urls:
            continue
        if not _keyword_match(title, include_keywords, exclude_keywords):
            continue
        seen_urls.add(url)

        surrounding_text = anchor.parent.get_text(" ", strip=True) if anchor.parent else title
        match = _DATE_PATTERN.search(surrounding_text)
        metadata: dict[str, JsonValue] = {
            "title": title,
            "source_kind": "jiangsu_personnel_exam",
            "region": "jiangsu",
        }
        if match is not None:
            metadata["published_on"] = _match_date(match).date().isoformat()
        candidates.append(DiscoveredItem(url=url, metadata=metadata))

    if not recognized_links:
        raise PermanentJobAgentError(
            "Jiangsu personnel-exam list structure was not recognized.",
            code="crawler.jiangsu_list_unrecognized",
            details={"list_url": list_url},
        )
    return tuple(candidates)


def parse_jiangsu_detail(html: bytes, *, detail_url: str) -> RawDocumentInput:
    """Extract stable article provenance while preserving the original page."""
    soup = BeautifulSoup(html, "html.parser")
    title = _first_meta(soup, "ArticleTitle", "og:title", "ColumnName", "channel") or _first_text(
        soup,
        "h1",
        "h2",
        ".title",
        ".article-title",
    )
    if title is None:
        raise PermanentJobAgentError(
            "Jiangsu personnel-exam detail has no recognizable title.",
            code="crawler.jiangsu_detail_title_missing",
            details={"detail_url": detail_url},
        )

    text = "\n".join(part.strip() for part in soup.stripped_strings if part.strip())
    if not text:
        raise PermanentJobAgentError(
            "Jiangsu personnel-exam detail has no readable text.",
            code="crawler.jiangsu_detail_body_missing",
            details={"detail_url": detail_url},
        )
    normalized_title = _normalize_title(title)
    if normalized_title not in text:
        text = f"{normalized_title}\n{text}"

    return RawDocumentInput(
        url=_canonical_url(detail_url),
        title=normalized_title,
        raw_html=html.decode(soup.original_encoding or "utf-8", errors="replace"),
        raw_text=text,
        published_at=_parse_published_at(soup, text),
        metadata={
            "source_kind": "jiangsu_personnel_exam",
            "official_owner": "江苏省人力资源和社会保障厅",
            "region": "jiangsu",
        },
    )


def _first_meta(soup: BeautifulSoup, *names: str) -> str | None:
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if isinstance(tag, Tag):
            content = tag.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return None


def _first_text(soup: BeautifulSoup, *selectors: str) -> str | None:
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag is not None:
            text = tag.get_text(" ", strip=True)
            if text:
                return text
    return None


def _parse_published_at(soup: BeautifulSoup, text: str) -> datetime | None:
    meta_value = _first_meta(soup, "PubDate", "publishdate", "date", "Maketime")
    match = _DATE_PATTERN.search(meta_value or "") or _DATE_PATTERN.search(text)
    return _match_date(match) if match is not None else None


def _match_date(match: re.Match[str]) -> datetime:
    return datetime(
        int(match.group("year")),
        int(match.group("month")),
        int(match.group("day")),
        tzinfo=_SHANGHAI,
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


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))


def _normalize_discovered_url(url: str, list_url: str) -> str:
    parsed = urlsplit(_canonical_url(url))
    configured = urlsplit(list_url)
    scheme = parsed.scheme
    if (
        scheme == "http"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
    ):
        scheme = "https"
    return urlunsplit((scheme, parsed.netloc, parsed.path, "", ""))


def _normalize_title(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def _is_allowed_detail_url(url: str, list_url: str) -> bool:
    parsed = urlsplit(url)
    configured = urlsplit(list_url)
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == (configured.hostname or "").lower()
        and parsed.path != configured.path
        and bool(
            _ARTICLE_PATH_PATTERN.search(parsed.path) or _TOPIC_PATH_PATTERN.search(parsed.path)
        )
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
