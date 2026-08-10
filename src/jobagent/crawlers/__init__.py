"""Public collection interfaces for source adapters and orchestration."""

from jobagent.crawlers.attachments import (
    AttachmentCandidate,
    AttachmentRecord,
    AttachmentRepository,
    AttachmentStoragePolicy,
    AttachmentStorageService,
    AttachmentStoreResult,
    AttachmentStoreStatus,
    SqlAlchemyAttachmentRepository,
    discover_attachment_links,
)
from jobagent.crawlers.catalog import SourceCatalog, SourceCatalogEntry, load_source_catalog
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
from jobagent.crawlers.documents import (
    PreparedRawDocument,
    RawDocumentRepository,
    RawDocumentWriteResult,
    RawDocumentWriteStatus,
    SqlAlchemyRawDocumentRepository,
    canonicalize_url,
    content_fingerprint,
    normalize_document_content,
    prepare_raw_document,
)
from jobagent.crawlers.http import (
    HttpCacheValidators,
    HttpFetchResult,
    HttpSourcePolicy,
    SourceHttpClient,
)
from jobagent.crawlers.jiangsu import JiangsuPersonnelExamAdapter
from jobagent.crawlers.orchestrator import CollectionOrchestrator
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.repository import CrawlRunRepository, SqlAlchemyCrawlRunRepository
from jobagent.crawlers.sasac import SasacRecruitmentAdapter

__all__ = [
    "AdapterFactory",
    "AdapterRegistry",
    "AttachmentCandidate",
    "AttachmentRecord",
    "AttachmentRepository",
    "AttachmentStoragePolicy",
    "AttachmentStorageService",
    "AttachmentStoreResult",
    "AttachmentStoreStatus",
    "CollectionOrchestrator",
    "CrawlBatchResult",
    "CrawlCursor",
    "CrawlItemFailure",
    "CrawlRunRepository",
    "DiscoveredItem",
    "HttpCacheValidators",
    "HttpFetchResult",
    "HttpSourcePolicy",
    "JiangsuPersonnelExamAdapter",
    "PreparedRawDocument",
    "RawDocumentInput",
    "RawDocumentRepository",
    "RawDocumentWriteResult",
    "RawDocumentWriteStatus",
    "SasacRecruitmentAdapter",
    "SourceAdapter",
    "SourceCatalog",
    "SourceCatalogEntry",
    "SourceDefinition",
    "SourceHttpClient",
    "SqlAlchemyAttachmentRepository",
    "SqlAlchemyCrawlRunRepository",
    "SqlAlchemyRawDocumentRepository",
    "canonicalize_url",
    "content_fingerprint",
    "discover_attachment_links",
    "load_source_catalog",
    "normalize_document_content",
    "prepare_raw_document",
]
