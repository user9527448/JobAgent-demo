# JOBAGENT core database model

> 简体中文：[JOBAGENT 核心数据库模型](zh-CN/DATABASE.md)

This document describes the PostgreSQL schema established in JAI-006 and extended by the JAI-009 [raw-document version policy](RAW_DOCUMENTS.md), JAI-010 [attachment storage policy](ATTACHMENTS.md), JAI-019 [versioned extraction/evidence policy](MERGING_AND_EVIDENCE.md), JAI-020 [validation/reparse policy](VALIDATION_AND_REPARSING.md), JAI-022 [single-user preference policy](PREFERENCES.md), JAI-023 [versioned matching policy](MATCHING.md), JAI-024 [daily report snapshots](REPORTS.md), and JAI-026 [durable scheduling](SCHEDULING.md). JAI-007 adds the crawl-run repository and collection orchestration described in [COLLECTION.md](COLLECTION.md).

## Tables

| Table | Purpose | Important fields and constraints |
|---|---|---|
| `sources` | Public recruitment source configuration | Unique `name`; positive `crawl_interval_minutes`; disable with `enabled=false` |
| `crawl_runs` | One source execution | Restricted status values; `finished_at` cannot precede `started_at`; JSONB statistics |
| `raw_documents` | Immutable source announcement version | Unique `(source_id, canonical_url, version)`; one current version per source URL; SHA-256 content hash; optional ETag/Last-Modified; HTML or text must be present |
| `attachments` | Files discovered from an announcement | Unique `(document_id, url)`; validated download status and metadata; separate parse status |
| `job_posts` | Versioned announcement-level structured result | Unique document/extraction version; one current version; version/supersedes/hash chain; deadline order; review status and recommendation eligibility |
| `job_positions` | Optional position records below one post version | Stable record key; evidenced name may be absent; positive headcount when known |
| `field_evidence` | Field-level traceability | Raw/normalized values, method/version, selection/conflict, exactly one source, quote/page/line/sheet/cell locator, confidence from 0 to 1 |
| `validation_issues` | Version-specific quality findings | Stable issue key per post; reason, severity, entity/field identity; errors and warnings only |
| `user_preferences` | Singleton local-user profile | Fixed `id=1`; structured filters; unrestricted defaults; audit timestamps and sticky recomputation signal |
| `match_results` | Versioned position matching decision | Score/rule version; input/preference/result hashes; hard-filter decision; JSONB components/rules; one current result plus append-only history |
| `daily_report_snapshots` | Immutable structured/rendered daily report | Date/timezone/version/input identity; JSONB payload; content hash; Markdown and escaped HTML; identical inputs reuse one snapshot |
| `apscheduler_jobs` | APScheduler 3 persistent job store | Fixed string job ID; next-run timestamp index; serialized scheduler state; managed only by the single scheduler process |
| `pipeline_runs` | One durable logical daily execution | Unique `(job_name, scheduled_for)`; trigger, local report date/timezone, current stage, terminal status, timestamps, and safe error metadata |
| `pipeline_stage_runs` | Numbered attempts for each pipeline stage | Unique run/stage/attempt; constrained stage/status; JSONB artifact IDs, versions, counts, and safe failure output |

## Relationships and deletion policy

```text
sources
├── crawl_runs
└── raw_documents
    ├── supersedes → prior raw_documents version
    ├── attachments
    │   └── field_evidence (attachment source)
    ├── job_posts
    │   ├── job_positions
    │   │   └── match_results → user_preferences
    │   └── validation_issues
    └── field_evidence (document source)

daily_report_snapshots (immutable report payload and renderings)

pipeline_runs
└── pipeline_stage_runs (restricted, append-only numbered attempts)

apscheduler_jobs (single APScheduler process job store)
```

All historical foreign keys use `ON DELETE RESTRICT`, and ORM relationships do not use delete cascades. A source with history cannot be accidentally removed. Normal source retirement changes `sources.enabled` to false, preserving runs, documents, attachments and extracted data.

