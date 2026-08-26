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
    CrawlRunSummary,
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
from jobagent.crawlers.firstjob import ShanghaiFirstjobAdapter
from jobagent.crawlers.http import (
    HttpCacheValidators,
    HttpFetchResult,
    HttpSourcePolicy,
    SourceHttpClient,
)
from jobagent.crawlers.jiangsu import JiangsuPersonnelExamAdapter
from jobagent.crawlers.ncss import NcssJobsAdapter
from jobagent.crawlers.orchestrator import CollectionOrchestrator
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.repository import CrawlRunRepository, SqlAlchemyCrawlRunRepository
from jobagent.crawlers.runtime import build_adapter_registry, match_catalog_entry
from jobagent.crawlers.sasac import SasacRecruitmentAdapter
from jobagent.crawlers.shanghai_rsj import ShanghaiPublicInstitutionAdapter

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
    "CrawlRunSummary",
    "DiscoveredItem",
    "HttpCacheValidators",
    "HttpFetchResult",
    "HttpSourcePolicy",
    "JiangsuPersonnelExamAdapter",
    "NcssJobsAdapter",
    "PreparedRawDocument",
    "RawDocumentInput",
    "RawDocumentRepository",
    "RawDocumentWriteResult",
    "RawDocumentWriteStatus",
    "SasacRecruitmentAdapter",
    "ShanghaiFirstjobAdapter",
    "ShanghaiPublicInstitutionAdapter",
    "SourceAdapter",
    "SourceCatalog",
    "SourceCatalogEntry",
    "SourceDefinition",
    "SourceHttpClient",
    "SqlAlchemyAttachmentRepository",
    "SqlAlchemyCrawlRunRepository",
    "SqlAlchemyRawDocumentRepository",
    "build_adapter_registry",
    "canonicalize_url",
    "content_fingerprint",
    "discover_attachment_links",
    "load_source_catalog",
    "match_catalog_entry",
    "normalize_document_content",
    "prepare_raw_document",
]
