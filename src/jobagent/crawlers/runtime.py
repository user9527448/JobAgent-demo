"""Explicit runtime wiring for one catalog-backed source collection."""

from __future__ import annotations

from jobagent.core.exceptions import ConfigurationError
from jobagent.crawlers.catalog import SourceCatalog, SourceCatalogEntry
from jobagent.crawlers.china_mobile import ChinaMobileRecruitmentAdapter
from jobagent.crawlers.contracts import SourceDefinition
from jobagent.crawlers.firstjob import ShanghaiFirstjobAdapter
from jobagent.crawlers.http import SourceHttpClient
from jobagent.crawlers.jiangsu import JiangsuPersonnelExamAdapter
from jobagent.crawlers.ncss import NcssJobsAdapter
from jobagent.crawlers.registry import AdapterRegistry
from jobagent.crawlers.shanghai_rsj import ShanghaiPublicInstitutionAdapter


def match_catalog_entry(
    catalog: SourceCatalog,
    source: SourceDefinition,
) -> SourceCatalogEntry:
    """Resolve one runnable catalog entry without guessing by adapter name alone."""
    matches = tuple(
        entry
        for entry in catalog.runnable_entries()
        if entry.adapter == source.adapter
        and entry.name == source.name
        and entry.base_url.rstrip("/") == source.base_url.rstrip("/")
    )
    if len(matches) != 1:
        raise ConfigurationError(
            "Database source does not match exactly one runnable catalog entry.",
            code="crawler.catalog_source_mismatch",
            details={
                "source_id": source.id,
                "adapter": source.adapter,
                "matches": len(matches),
            },
        )
    return matches[0]


def build_adapter_registry(
    source: SourceDefinition,
    entry: SourceCatalogEntry,
    http_client: SourceHttpClient,
) -> AdapterRegistry:
    """Register the one explicit Adapter allowed for this manual source run."""
    registry = AdapterRegistry()
    if entry.adapter == "jiangsu_personnel_exam":
        registry.register(
            entry.adapter,
            lambda resolved: JiangsuPersonnelExamAdapter(resolved, entry, http_client),
        )
    elif entry.adapter == "shanghai_firstjob":
        registry.register(
            entry.adapter,
            lambda resolved: ShanghaiFirstjobAdapter(resolved, entry, http_client),
        )
    elif entry.adapter == "ncss_jobs":
        registry.register(
            entry.adapter,
            lambda resolved: NcssJobsAdapter(resolved, entry, http_client),
        )
    elif entry.adapter == "shanghai_public_institution":
        registry.register(
            entry.adapter,
            lambda resolved: ShanghaiPublicInstitutionAdapter(resolved, entry, http_client),
        )
    elif entry.adapter == "china_mobile_recruitment":
        registry.register(
            entry.adapter,
            lambda resolved: ChinaMobileRecruitmentAdapter(resolved, entry, http_client),
        )
    else:
        raise ConfigurationError(
            f"Adapter '{entry.adapter}' has no manual runtime wiring.",
            code="crawler.manual_adapter_not_registered",
            details={"adapter": entry.adapter, "source_id": source.id},
        )
    return registry