`field_evidence.entity_type/entity_id` is intentionally a validated polymorphic reference to either `job_posts` or `job_positions`. The extraction repository validates that entity target while the database maintains a real foreign key to the source document or attachment that supplied the evidence. New extraction versions append post/position/evidence rows; old versions remain deletion-resistant.

`validation_issues.post_id` is a real restricted foreign key to the exact `job_posts` extraction version that was validated. A new rule/extraction version appends a new post and new findings instead of mutating the historical decision.

`match_results.position_id` and `preference_id` are restricted foreign keys to the exact position and singleton preference profile. New preference snapshots or score versions append results and move the one-current-result marker; `supersedes_id` retains the prior decision.

## Time handling

- PostgreSQL columns use `TIMESTAMP WITH TIME ZONE`.
- `UTCDateTime` rejects timezone-naive Python values.
- Aware values are normalized to UTC before binding and after reading.
- Database defaults use PostgreSQL's current instant; PostgreSQL stores `timestamptz` as an absolute instant.
- Display and scheduling conversion to `Asia/Shanghai` belongs at the application boundary, not in stored values.

## Constraints and indexes

- SHA-256 values are lowercase 64-character hexadecimal strings.
- Raw-document versions are positive and form a deletion-resistant self-referencing chain; a partial unique index permits only one `is_current=true` row per source/canonical URL.
- A stored attachment requires MIME type, SHA-256, relative local path, non-negative byte size and download timestamp; the repository clears that success metadata when recording a failed download.
- Attachment `download_status` (`pending`/`stored`/`failed`) remains independent of the later `parse_status` pipeline.
- Status and evidence type fields have explicit check constraints rather than unconstrained free text.
- Common source/date, status, deadline, location/education and evidence lookup paths are indexed.
- Incomplete structured fields remain nullable so raw evidence is retained and can enter later review workflows.
- A document/extraction-version pair is idempotent by result hash. A partial unique index allows only one current post per document, while `supersedes_id` preserves the complete post-version chain.
- Field evidence stores original and normalized values together and retains conflicting candidates instead of overwriting them. Line and worksheet/cell coordinates complement existing page/quote locators.
- `review_status` is limited to `approved`, `review_required`, or `blocked`; `validation_issues.severity` is limited to `warning` or `error`. Any error sets `recommendation_eligible=false` in the same extraction transaction.
- The current/eligibility index supports later recommendation queries without treating legacy or blocked rows as eligible. Legacy rows are backfilled as `review_required` and `legacy-unvalidated`, never silently approved.
- `user_preferences` permits only `id=1`; JSON preference fields must remain arrays and `education` must be a supported deterministic enum or null. Empty values are unrestricted, never “match nothing.”
- `match_results` constrains scores to 0–100, requires zero after any failed hard filter, validates all SHA-256 identities, and requires JSON arrays for component/rule explanations. One partial unique index permits one current result per position.
- `daily_report_snapshots` requires a JSON object payload and valid input/content SHA-256 values. Its date/timezone/report-version/input-hash identity prevents duplicate snapshots while retaining changed same-day inputs as separate immutable rows.
- `pipeline_runs` uses the UTC schedule instant as part of its logical identity while retaining the resolved local report date and timezone. Scheduled and makeup triggers for the same slot therefore cannot create duplicate runs.
- `pipeline_stage_runs` permits only collection, extraction, matching, and report stages. Running attempts become `interrupted` on recovery; completed attempts and their JSON artifact references are retained.
- `apscheduler_jobs` is shared by no more than one scheduler process. The domain advisory lock remains the cross-process authority and prevents a competing process from writing a duplicate run.

## Migrations

Alembic reads `JOBAGENT_DATABASE_URL` through normal settings; `alembic.ini` contains no credential.

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

Inside Compose:

```powershell
docker compose exec api alembic upgrade head
```

Migration integration tests are destructive and therefore refuse any database whose name does not end in `_test`.
Migration `0009_pipeline_scheduling` is covered by that guard. Applying it to a populated business database and starting the Compose scheduler are separate runtime operations requiring explicit approval.
