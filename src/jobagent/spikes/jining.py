"""Deterministic parsers for the JAI-005 Jining source Spike."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin

import pymupdf
from bs4 import BeautifulSoup, UnicodeDammit
from bs4.element import Tag

BASE_URL = "https://hrss.jining.gov.cn"
LIST_URL = f"{BASE_URL}/col/col71291/index.html"
TARGET_DETAIL_PATH = "/art/2026/1/22/art_71291_2718366.html"

_CDATA_PATTERN = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
_ARTICLE_PATH_MARKER = "art_71291_"


class SpikeParseError(ValueError):
    """The selected source no longer matches the verified Spike structure."""


@dataclass(frozen=True, slots=True)
class DiscoveredAnnouncement:
    """Minimal item discovered from the public recruitment list."""

    title: str
    url: str
    published_on: date


@dataclass(frozen=True, slots=True)
class AttachmentLink:
    """PDF attachment linked from an announcement."""

    file_name: str
    url: str


@dataclass(frozen=True, slots=True)
class AnnouncementDetail:
    """Fields proven extractable from the selected detail page."""

    title: str
    url: str
    published_at: datetime
    body_text: str
    attachments: tuple[AttachmentLink, ...]


@dataclass(frozen=True, slots=True)
class PdfPage:
    """Page-level PDF text with a one-based source page number."""

    page_number: int
    text: str


def parse_list(html: bytes, *, base_url: str = BASE_URL) -> tuple[DiscoveredAnnouncement, ...]:
    """Parse announcement links embedded in the source's CDATA record set."""
    decoded = UnicodeDammit(html).unicode_markup
    if decoded is None:
        raise SpikeParseError("The list page encoding could not be detected.")

    discovered: list[DiscoveredAnnouncement] = []
    seen_urls: set[str] = set()
    for fragment in _CDATA_PATTERN.findall(decoded):
        fragment_soup = BeautifulSoup(fragment, "html.parser")
        for link in fragment_soup.find_all("a"):
            if not isinstance(link, Tag):
                continue
            href = link.get("href")
            if not isinstance(href, str) or _ARTICLE_PATH_MARKER not in href:
                continue

            item_url = urljoin(base_url, href)
            if item_url in seen_urls:
                continue

            list_item = link.find_parent("li")
            published_node = list_item.select_one("span.sp_time") if list_item else None
            published_text = published_node.get_text(strip=True) if published_node else ""
            title_value = link.get("title")
            title = title_value.strip() if isinstance(title_value, str) else ""
            if not title or not published_text:
                raise SpikeParseError("A list item is missing its title or publication date.")

            try:
                published_on = date.fromisoformat(published_text)
            except ValueError as error:
                raise SpikeParseError(
                    f"Invalid list publication date: {published_text!r}."
                ) from error

            seen_urls.add(item_url)
            discovered.append(
                DiscoveredAnnouncement(
                    title=title,
                    url=item_url,
                    published_on=published_on,
                )
            )

    if not discovered:
        raise SpikeParseError("No announcement links were found in the list CDATA records.")
    return tuple(discovered)


def parse_detail(html: bytes, *, detail_url: str) -> AnnouncementDetail:
    """Extract title, publication time, body text, and PDF links from a detail page."""
    soup = BeautifulSoup(html, "html.parser")
    title = _required_meta(soup, "ArticleTitle")
    published_text = _required_meta(soup, "pubdate")
    try:
        published_at = datetime.fromisoformat(published_text)
    except ValueError as error:
        raise SpikeParseError(f"Invalid detail publication time: {published_text!r}.") from error

    body_node = soup.select_one("#zoom .wenz")
    if body_node is None:
        raise SpikeParseError("The detail body '#zoom .wenz' was not found.")
    for discarded in body_node.select("script, style"):
        discarded.decompose()
    body_text = _normalized_text(body_node.get_text("\n", strip=True))
    if not body_text:
        raise SpikeParseError("The detail body is empty.")

    attachments: list[AttachmentLink] = []
    for link in body_node.find_all("a"):
        if not isinstance(link, Tag):
            continue
        href = link.get("href")
        file_name = link.get_text(" ", strip=True)
        if not isinstance(href, str) or ".pdf" not in href.lower():
            continue
        if not file_name:
            raise SpikeParseError("A PDF attachment is missing its display name.")
        attachments.append(AttachmentLink(file_name=file_name, url=urljoin(detail_url, href)))

    if not attachments:
        raise SpikeParseError("No PDF attachments were found on the detail page.")

    return AnnouncementDetail(
        title=title,
        url=detail_url,
        published_at=published_at,
        body_text=body_text,
        attachments=tuple(attachments),
    )


def extract_pdf_pages(pdf_bytes: bytes) -> tuple[PdfPage, ...]:
    """Extract normalized text from every PDF page while preserving page numbers."""
    pages: list[PdfPage] = []
    # PyMuPDF exposes this typed public helper through an untyped Document constructor.
    with pymupdf.open(  # type: ignore[no-untyped-call]
        stream=pdf_bytes,
        filetype="pdf",
    ) as document:
        for page_index, page in enumerate(document):
            pages.append(
                PdfPage(
                    page_number=page_index + 1,
                    text=_normalized_text(page.get_text("text", sort=True)),
                )
            )
    if not pages:
        raise SpikeParseError("The PDF contains no pages.")
    return tuple(pages)


def _required_meta(soup: BeautifulSoup, name: str) -> str:
    node = soup.find("meta", attrs={"name": name})
    if not isinstance(node, Tag):
        raise SpikeParseError(f"Required metadata {name!r} was not found.")
    value = node.get("content")
    if not isinstance(value, str) or not value.strip():
        raise SpikeParseError(f"Required metadata {name!r} is empty.")
    return value.strip()


def _normalized_text(text: str) -> str:
    return "\n".join(line for raw_line in text.splitlines() if (line := raw_line.strip()))
