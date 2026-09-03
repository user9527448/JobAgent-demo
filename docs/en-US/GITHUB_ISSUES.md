# JOBAGENT V1.0 — GitHub Issues Backlog

> Simplified Chinese source: [`../GITHUB_ISSUES.md`](../GITHUB_ISSUES.md).

This document turns the ten-week plan into executable Issues. These are planning identifiers and do not equal GitHub's automatically assigned Issue numbers.

## 1. Suggested labels

### Type

`type:feature`, `type:chore`, `type:test`, `type:docs`, `type:spike`, `type:bug`

### Area

`area:infra`, `area:database`, `area:crawler`, `area:parser`, `area:extraction`, `area:matching`, `area:report`, `area:notification`, `area:api`, `area:ui`, `area:agent`

### Priority and size

`priority:P0`, `priority:P1`, `priority:P2`; `size:S` (≤0.5 day), `size:M` (1–2 days), `size:L` (3–4 days). Split any Issue larger than L.

## 2. Milestones and week mapping

| Milestone | Week | Issues |
|---|---|---|
| M1 Foundation | W1 | JAI-001–JAI-005 |
| M2 Collection | W2–W3 | JAI-006–JAI-012 |
| M3 Extraction | W4–W6 | JAI-013–JAI-021 |
| M4 Intelligence | W7 | JAI-022–JAI-025 |
| M5 MVP Release | W8 | JAI-026–JAI-029 |
| M6 Agent | W9–W10 | JAI-030–JAI-035 |
| Cross-cutting documentation | Ongoing | JAI-036, JAI-046–JAI-048 |

---

## M1 Foundation (week 1)

### JAI-001 Initialize the Python project and development conventions

- **Labels**: `type:chore` `area:infra` `priority:P0` `size:M`
- **Dependencies**: none
- **Goal**: establish an installable, testable monolith that can evolve safely.
- **Scope**: `pyproject.toml`, application/test directories, formatting/static-check configuration, `.gitignore`, `.env.example`, and a baseline README.
- **Non-goals**: business models, frontend, Agent.
- **Acceptance**:
  - [ ] A new environment installs dependencies and starts the empty application from the README.
  - [ ] Formatting, static checks, and tests run locally.
  - [ ] No secrets, caches, database files, or downloaded attachments are committed.

### JAI-002 Add configuration, structured logging, and unified exceptions

- **Labels**: `type:feature` `area:infra` `priority:P0` `size:M`
- **Dependencies**: JAI-001
- **Goal**: use consistent configuration, log fields, and error classes across all modules.
- **Scope**: environment settings, timezone, log level, request/run/source context, retryable and permanent errors.
- **Acceptance**:
  - [ ] Missing required configuration fails startup with a clear message.
  - [ ] Logs include time, level, event, and correlation IDs.
  - [ ] Common secret fields are automatically redacted.

### JAI-003 Add FastAPI, PostgreSQL, and health checks

- **Labels**: `type:feature` `area:infra` `area:api` `priority:P0` `size:M`
- **Dependencies**: JAI-001, JAI-002
- **Goal**: start the API and database with Docker Compose.
- **Scope**: Compose, database pool, `/health/live`, `/health/ready`.
- **Acceptance**:
  - [ ] One command starts the services.
  - [ ] Liveness does not depend on the database; readiness verifies it.
  - [ ] Database failure makes readiness return a non-success status and produces a diagnostic log.

### JAI-004 Establish testing and CI

- **Labels**: `type:test` `area:infra` `priority:P0` `size:M`
- **Dependencies**: JAI-001, JAI-003
- **Goal**: run quality checks for every change.
- **Scope**: pytest, test-database strategy, lint/type/test workflow.
- **Acceptance**:
  - [ ] Local development and CI invoke the same gate.
  - [ ] Tests are isolated and repeatable.
  - [ ] A deliberate failing test blocks the gate.

### JAI-005 Complete the first real-source vertical Spike

- **Labels**: `type:spike` `area:crawler` `area:parser` `priority:P0` `size:L`
- **Dependencies**: JAI-003
- **Goal**: prove announcement HTML, attachment download, and PDF text extraction with a real public source.
- **Scope**: select one static source; record entry point, structure, and rate limits; preserve one list page, detail page, and PDF sample.
- **Deliverables**: technical findings, fixtures, known limitations, and integration recommendation.
- **Acceptance**:
  - [ ] Discover a detail link and extract title, publication time, and body.
  - [ ] Discover/download one PDF and extract page-level text.
  - [ ] Record access policy and compliance findings.

