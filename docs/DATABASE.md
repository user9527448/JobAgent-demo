# JOBAGENT core database model

This document describes the JAI-006 PostgreSQL schema. JAI-007 adds the crawl-run repository and collection orchestration described in [COLLECTION.md](COLLECTION.md); raw-document persistence begins in JAI-009.

## Tables

| Table | Purpose | Important fields and constraints |
|---|---|---|
| `sources` | Public recruitment source configuration | Unique `name`; positive `crawl_interval_minutes`; disable with `enabled=false` |
| `crawl_runs` | One source execution | Restricted status values; `finished_at` cannot precede `started_at`; JSONB statistics |
| `raw_documents` | Immutable source announcement | Unique `(source_id, canonical_url)`; SHA-256 content hash; HTML or text must be present |
| `attachments` | Files discovered from an announcement | Unique `(document_id, url)`; SHA-256 and parse-status validation |
| `job_posts` | Announcement-level structured result | At most one current post per document; deadline cannot precede start |
| `job_positions` | Optional position rows below a post | Positive headcount when known; a post may have zero positions |
| `field_evidence` | Field-level traceability | Points to exactly one document or attachment; quote/page/cell locator required; confidence from 0 to 1 |

## Relationships and deletion policy

```text
sources
├── crawl_runs
└── raw_documents
    ├── attachments
    │   └── field_evidence (attachment source)
    ├── job_posts
    │   └── job_positions
    └── field_evidence (document source)
```

All historical foreign keys use `ON DELETE RESTRICT`, and ORM relationships do not use delete cascades. A source with history cannot be accidentally removed. Normal source retirement changes `sources.enabled` to false, preserving runs, documents, attachments and extracted data.

`field_evidence.entity_type/entity_id` is intentionally a validated polymorphic reference to either `job_posts` or `job_positions`. The database also maintains a real foreign key to the source document or attachment that supplied the evidence.

## Time handling

- PostgreSQL columns use `TIMESTAMP WITH TIME ZONE`.
- `UTCDateTime` rejects timezone-naive Python values.
- Aware values are normalized to UTC before binding and after reading.
- Database defaults use PostgreSQL's current instant; PostgreSQL stores `timestamptz` as an absolute instant.
- Display and scheduling conversion to `Asia/Shanghai` belongs at the application boundary, not in stored values.

## Constraints and indexes

- SHA-256 values are lowercase 64-character hexadecimal strings.
- Status and evidence type fields have explicit check constraints rather than unconstrained free text.
- Common source/date, status, deadline, location/education and evidence lookup paths are indexed.
- Incomplete structured fields remain nullable so raw evidence is retained and can enter later review workflows.

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
