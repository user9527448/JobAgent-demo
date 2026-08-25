# Extraction Merging and Field Evidence

> Simplified Chinese mirror: [`zh-CN/MERGING_AND_EVIDENCE.md`](zh-CN/MERGING_AND_EVIDENCE.md).

JAI-019 turns isolated deterministic and validated LLM candidates into versioned `job_posts`, optional partial `job_positions`, and durable `field_evidence`. The merge is deterministic, retains contradictions, and never mutates a prior extraction version.

## Inputs and entity boundaries

`ExtractionMergeInput` identifies one immutable `raw_documents` row and one explicit merge `extraction_version`. It accepts any number of `ExtractionResult` objects plus `LlmMergeContribution` objects that bind a validated `LlmExtractionPayload` back to the exact parser fragments sent to the provider.

Document parser sources must use the same database ID as `document_id`. Attachment source IDs are validated by the persistence repository to ensure every attachment belongs to that document. Mixed or missing source identities are rejected before a business write.

Announcement fields are `start_at`, `deadline`, `region`, `organization`, `apply_url`, and `category`. A parser record containing `headcount` or `education` can materialize one partial position with `region`, `headcount`, and `education`. Position `name` is nullable because JAI-017 did not produce an evidenced position-name field; JAI-019 never invents a placeholder. Body and attachment position rows remain separate when no evidenced identity can prove they describe the same position.

## Precedence and conflicts

Precedence is stable and field-target specific:

1. deterministic candidates always precede LLM candidates;
2. announcement fields prefer document/body evidence before attachment evidence;
3. position fields prefer attachment evidence before document/body evidence;
4. remaining ties sort by source ID, exact location, raw value, and normalized value.

Exact duplicate candidates collapse without losing distinct evidence. The first candidate under this order becomes the selected business value. Every different normalized value remains a `MergedEvidence` row; losing contradictory candidates set `conflict=true`, while `MergedField.has_conflict` exposes the field-level condition. Conflicts are therefore queryable and are never silently overwritten.

Deterministic evidence uses confidence `1.0000`. Validated LLM evidence uses policy confidence `0.6000`; this value describes the extraction method and is not model self-assessment. LLM values receive field-specific semantic checks before merging: dates must be timezone-aware ISO values, headcount a positive integer, regions non-empty text/list values, and text fields non-empty strings. Unsupported LLM semantics are omitted instead of coerced.

## Versioned persistence and idempotency

`SqlAlchemyExtractionRepository.save()` takes a PostgreSQL advisory lock per document and writes one atomic extraction version. `job_posts` now has:

- unique `(document_id, extraction_version)`;
- a positive per-document `version`;
- one partial-unique `is_current=true` row per document;
- `supersedes_id` linking the prior post version;
- a SHA-256 `result_hash` over stable values, positions, evidence, conflicts, and coordinates.

Repeating the same `extraction_version` and result hash returns `unchanged` with the original post/position IDs. If the same version produces a different hash, persistence rejects it as `extraction.version_not_deterministic`; callers must fix nondeterminism or use a new explicit version. A new version marks the prior post non-current and appends a new post, positions, and evidence. Historical rows are retained under `ON DELETE RESTRICT` relationships.

Migration `0004_versioned_field_evidence` backfills pre-JAI-019 structured rows as `legacy-v1`, version 1, current, with stable legacy position keys and evidence metadata. Empty-schema upgrade/check/downgrade and an upgrade containing legacy rows are both covered by PostgreSQL tests.

## Evidence schema

Every persisted evidence row stores:

- target `entity_type`, `entity_id`, and `field_name`;
- exactly one source document or attachment ID and matching `source_type`;
- `raw_value` and JSONB `normalized_value` together;
- `extraction_method`, producer `extraction_version`, confidence, selection, and conflict flags;
- exact quote plus page, inclusive line range, or worksheet/cell range coordinates.

Selected and conflicting evidence survive re-extraction because each business entity version has its own IDs and evidence rows. The repository also rejects attachment evidence that belongs to a different raw document. Region tuples are stored as ordered JSON arrays in evidence and comma-separated stable codes in current business columns; UTC datetimes use ISO `Z` strings in evidence and timezone-aware columns in `job_posts`.

## Issue boundaries

- JAI-019 materializes values and exposes conflicts but does not assign review severity, block recommendation eligibility, or implement correction workflows; those belong to JAI-020.
- No reparse command/API is added. Idempotent version persistence is the lower-level primitive JAI-020 may call later.
- Position rows are not guessed across sources when no evidenced position identity exists. Adding a position-name extractor requires a separately scoped extraction change.
- LLM provider calls, budgets, and Prompt behavior remain JAI-018; OCR remains JAI-B01.
