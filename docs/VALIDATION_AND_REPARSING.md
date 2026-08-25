# Validation, review, and reparsing

> 简体中文：[数据校验、待复核与重解析](zh-CN/VALIDATION_AND_REPARSING.md)

JAI-020 adds a deterministic quality-control boundary after JAI-019 merging. Validation findings are persisted with each extraction version, severe errors prevent automatic recommendation eligibility, and one stored document can be reparsed explicitly after extraction or validation rules change.

## Validation rules

`ExtractionValidator` emits stable codes, severities, entity keys, optional field names, safe reasons, and deterministic issue keys. It never invents a missing value.

- Missing `organization`, `deadline`, `apply_url`, all positions, or position `education` is an `error`.
- Missing announcement `region`/`category` or position `headcount`/`region` is a `warning`.
- An inverted date range, invalid absolute HTTP(S) application URL, or unsupported normalized region/category/education enum is an `error`.
- Conflicts on `organization`, `deadline`, `apply_url`, or position `education` are errors. Other evidenced conflicts are warnings.

Reasons never include credentials, attachment paths, provider bodies, or raw personal data. Original field values and locations remain in `field_evidence`, not duplicated into validation messages.

## Review and recommendation eligibility

Every `job_posts` version stores `review_status`, `recommendation_eligible`, `validation_version`, and `validated_at`.

| Findings | `review_status` | `recommendation_eligible` |
|---|---|---|
| None | `approved` | `true` |
| Warnings only | `review_required` | `true` |
| One or more errors | `blocked` | `false` |

Every finding is appended to `validation_issues` with its reason and severity. Historical post versions and their findings remain queryable. Rows that predate JAI-020 are backfilled as `review_required`, ineligible, and `legacy-unvalidated`; migration does not pretend that legacy data has passed current rules.

## Stored-document reparse pipeline

`StoredDocumentReparsePipeline` reloads one immutable `raw_documents` row. It uses `raw_text` when present, otherwise converts stored HTML to text, and reparses every referenced attachment from the configured content-addressed storage root. Attachment paths must stay below that root, and persisted size/SHA-256 values must match before parsing.

An attachment that is not stored, fails integrity validation, is unsupported, or does not produce a parsed intermediate result fails the reparse explicitly. The default pipeline runs deterministic extraction and JAI-019 merging only; it makes no live source request and no LLM call.

## Command and API

The manual command requires a positive document ID and an explicit extraction/rule version:

```powershell
.\.venv\Scripts\python.exe scripts/manage_extraction.py reparse --document-id 19 --extraction-version rules-2026.08.25
```

The API uses the same service:

```http
POST /extraction/documents/19/reparse
Content-Type: application/json

{"extraction_version":"rules-2026.08.25"}
```

Both responses include the write outcome, post/position IDs, entity version, result hash, review status, recommendation eligibility, validation version, and error/warning counts. Safe permanent failures return `404` or `422`; temporary database/storage failures return `503`.

## Idempotency and version changes

The extraction version must use 1–100 letters, digits, dots, underscores, colons, or hyphens. Repeating the same document/version with the same result hash returns `unchanged` and reuses the existing entities and findings. Producing different output under an existing version is rejected as `extraction.version_not_deterministic`.

After a rule correction, use a new explicit extraction version. The repository appends a new current post/position/evidence/validation version, marks the prior post non-current, and preserves the `supersedes_id` chain.

## Issue boundaries

- JAI-020 does not add source 4/5 integration or multi-day stability runs; those remain JAI-021.
- It does not add preferences, matching, scores, reports, scheduling, OCR, or broad maintenance APIs.
- It does not add manual value-editing or approval endpoints. A blocked record becomes eligible only after corrected evidence/rules produce a valid new version.
- It never bypasses login, CAPTCHA, access controls, anti-bot measures, or platform restrictions.