---

## M2 Collection (weeks 2–3)

### JAI-006 Implement core models and the first migration

- **Labels**: `type:feature` `area:database` `priority:P0` `size:L`
- **Dependencies**: JAI-003
- **Goal**: persist sources, runs, raw documents, attachments, and structured jobs.
- **Scope**: `sources`, `crawl_runs`, `raw_documents`, `attachments`, `job_posts`, `job_positions`, `field_evidence`, indexes, and constraints.
- **Acceptance**:
  - [ ] Upgrade an empty database to head.
  - [ ] A uniqueness constraint blocks duplicate canonical URLs within one source.
  - [ ] Times persist in UTC and disabling a source does not delete history.
  - [ ] Models, relations, and fields are documented.

### JAI-007 Implement Source Adapter protocol and collection orchestrator

- **Labels**: `type:feature` `area:crawler` `priority:P0` `size:L`
- **Dependencies**: JAI-002, JAI-006
- **Goal**: new sources implement discovery/detail parsing without duplicating the common flow.
- **Scope**: Adapter registry, discover/fetch protocol, batching, step state, item-error isolation.
- **Acceptance**:
  - [ ] A fake Adapter completes and emits persisted statistics.
  - [ ] One detail failure does not stop later items.
  - [ ] Unknown Adapters fail clearly before a run starts.

### JAI-008 Implement HTTP policy, rate limits, retries, and cache validators

- **Labels**: `type:feature` `area:crawler` `priority:P0` `size:M`
- **Dependencies**: JAI-002
- **Goal**: access sources politely, predictably, and observably.
- **Scope**: timeouts, per-source concurrency/rate, exponential backoff, User-Agent, ETag/Last-Modified.
- **Acceptance**:
  - [ ] 429/5xx responses retry according to policy and record attempts.
  - [ ] Permanent 4xx responses do not retry forever.
  - [ ] Every source configures limits and timeouts independently.

### JAI-009 Implement URL canonicalization, fingerprints, and idempotent persistence

- **Labels**: `type:feature` `area:crawler` `area:database` `priority:P0` `size:M`
- **Dependencies**: JAI-006, JAI-007
- **Goal**: prevent duplicates while retaining page updates.
- **Scope**: tracking-parameter removal, relative links, canonical URLs, body normalization, SHA-256, update policy.
- **Acceptance**:
  - [ ] Repeating identical input retains one current announcement.
  - [ ] Content changes create a version/update event without losing evidence.
  - [ ] Unit tests cover critical URL/content boundaries.

### JAI-010 Implement attachment discovery, download, and storage

- **Labels**: `type:feature` `area:crawler` `priority:P0` `size:M`
- **Dependencies**: JAI-006, JAI-008, JAI-009
- **Goal**: preserve announcement attachments reliably without duplicate downloads.
- **Scope**: PDF/XLS/XLSX discovery, MIME/extension validation, size limits, SHA-256, atomic writes.
- **Acceptance**:
  - [ ] Repeated discovery reuses the same attachment.
  - [ ] HTML error pages disguised as attachments are rejected and recorded.
  - [ ] Interrupted downloads never leave a half-file marked successful.

### JAI-011 Integrate sources 1–3 and add contract fixtures

- **Labels**: `type:feature` `area:crawler` `priority:P0` `size:L`
- **Dependencies**: JAI-005, JAI-007–JAI-010
- **Goal**: use a maintainable official-source catalog to cover three representative public page structures.
- **Scope**: catalog campus, Jiangsu/Zhejiang/Shanghai public-exam, and central/state-owned enterprise sources; keep per-source status and include/exclude terms; make each source a separate subtask/commit; use SASAC first; keep application systems and unverified dynamic portals disabled.
- **Acceptance**:
  - [x] `config/source_catalog.toml` supports manual add/remove/toggle/keywords and rejects invalid/duplicate entries.
  - [x] The catalog covers campus, Jiangsu/Zhejiang/Shanghai public examinations, and central/state-owned recruitment with official entry points and status.
  - [x] Every source discovers and persists new announcements; supported JAI-010 attachments persist/reuse; Firstjob poster images retain source URLs only.
  - [x] Every source has at least three passing fixture groups.
  - [x] Two consecutive runs create no duplicates.

