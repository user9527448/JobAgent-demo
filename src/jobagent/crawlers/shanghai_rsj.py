"""Adapter for public Shanghai public-institution recruitment notices."""

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
_DETAIL_PATH_PATTERN = re.compile(
    r"/tzpgg_17408/(?P<date>20\d{6})/(?:t0035_\d+|[0-9a-f]{32})\.html$",
    re.IGNORECASE,
)
_ORGANIZATION_TITLE_MARKERS = (
    "非教师岗位招聘公告",
    "自主招聘",
    "工作人员公开招聘",
    "公开招聘",
    "招聘公告",
)
_YEAR_AFFIX = re.compile(r"^(?:20\d{2}年(?:度|上半年|下半年)?)|(?:20\d{2}年(?:度)?)$")
_SHANGHAI = ZoneInfo("Asia/Shanghai")


class ShanghaiPublicInstitutionAdapter:
    """Collect recruitment notices only, excluding proposed-hire announcements."""

    def __init__(
        self,
        source: SourceDefinition,
        catalog_entry: SourceCatalogEntry,
        http_client: SourceHttpClient,
    ) -> None:
        if catalog_entry.adapter != source.adapter:
            raise PermanentJobAgentError(
                "Catalog adapter does not match the database source definition.",
                code="crawler.shanghai_rsj_adapter_mismatch",
                details={
                    "source_adapter": source.adapter,
                    "catalog_adapter": catalog_entry.adapter,
                },
            )
        self._catalog_entry = catalog_entry
        self._http_client = http_client

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Fetch the official public-institution column and filter recruitment links."""
        response = await self._http_client.get(self._catalog_entry.list_url)
        items = parse_shanghai_public_institution_list(
            response.response.content,
            list_url=self._catalog_entry.list_url,
            include_keywords=self._catalog_entry.include_keywords,
            exclude_keywords=self._catalog_entry.exclude_keywords,
        )
        return _after_cursor(items, cursor)

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Fetch one same-origin public recruitment article."""
        if not _is_allowed_detail_url(item.url, self._catalog_entry.list_url):
            raise PermanentJobAgentError(
                "Shanghai public-institution detail URL is outside the recruitment column.",
                code="crawler.shanghai_rsj_detail_url_rejected",
                details={"detail_url": item.url},
            )
        response = await self._http_client.get(item.url)
        return parse_shanghai_public_institution_detail(
            response.response.content,
            detail_url=item.url,
            official_owner=self._catalog_entry.official_owner,
        )


def parse_shanghai_public_institution_list(
    html: bytes,
    *,
    list_url: str,
    include_keywords: Sequence[str] = (),
    exclude_keywords: Sequence[str] = (),
) -> tuple[DiscoveredItem, ...]:
    """Discover only official recruitment-announcement detail paths."""
    soup = BeautifulSoup(html, "html.parser")
    items: list[DiscoveredItem] = []
    seen_urls: set[str] = set()
    recognized = False
    for anchor in soup.find_all("a", href=True):
        if not isinstance(anchor, Tag):
            continue
        href = anchor.get("href")
        if not isinstance(href, str):
            continue
        url = _canonical_url(urljoin(list_url, href))
        match = _detail_match(url, list_url)
        if match is None:
            continue
        recognized = True
        title_attribute = anchor.get("title")
        title = _normalize_text(
            title_attribute
            if isinstance(title_attribute, str) and title_attribute.strip()
            else anchor.get_text(" ", strip=True)
        )
        if (
            not title
            or url in seen_urls
            or not _keyword_match(title, include_keywords, exclude_keywords)
        ):
            continue
        seen_urls.add(url)
        published_at = datetime.strptime(match.group("date"), "%Y%m%d").replace(tzinfo=_SHANGHAI)
        metadata: dict[str, JsonValue] = {
            "title": title,
            "published_on": published_at.date().isoformat(),
            "source_kind": "shanghai_public_institution",
            "region": "shanghai",
        }
        items.append(DiscoveredItem(url=url, metadata=metadata))
    if not recognized:
        raise PermanentJobAgentError(
            "Shanghai public-institution recruitment list structure was not recognized.",
            code="crawler.shanghai_rsj_list_unrecognized",
            details={"list_url": list_url},
        )
    return tuple(items)


