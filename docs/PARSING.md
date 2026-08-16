# Parser contracts and standard intermediate format

> 简体中文：[解析器协议与标准中间格式](zh-CN/PARSING.md)

JAI-013 defines the common boundary between stored source content and later format-specific parsing or extraction. It adds contracts and MIME-based selection only; PDF extraction, OCR detection, Excel heuristics, persistence orchestration, and field extraction remain JAI-014 and later Issues.

## Parser input and selection

`ParseRequest` contains immutable source identity plus non-empty bytes. `ParseSource` records:

- `source_type`: `document` or `attachment`;
- positive persisted `source_id`;
- `source_name`: a traceable file name, object path, or source URL;
- canonical `media_type`, normalized to lower case without optional parameters.

`ParserRegistry` maps each canonical MIME type to exactly one explicitly registered `DocumentParser`. Parser names and MIME registrations must be unique. Dynamic imports and configured arbitrary code execution are not allowed.

Calling `ParserRegistry.parse()` for an unregistered MIME type returns an `unsupported` `ParseResult` with code `parser.unsupported_media_type`; the input is never silently discarded. A registered parser must return the same source identity and its registered parser name, otherwise the registry raises a permanent contract error.

## Standard intermediate format

Every output block carries an `EvidenceLocation` whose `source` equals the result's `ParseSource`:

| Schema | Purpose | Required location |
|---|---|---|
| `TextBlock` | Heading, paragraph, list item, or other textual content | `PageLocation`, `LineRangeLocation`, or `CellRangeLocation` |
| `TableBlock` | Ordered rows of parsed cells | Block-level page/line/cell range |
| `TableCell` | One value inside a table | Its own page/line/cell location |
| `PageLocation` | PDF or paginated evidence | Positive one-based page number |
| `LineRangeLocation` | HTML/text evidence | Inclusive positive one-based line range |
| `CellRangeLocation` | Spreadsheet evidence | Worksheet plus inclusive one-based A1 cell range |

`TableBlock` rejects cells that reference another source. `ParseResult` applies the same invariant to every top-level block, so later extraction can always return to the persisted document or attachment without relying on parser-local state.

## PDF text parser

JAI-014 adds `PdfTextParser` and registers it explicitly through `build_parser_registry()` for `application/pdf`. It uses the existing PyMuPDF dependency and never performs network access or OCR.

- Each non-empty page becomes one normalized `TextBlock` with a one-based `PageLocation`; page order and line breaks are preserved while repeated inline whitespace is collapsed.
- Result metadata records page count, total and average non-whitespace character counts, page-level counts, and non-empty standard PDF metadata fields.
- `PdfTextPolicy.min_average_characters_per_page` defaults to `40`. A document below this deterministic average returns `ocr_required`; any partial text blocks remain available for manual review, but no OCR engine is invoked.
- Password-protected files return `failed` with `parser.encrypted_document`. Empty, invalid, damaged, or unreadable page trees return `failed` with `parser.corrupt_document`.
- Direct calls with a non-PDF media type return `parser.invalid_input`; normal callers select the parser through the registry.

The threshold is intentionally conservative and configurable for later fixture evaluation. JAI-016 will establish the broader golden-sample success metric; JAI-B01 remains the only planned OCR implementation.

## Status and error codes

`ParseStatus` matches the existing attachment state vocabulary:

| Status | Meaning |
|---|---|
| `pending` | Persisted attachment has not completed parsing; invalid as a completed `ParseResult` |
| `parsed` | At least one traceable block was produced |
| `ocr_required` | Direct parsing is insufficient and manual/OCR handling is required |
| `unsupported` | No compliant parser or supported variant exists |
| `failed` | Parsing was attempted but could not produce a valid completed result |

Non-`parsed` results require at least one `ParseIssue`. Stable `ParseErrorCode` values are:

- `parser.unsupported_media_type`
- `parser.invalid_input`
- `parser.invalid_output`
- `parser.corrupt_document`
- `parser.encrypted_document`
- `parser.ocr_required`
- `parser.failed`

An issue contains a safe message, retryability, and optional JSON-compatible details. It must not contain file contents, credentials, or personal data.

## Example

```python
source = ParseSource(
    source_type=ParseSourceType.ATTACHMENT,
    source_id=42,
    source_name="objects/ab/example.pdf",
    media_type="application/pdf",
)
result = registry.parse(ParseRequest(source=source, content=file_bytes))
```

The caller may later map `result.status` and safe diagnostics to the attachment row. JAI-013 does not add a database table for intermediate blocks or start an attachment-parsing worker.