### JAI-012 Add run statistics, manual triggers, and failed-item reruns

- **Labels**: `type:feature` `area:crawler` `area:api` `priority:P1` `size:M`
- **Dependencies**: JAI-007, JAI-011
- **Goal**: explain what happened in one run and rerun failures only.
- **Scope**: command/API, run state, discovered/created/updated/skipped/failed counts, error classes.
- **Acceptance**:
  - [x] Start a source manually and receive a run ID.
  - [x] Read run summary and failed items.
  - [x] Reruns do not duplicate successful data.

---

## M3 Extraction (weeks 4–6)

### JAI-013 Define parser protocol and standard intermediate format

- **Labels**: `type:feature` `area:parser` `priority:P0` `size:M`
- **Dependencies**: JAI-006, JAI-010
- **Goal**: give HTML, PDF, and Excel a common traceable output.
- **Scope**: parser registry, block/table/evidence Schemas, states, error codes.
- **Acceptance**:
  - [x] Select parsers by MIME type.
  - [x] Every block retains source file and page/row/cell position.
  - [x] Unsupported files enter an explicit state.

### JAI-014 Implement PDF text parsing and scan detection

- **Labels**: `type:feature` `area:parser` `priority:P0` `size:M`
- **Dependencies**: JAI-013
- **Goal**: parse text PDFs and identify files that cannot be parsed directly.
- **Scope**: page text, metadata, encrypted/corrupt errors, text density; no V1 OCR.
- **Acceptance**:
  - [x] Normal PDFs emit page text and page numbers.
  - [x] Scans become `ocr_required`.
  - [x] Encrypted/corrupt files return diagnostic errors.

### JAI-015 Implement Excel position-table parsing

- **Labels**: `type:feature` `area:parser` `priority:P0` `size:L`
- **Dependencies**: JAI-013
- **Goal**: convert common position sheets into evidence-preserving tables.
- **Scope**: multiple sheets, header detection, blank rows, merged cells, XLSX; decide XLS support from feasible dependencies.
- **Acceptance**:
  - [x] Header/data-region accuracy reaches the agreed golden-sample target.
  - [x] Every field points to sheet and cell/row.
  - [x] Unrecognized headers enter review state.

### JAI-016 Establish attachment golden samples and regression tests

- **Labels**: `type:test` `area:parser` `priority:P0` `size:M`
- **Dependencies**: JAI-014, JAI-015
- **Goal**: prevent parser changes from breaking known formats.
- **Scope**: at least ten sanitized PDF/Excel samples, expected intermediate output, batch evaluator.
- **Acceptance**:
  - [x] Samples cover multiple pages, merged cells, blank rows, and date formats.
  - [x] CI runs the full regression offline.
  - [x] Report parsing success and differences.

### JAI-017 Implement deterministic field extraction and normalization

- **Labels**: `type:feature` `area:extraction` `priority:P0` `size:L`
- **Dependencies**: JAI-013
- **Goal**: reliably extract dates, regions, organizations, application links, and related fields with rules.
- **Scope**: date ranges/timezones, region dictionary, URLs, headcount, education, enums.
- **Acceptance**:
  - [x] Date parsing covers golden formats and start never follows deadline.
  - [x] Preserve raw and normalized values.
  - [x] Never guess unsupported critical fields.

### JAI-018 Implement a replaceable LLM extraction service

- **Labels**: `type:feature` `area:extraction` `priority:P0` `size:L`
- **Dependencies**: JAI-002, JAI-017
- **Goal**: supplement irregular announcements while controlling cost and hallucination.
- **Scope**: provider interface, strict JSON Schema, prompt version, timeout/retry, token/cost metrics, mocks.
- **Acceptance**:
  - [x] Provider is configurable.
  - [x] Invalid output never enters business tables directly.
  - [x] Record model, prompt version, token use, and result status.
  - [x] Stop new calls at daily budget and queue remaining work.

### JAI-019 Merge body/attachment results and preserve field evidence