def parse_shanghai_public_institution_detail(
    html: bytes,
    *,
    detail_url: str,
    official_owner: str,
) -> RawDocumentInput:
    """Extract stable article provenance while retaining original public HTML."""
    soup = BeautifulSoup(html, "html.parser")
    title = _first_meta(soup, "ArticleTitle", "og:title") or _first_text(
        soup, "h1", "h2", ".title", ".article-title"
    )
    if title is None:
        raise PermanentJobAgentError(
            "Shanghai public-institution detail has no recognizable title.",
            code="crawler.shanghai_rsj_detail_title_missing",
            details={"detail_url": detail_url},
        )
    text = "\n".join(part.strip() for part in soup.stripped_strings if part.strip())
    if not text:
        raise PermanentJobAgentError(
            "Shanghai public-institution detail has no readable text.",
            code="crawler.shanghai_rsj_detail_body_missing",
            details={"detail_url": detail_url},
        )
    normalized_title = _normalize_text(title)
    if normalized_title not in text:
        text = f"{normalized_title}\n{text}"
    organization = _organization_from_title(normalized_title)
    if organization is not None:
        text = f"招聘单位: {organization}\n{text}"
    published_at = _parse_published_at(soup, text, detail_url)
    metadata: dict[str, JsonValue] = {
        "source_kind": "shanghai_public_institution",
        "official_owner": official_owner,
        "region": "shanghai",
    }
    if organization is not None:
        metadata["organization"] = organization
        metadata["organization_evidence"] = normalized_title
    return RawDocumentInput(
        url=_canonical_url(detail_url),
        title=normalized_title,
        raw_html=html.decode(soup.original_encoding or "utf-8", errors="replace"),
        raw_text=text,
        published_at=published_at,
        metadata=metadata,
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


def _parse_published_at(soup: BeautifulSoup, text: str, detail_url: str) -> datetime | None:
    meta_value = _first_meta(soup, "PubDate", "publishdate", "date", "Maketime")
    match = _DATE_PATTERN.search(meta_value or "") or _DATE_PATTERN.search(text)
    if match is not None:
        return datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            tzinfo=_SHANGHAI,
        )
    path_match = _DETAIL_PATH_PATTERN.fullmatch(urlsplit(detail_url).path)
    if path_match is None:
        return None
    return datetime.strptime(path_match.group("date"), "%Y%m%d").replace(tzinfo=_SHANGHAI)


def _keyword_match(
    title: str, include_keywords: Sequence[str], exclude_keywords: Sequence[str]
) -> bool:
    normalized = title.casefold()
    if any(keyword.casefold() in normalized for keyword in exclude_keywords):
        return False
    return not include_keywords or any(
        keyword.casefold() in normalized for keyword in include_keywords
    )


def _detail_match(url: str, list_url: str) -> re.Match[str] | None:
    parsed = urlsplit(url)
    configured = urlsplit(list_url)
    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname is None
        or parsed.hostname.lower() != (configured.hostname or "").lower()
        or parsed.query
    ):
        return None
    return _DETAIL_PATH_PATTERN.fullmatch(parsed.path)


def _is_allowed_detail_url(url: str, list_url: str) -> bool:
    return _detail_match(url, list_url) is not None


def _canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, "", ""))


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\ufeff", "").split())


def _organization_from_title(title: str) -> str | None:
    positions = [
        position for marker in _ORGANIZATION_TITLE_MARKERS if (position := title.find(marker)) > 0
    ]
    if not positions:
        return None
    organization = title[: min(positions)].strip(" -—\uff1a:\uff08\uff09()")
    while (stripped := _YEAR_AFFIX.sub("", organization).strip()) != organization:
        organization = stripped
    if not 2 <= len(organization) <= 120:
        return None
    return organization


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
