"""Typed loading and validation for the manually maintained source catalog."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from jobagent.core.exceptions import ConfigurationError

SOURCE_CATEGORIES = frozenset({"campus", "foreign_enterprise", "public_exam", "state_owned"})
IMPLEMENTATION_STATUSES = frozenset({"active", "planned", "blocked"})


@dataclass(frozen=True, slots=True)
class SourceCatalogEntry:
    """One human-maintained official recruitment source and its crawl policy."""

    key: str
    name: str
    official_owner: str
    category: str
    regions: tuple[str, ...]
    base_url: str
    list_url: str
    adapter: str
    implementation_status: str
    enabled: bool
    crawl_interval_minutes: int
    include_keywords: tuple[str, ...]
    exclude_keywords: tuple[str, ...]
    notes: str = ""

    @property
    def runnable(self) -> bool:
        """Return whether this entry may be handed to collection code."""
        return self.enabled and self.implementation_status == "active"


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    """Validated catalog with stable lookup by source key."""

    entries: tuple[SourceCatalogEntry, ...]

    def get(self, key: str) -> SourceCatalogEntry:
        """Return one source or raise a safe configuration error."""
        normalized_key = key.strip()
        for entry in self.entries:
            if entry.key == normalized_key:
                return entry
        raise ConfigurationError(
            f"Source catalog entry '{normalized_key}' does not exist.",
            code="crawler.catalog_source_not_found",
            details={"source_key": normalized_key},
        )

    def runnable_entries(self) -> tuple[SourceCatalogEntry, ...]:
        """Return active and explicitly enabled sources in catalog order."""
        return tuple(entry for entry in self.entries if entry.runnable)


def load_source_catalog(path: Path) -> SourceCatalog:
    """Load a TOML catalog and reject ambiguous or unsafe entries."""
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(
            "Source catalog could not be loaded.",
            code="crawler.catalog_load_failed",
            details={"path": str(path), "error_type": type(error).__name__},
        ) from error

    raw_sources = raw.get("sources")
    if not isinstance(raw_sources, list) or not raw_sources:
        raise ConfigurationError(
            "Source catalog must contain at least one [[sources]] entry.",
            code="crawler.catalog_sources_missing",
            details={"path": str(path)},
        )

    entries = tuple(_parse_entry(item, index=index) for index, item in enumerate(raw_sources))
    _ensure_unique(entries, "key")
    _ensure_unique(entries, "name")
    return SourceCatalog(entries=entries)


def _parse_entry(item: object, *, index: int) -> SourceCatalogEntry:
    if not isinstance(item, dict):
        raise _invalid_entry(index, "entry", "must be a TOML table")

    key = _required_string(item, "key", index)
    name = _required_string(item, "name", index)
    official_owner = _required_string(item, "official_owner", index)
    category = _required_string(item, "category", index)
    if category not in SOURCE_CATEGORIES:
        raise _invalid_entry(index, "category", f"must be one of {sorted(SOURCE_CATEGORIES)}")

    regions = _string_list(item, "regions", index, required=True)
    base_url = _https_url(item, "base_url", index)
    list_url = _https_url(item, "list_url", index)
    adapter = _required_string(item, "adapter", index)
    implementation_status = _required_string(item, "implementation_status", index)
    if implementation_status not in IMPLEMENTATION_STATUSES:
        raise _invalid_entry(
            index,
            "implementation_status",
            f"must be one of {sorted(IMPLEMENTATION_STATUSES)}",
        )

    enabled = item.get("enabled")
    if not isinstance(enabled, bool):
        raise _invalid_entry(index, "enabled", "must be a boolean")
    if enabled and implementation_status != "active":
        raise _invalid_entry(index, "enabled", "planned or blocked sources cannot be enabled")

    interval = item.get("crawl_interval_minutes")
    if not isinstance(interval, int) or isinstance(interval, bool) or interval <= 0:
        raise _invalid_entry(index, "crawl_interval_minutes", "must be a positive integer")

    return SourceCatalogEntry(
        key=key,
        name=name,
        official_owner=official_owner,
        category=category,
        regions=regions,
        base_url=base_url,
        list_url=list_url,
        adapter=adapter,
        implementation_status=implementation_status,
        enabled=enabled,
        crawl_interval_minutes=interval,
        include_keywords=_string_list(item, "include_keywords", index),
        exclude_keywords=_string_list(item, "exclude_keywords", index),
        notes=_optional_string(item, "notes", index),
    )


def _required_string(item: dict[str, object], field: str, index: int) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise _invalid_entry(index, field, "must be a non-empty string")
    return value.strip()


def _optional_string(item: dict[str, object], field: str, index: int) -> str:
    value = item.get(field, "")
    if not isinstance(value, str):
        raise _invalid_entry(index, field, "must be a string")
    return value.strip()


def _string_list(
    item: dict[str, object], field: str, index: int, *, required: bool = False
) -> tuple[str, ...]:
    value = item.get(field)
    if value is None and not required:
        return ()
    if not isinstance(value, list) or not value:
        requirement = "a non-empty string array" if required else "a string array"
        raise _invalid_entry(index, field, f"must be {requirement}")
    normalized: list[str] = []
    for member in value:
        if not isinstance(member, str) or not member.strip():
            raise _invalid_entry(index, field, "must contain only non-empty strings")
        clean = member.strip()
        if clean in normalized:
            raise _invalid_entry(index, field, f"contains duplicate value '{clean}'")
        normalized.append(clean)
    return tuple(normalized)


def _https_url(item: dict[str, object], field: str, index: int) -> str:
    value = _required_string(item, field, index)
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise _invalid_entry(index, field, "must be an HTTPS URL without credentials")
    return value


def _ensure_unique(entries: tuple[SourceCatalogEntry, ...], field: str) -> None:
    seen: set[str] = set()
    for entry in entries:
        value = getattr(entry, field)
        if value in seen:
            raise ConfigurationError(
                f"Source catalog contains duplicate {field} '{value}'.",
                code="crawler.catalog_duplicate",
                details={"field": field, "value": value},
            )
        seen.add(value)


def _invalid_entry(index: int, field: str, message: str) -> ConfigurationError:
    return ConfigurationError(
        f"Source catalog entry {index + 1} field '{field}' {message}.",
        code="crawler.catalog_entry_invalid",
        details={"entry_index": index, "field": field},
    )