- **Labels**: `type:feature` `area:extraction` `area:database` `priority:P0` `size:L`
- **Dependencies**: JAI-014, JAI-015, JAI-017, JAI-018
- **Goal**: create announcement/position entities and explain every critical field.
- **Scope**: precedence, conflicts, confidence, extraction version, `field_evidence`.
- **Acceptance**:
  - [x] Critical fields retain source type and evidence location.
  - [x] Body/attachment conflicts are never silently overwritten.
  - [x] Re-extraction preserves history and is deterministic.

### JAI-020 Implement validation, review, and reparsing

- **Labels**: `type:feature` `area:extraction` `priority:P0` `size:M`
- **Dependencies**: JAI-019
- **Goal**: prevent bad data from silently entering recommendations.
- **Scope**: required fields, date/link/enum/conflict validation, review state, reparse command/API.
- **Acceptance**:
  - [x] Validation failures record reason and severity.
  - [x] Severe errors do not enter automatic recommendations.
  - [x] Reparse selected documents idempotently after rule fixes.

### JAI-021 Integrate sources 4–5 and verify three-day stability

- **Labels**: `type:feature` `area:crawler` `area:extraction` `priority:P0` `size:L`
- **Dependencies**: JAI-011, JAI-020
- **Goal**: meet MVP source coverage and quality metrics.
- **Scope**: prefer the National College Student Employment Service Platform and Shanghai public-institution announcements; if dynamic lists violate public-access boundaries, use a stable official endpoint or record a blocker, never login/application systems.
- **Acceptance**:
  - [ ] Five sources have Adapter contract tests.
  - [ ] Record success, duplicate, and completeness metrics for three consecutive days.
  - [ ] Core fields reach 85%, or a corrective Issue documents the gap.

---

## M4 Intelligence (week 7)

### JAI-022 Implement single-user preferences and configuration API

- **Labels**: `type:feature` `area:matching` `area:api` `priority:P0` `size:M`
- **Dependencies**: JAI-006
- **Status**: implementation, paired documentation, and the PostgreSQL-enabled full gate completed on 2026-08-30; dedicated branch `feature/jai-022-single-user-preferences` awaits JAI-021 integration first, then synchronization from updated `develop` before integration.
- **Goal**: store structured filters and preferences.
- **Scope**: region, education, major, keywords, organization type, exclusions, read/update API.
- **Acceptance**:
  - [x] Schema and enum validation protects input.
  - [x] Changes record update time and can trigger recomputation.
  - [x] Defaults do not accidentally filter every job.

### JAI-023 Implement hard filters and versioned rule scoring

- **Labels**: `type:feature` `area:matching` `priority:P0` `size:L`
- **Dependencies**: JAI-020, JAI-022
- **Status**: implementation, migration, paired documentation, and the PostgreSQL-enabled complete gate finished on 2026-08-30. Dedicated branch `feature/jai-023-hard-filter-versioned-scoring` is based on published JAI-022 tip `44ed502` and will synchronize from updated `develop` only after JAI-021 and JAI-022 integrate in the recorded order.
- **Goal**: stable, explainable, recomputable ranking.
- **Scope**: education/deadline/exclusion hard filters; region/direction/major/organization/urgency/completeness components.
- **Acceptance**:
  - [x] Identical input/version yields identical output.
  - [x] Persist each component's rule, input, score, and explanation.
  - [x] Preference changes support full recomputation.
  - [x] Unit tests cover boundaries.

### JAI-024 Implement report query and Markdown/HTML rendering

- **Labels**: `type:feature` `area:report` `priority:P0` `size:L`
- **Dependencies**: JAI-023
- **Status**: deterministic grouping, rendering, snapshot migration, API, tests, and paired documentation completed on the dedicated branch on 2026-09-03. Seven focused PostgreSQL tests passed, and the complete gate passed all 252 tests with no skips and 88.53% coverage; commit and normal push remain.
- **Goal**: produce an actionable report suitable for reading and delivery.
- **Scope**: apply-first, closing-soon, added-today, needs-confirmation groups; templates, snapshots, source links.
- **Acceptance**:
  - [x] Each item has organization, title, region, deadline, reason, risk, and links.
  - [x] Identical daily input has stable ordering.
  - [x] Empty input still creates an explicit empty report.

