# Daily report queries, rendering, and snapshots

> Simplified Chinese: [日报查询、渲染与快照](zh-CN/REPORTS.md)

## Report input and output

JAI-024 reads only current `match_results` attached to current `job_posts`. A report date and the configured IANA timezone are explicit inputs; the builder never reads the process clock. Every JSON item contains `organization`, `title`, `region`, `deadline`, `reason`, `risks`, and the immutable original `source_url`. Missing evidenced fields remain null and render as `未提供 (需确认)` rather than being guessed.

All four sections are always present. The same position may appear in more than one section because “apply first,” “closing soon,” and “added today” are independent actions.

## Four deterministic groups

| Group | Inclusion rule |
|---|---|
| `priority_applications` | Current hard filters pass and the JAI-023 score is at least 70 |
| `closing_soon` | Current hard filters pass and the evidenced deadline falls from local day start through, but not including, local day start plus seven calendar days |
| `added_today` | Current hard filters pass and the source document's first `fetched_at` falls on the local report date |
| `needs_confirmation` | The extraction review status is not `approved`, or one of organization/title/region/deadline/source URL lacks evidence |

An empty source set produces the four headings with explicit `本组暂无岗位。` messages. Hard-filtered positions are not presented as actionable unless their validation state or evidence gap separately requires confirmation.

## Stable ordering and risks

`jai-024-v1` hashes canonical JSON containing the report date, timezone, report version, and every candidate field that can affect grouping, ordering, reasons, or risks. Candidate input order is normalized by position ID before hashing and grouping.

- Priority applications sort by score descending, then deadline, normalized organization/title, and position ID.
- Closing-soon items sort by deadline, then score descending and stable text/ID ties.
- Added-today items sort by first-fetch instant descending, then score and stable text/ID ties.
- Needs-confirmation items sort by risk count descending, then score, deadline, and position ID.

Risks come only from persisted validation reasons, non-approved review state, evidenced missing fields, failed hard-filter explanations where applicable, and an evidenced deadline within 72 hours. A clean item says that no validation or evidence risk is recorded.

## Markdown and HTML rendering

`render_markdown()` and `render_html()` consume the immutable report contract. Markdown escapes source-controlled formatting characters and emits the original URL as an autolink. HTML escapes all source-controlled text and URL attributes and adds `rel="noopener noreferrer"`. Both renderers retain all fields, reasons, risks, and explicit empty sections.

No template executes source HTML or JavaScript. The report does not copy raw source bodies, attachment paths, credentials, or provider payloads.

## Persistence and API

Migration `0008_daily_report_snapshots` adds `daily_report_snapshots`. The unique identity is `(report_date, timezone, report_version, input_hash)`; identical generation reuses the existing row after verifying the content hash and exact renderings. The JSON payload, SHA-256 content hash, Markdown, HTML, and audit timestamp are immutable snapshot evidence.

```http
POST /reports/daily
Content-Type: application/json

{"report_date":"2026-09-03"}
```

The response returns `snapshot_id`, `content_hash`, structured `report`, `markdown`, `html`, and `created_at`. Existing snapshots are read without recomputation:

```http
GET /reports/daily/{snapshot_id}
GET /reports/daily/{snapshot_id}/markdown
GET /reports/daily/{snapshot_id}/html
```

Unknown positive IDs return `reports.snapshot_not_found`; unavailable persistence returns `reports.database_unavailable`. A non-deterministic repeat is rejected as `reports.version_not_deterministic` rather than overwriting history.

## Scope boundary

JAI-024 does not tune ranking quality, schedule report generation, send notifications, manage channels/tokens, or implement LLM/embedding ranking. JAI-025 owns human Top-20 review, JAI-026 owns scheduling and recovery, and JAI-027 owns one idempotent notification channel.
