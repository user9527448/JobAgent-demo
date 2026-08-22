# Deterministic Field Extraction and Normalization

> Simplified Chinese mirror: [`zh-CN/EXTRACTION.md`](zh-CN/EXTRACTION.md).

JAI-017 adds an in-memory deterministic extraction layer over the traceable parser intermediate format. It does not write business tables or evidence rows. The extractor emits a value only when a parser block or table cell directly supports it.

## Contracts

`DeterministicFieldExtractor.extract()` accepts one `ParseResult` and returns an `ExtractionResult`. Records preserve parser order and correspond to one text block or one table data row.

Every `ExtractedField` contains:

- a stable `FieldName`;
- the exact supported `raw_value`;
- a deterministic `normalized_value`;
- `ExtractionEvidence` with the parser page/line/cell location and a source quote;
- a stable `rule_id` and result-level `extractor_version`.

The contracts reject empty evidence, naive date-times, non-positive headcounts, empty region sets, and mixed parser sources. Unsupported or contradictory evidenced values become `ExtractionIssue` objects retaining raw values and evidence; they are never silently converted into guessed fields.

## Supported fields

| Field | Deterministic input | Normalized output |
|---|---|---|
| `start_at` / `deadline` | Labeled text dates/ranges or recognized table headers | UTC-aware `datetime` |
| `region` | Labeled text or location/region columns | Ordered tuple of stable provincial-level codes |
| `organization` | Explicit organization/employer label or column | NFKC and whitespace-normalized text |
| `apply_url` | Explicit application/registration label or column | Canonical HTTP(S) URL |
| `headcount` | One exact positive integer, optionally followed by 人/名/个 | Positive `int` |
| `education` | Exact bounded dictionary value | Stable education enum string |
| `category` | Exact bounded recruitment-type dictionary value | Stable recruitment category string |

Unlabeled dates, regions, organizations, URLs, education terms, and numbers in free text are ignored. This prevents an announcement source link, publication date, or incidental organization name from being relabeled as an application field.

## Date and timezone rules

The accepted golden formats are `YYYY-MM-DD`, `YYYY/MM/DD`, and `YYYY年M月D日`; an evidenced time and supported timezone may follow. Date ranges require two evidenced values. The configured default timezone is `Asia/Shanghai`, while `Z`, `UTC`, `GMT`, `Asia/Shanghai`, Beijing-time labels, and numeric UTC/GMT offsets are recognized explicitly.

All outputs are converted to UTC. A date-only start uses local `00:00:00`; a date-only deadline uses the end of the local day. Invalid calendar values produce `extraction.invalid_date`. If a start is later than its deadline, both date fields are removed from that record and `extraction.date_range_inverted` retains both raw values and evidence.

## Dictionaries and URL boundaries

The region dictionary covers national scope and provincial-level mainland, Hong Kong, Macao, and Taiwan names with bounded Chinese/English aliases. Concrete regions take precedence over a simultaneous national alias. Education normalization distinguishes exact requirements such as `bachelor`, `bachelor_or_above`, `master`, `master_or_above`, and `doctorate`; unsupported prose remains a diagnostic.

Application URLs must be directly labeled and use HTTP(S). Relative paths require an explicitly supplied source `base_url`; the extractor never invents a host. Canonicalization removes fragments and tracking parameters while retaining business query parameters. Credentials and unsupported schemes are rejected.

## Issue boundaries

- JAI-017 performs no LLM calls and defines no provider, prompt, token budget, retry, or cost behavior; those belong to JAI-018.
- JAI-017 keeps records separate by parser block/table row. It does not merge body and attachment results or resolve cross-source conflicts.
- JAI-017 does not persist `job_posts`, `job_positions`, or database `field_evidence`; those operations belong to JAI-019.
- OCR remains deferred to JAI-B01. Partial text already returned with `ocr_required` may be examined, but no missing field is inferred.