### JAI-025 Review Top 20 quality with historical samples

- **Labels**: `type:test` `area:matching` `priority:P1` `size:M`
- **Dependencies**: JAI-023, JAI-024
- **Goal**: tune weights against human judgment.
- **Scope**: at least 50 human-labeled positions; review Top 20 and misses.
- **Acceptance**:
  - [ ] Classify obvious false positives and misses.
  - [ ] Compare scores before/after changes and bump score version.
  - [ ] Document MVP recommendation limitations.

---

## M5 MVP Release (week 8)

### JAI-026 Implement daily scheduling, locks, and recovery

- **Labels**: `type:feature` `area:infra` `priority:P0` `size:L`
- **Dependencies**: JAI-012, JAI-024
- **Goal**: run the full pipeline unattended every day.
- **Scope**: APScheduler, `Asia/Shanghai`, single-instance locks, misfires, stage retries, manual makeup runs.
- **Acceptance**:
  - [ ] One schedule time cannot run duplicate jobs concurrently.
  - [ ] Restart safely recovers or terminates incomplete work.
  - [ ] Every scheduled run traces collection, parsing, scoring, and report records.

### JAI-027 Integrate WeChat delivery with idempotency and retries

- **Labels**: `type:feature` `area:notification` `priority:P0` `size:M`
- **Dependencies**: JAI-024
- **Goal**: reliably deliver through one selected channel.
- **Scope**: PushPlus or WeCom bot, message length, retries, send records, secret configuration.
- **Acceptance**:
  - [ ] A successful report/channel pair is not sent again.
  - [ ] Temporary failures retry within limits; permanent failures expose a reason.
  - [ ] Tokens never appear in logs or database records.

### JAI-028 Complete end-to-end tests and five unattended trials

- **Labels**: `type:test` `area:infra` `priority:P0` `size:L`
- **Dependencies**: JAI-026, JAI-027
- **Goal**: prove the real scheduled MVP loop is stable.
- **Scope**: offline E2E, controlled live trials, metrics, issue list.
- **Acceptance**:
  - [ ] Offline fixtures complete collection through report generation.
  - [ ] Five consecutive automatic runs succeed without duplicate announcements or notifications.
  - [ ] Record availability, completeness, parsing success, and duration.

### JAI-029 Write the operations guide and release v0.1.0-mvp

- **Labels**: `type:docs` `area:infra` `priority:P0` `size:M`
- **Dependencies**: JAI-028
- **Goal**: remain installable, operable, diagnosable, and recoverable one month later.
- **Scope**: install, config, source addition, reruns, troubleshooting, backup/restore, upgrade/rollback, release checklist.
- **Acceptance**:
  - [ ] A clean environment starts and creates a sample report from the guide.
  - [ ] PostgreSQL backup/restore drill succeeds.
  - [ ] Create `v0.1.0-mvp` tag/Release with known limitations.

---

## M6 Agent (weeks 9–10)

### JAI-030 Implement source, preference, run-history, and failure APIs

- **Labels**: `type:feature` `area:api` `priority:P1` `size:L`
- **Dependencies**: JAI-012, JAI-022, JAI-029
- **Goal**: perform routine maintenance without direct database access.
- **Scope**: source toggles, preferences, runs/details, failed items, reruns, local single-user boundary.
- **Acceptance**:
  - [ ] Validate and audit all writes.
  - [ ] Disabling a source retains history.
  - [ ] Reruns have idempotency protection.

### JAI-031 Implement the minimal configuration/status page

- **Labels**: `type:feature` `area:ui` `priority:P1` `size:L`
- **Dependencies**: JAI-030
- **Goal**: perform frequent maintenance in one simple page.
- **Scope**: source state/toggles, preferences, recent runs, failure details, today's report link.
- **Non-goals**: login, multiple users, generic CRUD admin, complex design system.
- **Acceptance**:
  - [ ] Supported desktop browsers perform all scoped actions.
  - [ ] Dangerous/repeated actions have confirmation or disabled state.
  - [ ] API errors become understandable UI feedback.

### JAI-032 Implement stable job-query and explanation services

