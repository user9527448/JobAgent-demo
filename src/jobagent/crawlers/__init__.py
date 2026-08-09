"""Public collection interfaces for source adapters and orchestration."""

from jobagent.crawlers.contracts import (
    AdapterFactory,
    CrawlBatchResult,
    CrawlCursor,
    CrawlItemFailure,
    DiscoveredItem,
    RawDocumentInput,
    SourceAdapter,
    SourceDefinition,
)
from jobagent.crawlers.orchestrator import CollectionOrchestrator
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.repository import CrawlRunRepository, SqlAlchemyCrawlRunRepository

__all__ = [
    "AdapterFactory",
    "AdapterRegistry",
    "CollectionOrchestrator",
    "CrawlBatchResult",
    "CrawlCursor",
    "CrawlItemFailure",
    "CrawlRunRepository",
    "DiscoveredItem",
    "RawDocumentInput",
    "SourceAdapter",
    "SourceDefinition",
    "SqlAlchemyCrawlRunRepository",
]
