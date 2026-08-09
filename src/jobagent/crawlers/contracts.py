"""Typed boundaries shared by source adapters and collection orchestration."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, TypeAlias

from jobagent.core.exceptions import JsonValue

CrawlCursor: TypeAlias = dict[str, JsonValue]


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    """Source fields needed by an adapter without exposing an ORM entity."""

    id: int
    name: str
    base_url: str
    category: str
    adapter: str
    enabled: bool


@dataclass(frozen=True, slots=True)
class DiscoveredItem:
    """A detail-page candidate emitted by an adapter's discovery step."""

    url: str
    metadata: dict[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RawDocumentInput:
    """Raw detail output handed to the later idempotent persistence stage."""

    url: str
    title: str
    raw_html: str | None = None
    raw_text: str | None = None
    published_at: datetime | None = None
    metadata: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.raw_html is None and self.raw_text is None:
            raise ValueError("A raw document must contain HTML or text.")


class SourceAdapter(Protocol):
    """The only source-specific behavior required by the common pipeline."""

    async def discover(self, cursor: CrawlCursor | None) -> Sequence[DiscoveredItem]:
        """Return detail-page candidates after the supplied incremental cursor."""
        ...

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput:
        """Fetch and parse one discovered detail page into raw source content."""
        ...


AdapterFactory: TypeAlias = Callable[[SourceDefinition], SourceAdapter]


@dataclass(frozen=True, slots=True)
class CrawlItemFailure:
    """Safe, structured information about one isolated detail failure."""

    url: str
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> dict[str, JsonValue]:
        """Return JSON-compatible data for crawl-run statistics."""
        return {
            "url": self.url,
            "code": self.code,
            "message": self.message,
            "retryable": self.retryable,
        }


@dataclass(frozen=True, slots=True)
class CrawlBatchResult:
    """One completed batch and the documents ready for downstream storage."""

    run_id: int
    source_id: int
    status: str
    documents: tuple[RawDocumentInput, ...]
    failures: tuple[CrawlItemFailure, ...]
    stats: dict[str, JsonValue]