- **Labels**: `type:feature` `area:api` `area:matching` `priority:P0` `size:L`
- **Dependencies**: JAI-023, JAI-030
- **Goal**: let Agent and UI share business services instead of direct database access.
- **Scope**: search, detail, score explanation, generate/read report, controlled source collection.
- **Acceptance**:
  - [ ] Inputs/outputs use explicit Schemas.
  - [ ] Search supports region, organization type, keywords, deadline state, and minimum score.
  - [ ] Explanations match persisted score components.

### JAI-033 Wrap Agent Tools and security boundaries

- **Labels**: `type:feature` `area:agent` `priority:P0` `size:L`
- **Dependencies**: JAI-032
- **Goal**: expose a minimal, controlled, auditable tool set.
- **Scope**: `search_jobs`, `get_job_detail`, `explain_match`, `generate_report`, `run_crawl`; parameter Schemas, timeouts, result limits, audit.
- **Acceptance**:
  - [ ] The Agent cannot run arbitrary SQL/code or unregistered tools.
  - [ ] Write/run tools have confirmation and idempotency keys.
  - [ ] Log tool name, parameter summary, result, and duration.

### JAI-034 Implement single-Agent orchestration and evaluation set

- **Labels**: `type:feature` `type:test` `area:agent` `priority:P1` `size:L`
- **Dependencies**: JAI-033
- **Goal**: reliably query, explain, and perform controlled operations from natural language.
- **Scope**: system instructions, tool selection, step limits, failure fallback, at least 30 evaluation tasks.
- **Acceptance**:
  - [ ] Query/explanation tasks never trigger writes.
  - [ ] Ambiguous run requests require confirmation.
  - [ ] Evaluation succeeds at least 90% with classified failures.

### JAI-035 Stabilize and release v0.2.0-agent

- **Labels**: `type:chore` `area:agent` `priority:P1` `size:M`
- **Dependencies**: JAI-031, JAI-034
- **Goal**: finish and document the Agent release.
- **Scope**: regression, performance/cost review, limitations, upgrade guidance, demo script.
- **Acceptance**:
  - [ ] Agent integration does not regress the MVP pipeline.
  - [ ] Critical Agent tasks have reproducible demos.
  - [ ] Release `v0.2.0-agent` with upgrade/rollback notes.

---

## Cross-cutting documentation maintenance

### JAI-036 Establish Simplified Chinese mirrors and synchronization rules

- **Labels**: `type:docs` `area:infra` `priority:P1` `size:M`
- **Dependencies**: JAI-010 (use the completed version as the documentation baseline)
- **Goal**: make English technical documents navigable in Simplified Chinese and keep future changes synchronized.
- **Scope**: `docs/zh-CN/` index/mirrors, synchronization conventions, README navigation, translation of current English technical documentation; existing Chinese documents remain single files under the original policy.
- **Non-goals**: line-by-line historical WORKLOG translation, translating code identifiers/third-party source material, machine-translation services.
- **Acceptance**:
  - [ ] Every current English technical document has a clear Chinese mirror/entry.
  - [ ] Chinese index is reachable from root README and points back to English sources.
  - [ ] `AGENTS.md` requires same-commit updates to English documents and Chinese mirrors.
  - [ ] New WORKLOG entries use Chinese from this Issue; old history stays unchanged.

### JAI-046 Strengthen separate bilingual files and Git authorship rules

- **Labels**: `type:docs` `area:infra` `priority:P0` `size:S`
- **Dependencies**: JAI-036, JAI-037
- **Goal**: replace the old “Chinese documents stay single-source” convention with explicit bilingual files, migration triggers, and trustworthy Git authorship.
- **Scope**: update root `AGENTS.md` and `docs/zh-CN/AGENTS.md` together; define language preservation, counterpart paths, same-commit synchronization, WORKLOG history protection, and repository-local author configuration.
- **Non-goals**: migrate all legacy documents, translate historical logs, rewrite existing authors, or change application code.
- **Acceptance**:
  - [x] English/Chinese repository instructions share sections and constraints.
  - [x] Explicitly prohibit overwriting one language with another and placeholder Git identities.
  - [x] Define future migration and mixed-WORKLOG preservation requirements.
  - [x] Normally push the branch and non-fast-forward merge it into `develop`, with local/tracking/GitHub commits matching.

### JAI-047 Establish the legacy bilingual-document migration baseline

