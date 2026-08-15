"""Explicit MIME-based registry for document parsers."""

from jobagent.core.exceptions import ConfigurationError, PermanentJobAgentError
from jobagent.parsers.contracts import (
    DocumentParser,
    ParseRequest,
    ParseResult,
    ParseStatus,
    normalize_media_type,
)


class ParserRegistry:
    """Select an explicitly registered parser without dynamic imports."""

    def __init__(self) -> None:
        self._parsers_by_name: dict[str, DocumentParser] = {}
        self._parsers_by_media_type: dict[str, DocumentParser] = {}

    def register(self, parser: DocumentParser) -> None:
        """Register one uniquely named parser and all of its unique media types."""
        name = parser.name.strip()
        if not name:
            raise ConfigurationError(
                "Parser name cannot be empty.",
                code="parser.name_empty",
            )
        if name in self._parsers_by_name:
            raise ConfigurationError(
                f"Parser '{name}' is already registered.",
                code="parser.name_duplicate",
                details={"parser": name},
            )

        try:
            media_types = tuple(
                dict.fromkeys(normalize_media_type(value) for value in parser.supported_media_types)
            )
        except ValueError as error:
            raise ConfigurationError(
                f"Parser '{name}' declares an invalid media type.",
                code="parser.media_type_invalid",
                details={"parser": name},
            ) from error
        if not media_types:
            raise ConfigurationError(
                f"Parser '{name}' must declare at least one media type.",
                code="parser.media_types_empty",
                details={"parser": name},
            )

        duplicates = tuple(
            media_type for media_type in media_types if media_type in self._parsers_by_media_type
        )
        if duplicates:
            raise ConfigurationError(
                f"Media type '{duplicates[0]}' already has a registered parser.",
                code="parser.media_type_duplicate",
                details={
                    "media_type": duplicates[0],
                    "parser": name,
                    "registered_parser": self._parsers_by_media_type[duplicates[0]].name,
                },
            )

        self._parsers_by_name[name] = parser
        for media_type in media_types:
            self._parsers_by_media_type[media_type] = parser

    def select(self, media_type: str) -> DocumentParser | None:
        """Return the parser registered for a canonicalized media type, if any."""
        try:
            normalized_media_type = normalize_media_type(media_type)
        except ValueError as error:
            raise PermanentJobAgentError(
                "Parser input media type is invalid.",
                code="parser.media_type_invalid",
                details={"media_type": media_type},
            ) from error
        return self._parsers_by_media_type.get(normalized_media_type)

    def parse(self, request: ParseRequest) -> ParseResult:
        """Parse input or return an explicit unsupported result."""
        parser = self.select(request.source.media_type)
        if parser is None:
            return ParseResult.unsupported(request.source)

        result = parser.parse(request)
        if result.source != request.source:
            raise PermanentJobAgentError(
                f"Parser '{parser.name}' returned output for another source.",
                code="parser.output_source_mismatch",
                details={"parser": parser.name, "source_id": request.source.source_id},
            )
        if result.parser_name != parser.name.strip():
            raise PermanentJobAgentError(
                f"Parser '{parser.name}' returned an inconsistent parser name.",
                code="parser.output_name_mismatch",
                details={"parser": parser.name, "result_parser": result.parser_name},
            )
        if result.status is ParseStatus.PENDING:
            raise PermanentJobAgentError(
                f"Parser '{parser.name}' returned a pending result.",
                code="parser.output_pending",
                details={"parser": parser.name},
            )
        return result

    @property
    def names(self) -> tuple[str, ...]:
        """Return registered parser names in stable order."""
        return tuple(sorted(self._parsers_by_name))

    @property
    def media_types(self) -> tuple[str, ...]:
        """Return registered media types in stable order."""
        return tuple(sorted(self._parsers_by_media_type))
