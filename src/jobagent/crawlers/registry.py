"""Explicit registry for source adapter factories."""

from jobagent.core.exceptions import ConfigurationError, PermanentJobAgentError
from jobagent.crawlers.contracts import AdapterFactory, SourceAdapter, SourceDefinition


class AdapterRegistry:
    """Resolve configured adapter names without dynamic imports or arbitrary code."""

    def __init__(self) -> None:
        self._factories: dict[str, AdapterFactory] = {}

    def register(self, name: str, factory: AdapterFactory) -> None:
        """Register one unique, non-empty adapter name."""
        normalized_name = name.strip()
        if not normalized_name:
            raise ConfigurationError(
                "Adapter name cannot be empty.",
                code="crawler.adapter_name_empty",
            )
        if normalized_name in self._factories:
            raise ConfigurationError(
                f"Adapter '{normalized_name}' is already registered.",
                code="crawler.adapter_duplicate",
                details={"adapter": normalized_name},
            )
        self._factories[normalized_name] = factory

    def create(self, source: SourceDefinition) -> SourceAdapter:
        """Build the configured adapter or fail before a crawl run starts."""
        factory = self._factories.get(source.adapter)
        if factory is None:
            raise PermanentJobAgentError(
                f"Adapter '{source.adapter}' is not registered.",
                code="crawler.adapter_not_registered",
                details={"adapter": source.adapter, "source_id": source.id},
            )
        return factory(source)

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered names in stable order for diagnostics."""
        return tuple(sorted(self._factories))