- **Labels**: `type:docs` `area:infra` `priority:P0` `size:M`
- **Dependencies**: JAI-046
- **Goal**: make JAI-046 executable and resumable, with a bounded follow-up for remaining legacy files.
- **Scope**: English mirrors for the substantively changed development plan and Issue backlog; byte-identical archive of the mixed WORKLOG plus separate active English/Chinese logs; bilingual indexes; JAI-048 inventory/registration.
- **Non-goals**: translate the historical archive, migrate every other single-language document, change application code, or implement later product work.
- **Acceptance**:
  - [x] `DEVELOPMENT_PLAN.md`, `GITHUB_ISSUES.md`, and the active WORKLOG have separate English/Simplified Chinese files with reciprocal links.
  - [x] The archived WORKLOG SHA-256 equals the pre-migration file; no history is deleted or rewritten.
  - [x] Both indexes distinguish paired documents, the archive, and the JAI-048 legacy inventory.
  - [x] Relative links, bilingual heading parity, `git diff --check`, and the full quality gate pass.

### JAI-048 Migrate remaining legacy single-language documents

- **Labels**: `type:docs` `area:infra` `priority:P1` `size:L`
- **Dependencies**: JAI-047
- **Goal**: add independent language versions for remaining repository-authored documents and clear the legacy inventory.
- **Scope**: root README, configuration guide, source catalog, unofficial reference sources, and fixture READMEs added after JAI-011; retain each original language and add the missing mirror; update both indexes.
- **Non-goals**: third-party materials, fixture bodies, historical WORKLOG archive, product functionality, or automatic machine-translation services.
- **Acceptance**:
  - [ ] Every repository-authored Markdown document has a bilingual pair or an indexed, verifiable non-translation reason.
  - [ ] Sections, constraints, commands, and links remain semantically aligned; code/API identifiers remain unchanged.
  - [ ] Root navigation, both indexes, relative links, and the full quality gate pass.

---

## M7 Source Expansion (post-MVP source track)

### JAI-037 Expand the official-source roadmap and unofficial-reference boundary

- **Labels**: `type:docs` `area:crawler` `priority:P1` `size:S`
- **Dependencies**: JAI-011
- **Goal**: map all 11 official candidates to executable Issues and define foreign-enterprise/commercial-platform boundaries.
- **Scope**: add `foreign_enterprise` with five official candidates; keep BOSS Zhipin manual-only; synchronize plan, catalog, Issue order, and WORKLOG.
- **Acceptance**:
  - [x] All 11 official candidates have implementation Issues or completion state.
  - [x] Foreign candidates are official career entry points and remain planned/disabled.
  - [x] Commercial references are physically separated and unauthorized automation is prohibited.
  - [x] Catalog validation, documentation links, and repository gate pass.

### JAI-038 Integrate Zhejiang civil-service recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:M`
- **Dependencies**: JAI-012, JAI-037
- **Goal**: collect public Zhejiang civil-service notices, application periods, and exam schedules.
- **Boundary**: never enter registration, payment, admission-ticket, score, or personal-query systems; prefer same-owner public announcement pages if the dynamic entry is unstable.
- **Acceptance**: at least three fixture groups, low-frequency live smoke test, and no duplicates across two persisted runs.

### JAI-039 Integrate Shanghai public civil-service recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:M`
- **Dependencies**: JAI-012, JAI-038
- **Goal**: collect Shanghai civil-service announcements, positions, and schedules.
- **Boundary**: prohibit `bm.shacs.gov.cn` registration interactions and every account/CAPTCHA flow.
- **Acceptance**: at least three fixture groups, public-URL enforcement, and no duplicates across two persisted runs.

### JAI-040 Integrate State Grid public recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:L`
- **Dependencies**: JAI-012, JAI-039
- **Goal**: collect graduate announcements and public Jiangsu/Zhejiang/Shanghai position data.
- **Boundary**: validate portal terms and public interfaces first; never collect profile, resume, or application interactions.
- **Acceptance**: at least three fixture groups, source-specific limits, visible failures, and no duplicates across two runs.

### JAI-041 Integrate China Mobile public recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:L`
- **Dependencies**: JAI-012, JAI-040
- **Goal**: collect group and Jiangsu/Zhejiang/Shanghai campus announcements and jobs.
- **Boundary**: official login-free pages/APIs only; never access resumes or applications.
- **Acceptance**: at least three fixture groups, region/campus filters, and no duplicates across two runs.

### JAI-042 Integrate China Telecom public recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:M`
- **Dependencies**: JAI-012, JAI-041
- **Goal**: collect the group public-recruitment column and relevant Jiangsu/Zhejiang/Shanghai jobs.
- **Boundary**: prefer the group public column; retain external application URLs as evidence without following interactions.
- **Acceptance**: at least three fixture groups, attachment traceability, and no duplicates across two runs.

### JAI-043 Integrate CNPC graduate recruitment

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:L`
- **Dependencies**: JAI-012, JAI-042
- **Goal**: collect graduate announcements, organizations, and public positions.
- **Boundary**: validate public access/terms before a dynamic portal; never login, edit resumes, or apply.
- **Acceptance**: at least three fixture groups, safe blocking when public access fails, and no duplicates across two runs.

### JAI-044 Integrate foreign-enterprise official sources 1–3

- **Labels**: `type:feature` `area:crawler` `priority:P1` `size:L`
- **Dependencies**: JAI-012, JAI-037
- **Goal**: establish foreign-enterprise collection with official Apple, Microsoft, and SAP career sites.
- **Scope**: China/Jiangsu-Zhejiang-Shanghai, graduate/student/internship and experienced public jobs; separate commits and at least three fixtures per source.
- **Acceptance**: incremental collection by stable official ID/URL, faithful English/Chinese fields, and no duplicates across two runs.

### JAI-045 Expand foreign-enterprise sources and section filters

- **Labels**: `type:feature` `area:crawler` `area:api` `priority:P1` `size:L`
- **Dependencies**: JAI-024, JAI-044
- **Goal**: integrate Siemens and P&G and expose a foreign-enterprise report/query section.
- **Scope**: two official Adapters; `foreign_enterprise` and Jiangsu/Zhejiang/Shanghai filtering; do not infer or assert legal ownership categories.
- **Acceptance**: five sources appear in one section with source text and position IDs preserved; filters/report regressions pass.

---

## 3. Post-MVP backlog (not part of the ten-week commitment)

### JAI-B01 Add scanned-PDF OCR

- `priority:P2`; start only when scans are common in high-value sources and manual handling becomes a bottleneck.

### JAI-B02 Add pgvector semantic retrieval

- `priority:P2`; first prove improvement over rules with a human-labeled benchmark.

### JAI-B03 Add LLM reranking

- `priority:P2`; apply only to rule/vector Top N with cost limits and offline evaluation.

### JAI-B04 Add Playwright dynamic sources

- `priority:P2`; only for high-value sources without stable public interfaces, isolated from normal collection.

### JAI-B05 Add a second notification channel

- `priority:P2`; only when the current channel remains unavailable or multi-device demand is explicit.

### JAI-B06 Integrate authorized commercial-platform data

- `priority:P2`; BOSS Zhipin and similar platforms require an official API, licensed data, or explicit written authorization. Until then, manual cross-check only; no crawler, login, anti-bot bypass, or access-control bypass.

## 4. Recommended execution order

Complete JAI-047 bilingual migration baseline → JAI-012 run/retry capability → implement JAI-013–JAI-021 in order. The user explicitly approved a bounded parallel exception: while JAI-021 remains in calendar-day acceptance observation only, JAI-022 and then JAI-023 may proceed on independent branches. Integration must follow JAI-021 → `develop`, updated `develop` → JAI-022 followed by its merge, then the newly updated `develop` → JAI-023. Preserve bilingual WORKLOG histories, resolve conflicts explicitly, and rerun the full gate at every integration boundary; never use rebase or history rewriting to avoid conflicts. Execute JAI-038–JAI-045 one source at a time after the release loop is stable. Execute JAI-048 as an independent documentation Issue before the next substantive change to any listed legacy document; never mix it into feature branches. Outside this explicitly approved observation/downstream-development exception, the personal WIP limit remains one primary feature plus one small test/docs Issue. If a dynamic portal cannot satisfy public-access and terms boundaries, record `blocked` and continue; never force coverage with login, CAPTCHA, Playwright, or evasion.
