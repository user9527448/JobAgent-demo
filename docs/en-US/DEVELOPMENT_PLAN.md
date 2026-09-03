# Recruitment Intelligence Agent Detailed Development Plan

> Simplified Chinese source: [`../DEVELOPMENT_PLAN.md`](../DEVELOPMENT_PLAN.md)
> Project code name: JOBAGENT V1.0
> Document status: Executable baseline
> Intended team: one developer covering product, engineering, testing, and operations
> Planned duration: 10 weeks; a daily-usable MVP in week 8 and an Agent-enhanced release in week 10

## 1. Project definition

### 1.1 One-sentence positioning

A personal recruitment-intelligence system that collects enterprise campus-recruiting, civil-service, and public-institution vacancies; parses announcements and attachments; filters and ranks them against personal preferences; and produces a daily actionable briefing.

### 1.2 Core value chain

```text
Source monitoring → Incremental collection → Source preservation → Attachment parsing
                  → Job structuring → Quality validation → Rule matching
                  → Daily report → Notification → Natural-language query
```

The primary asset is stable, traceable recruitment data rather than a chat interface. The Agent is a query and action entry point built on top of that data system.

### 1.3 Target user and operating boundary

- Initially serve one user; do not build registration, tenancy, permissions, or billing.
- Prefer public sources that require no login and permit reasonable access.
- Provide discovery, understanding, ranking, and reminders, but not automatic applications.
- One run per day is sufficient; sub-second updates and high concurrency are unnecessary.

## 2. Release scope

### 2.1 MVP (week 8)

- Integrate five stable sources covering both enterprise campus recruitment and civil-service/public-institution recruitment.
- Incrementally collect static HTML list and detail pages.
- Store source announcements, source URLs, collection timestamps, and content fingerprints.
- Download and parse PDF and XLSX/XLS attachments; flag scanned PDFs for manual handling.
- Structure announcements and positions while retaining field evidence and extraction confidence.
- Support personal preference configuration and explainable rule-based scoring.
- Generate Markdown/HTML daily reports and send them through one WeChat channel.
- Provide runtime logs, failure retries, and minimum health checks.

### 2.2 Agent-enhanced release (week 10)

- Query jobs, open details, and explain recommendation scores in natural language.
- Trigger collection and report regeneration through controlled operations.
- Allow the Agent to call explicit tools only; it must not write the database directly or execute arbitrary code.

### 2.3 Source-expansion track (does not block MVP release)

- Put all 11 existing official candidate sites on the implementation roadmap. The MVP target remains five stable sources; add the rest one site at a time after the common pipeline is reliable.
- Add a foreign-enterprise section, initially covering the official Apple, Microsoft, Siemens, SAP, and P&G career sites. Classify them as `foreign_enterprise` and target China/Jiangsu-Zhejiang-Shanghai jobs.
- Treat commercial platforms such as BOSS Zhipin as manual cross-check references only. Do not build an Adapter where terms prohibit automated collection; reconsider machine integration only with an official API, licensed data, or explicit written authorization.
- “On the roadmap” never authorizes bypassing restrictions. Sources requiring login, CAPTCHA, anti-bot evasion, or terms violations remain `planned`/`blocked`; prefer a public announcement endpoint owned by the same official body.

### 2.4 Bilingual-documentation governance track (does not block the product track)

- JAI-046 established separate English and Simplified Chinese files, same-commit synchronization, and repository-local Git authorship rules.
- JAI-047 adds English mirrors for the substantively changed plan and Issue backlog, archives the mixed-language WORKLOG byte-for-byte, and starts separate active English and Simplified Chinese logs.
- JAI-048 inventories and migrates remaining legacy single-language documents. If a feature Issue substantively changes one first, it must add the missing counterpart in the same commit.
- Historical archives are not translated, deleted, or rewritten. Code identifiers, environment variables, error codes, URLs, and commands remain unchanged.

### 2.5 Out of scope for V1

- Multiple users, login, permissions, subscriptions, or commercialization.
- Recruitment-platform account login, CAPTCHA bypass, or automatic applications.
- Elasticsearch, a standalone vector database, Kubernetes, or microservices.
- Arbitrary-site discovery or a universal crawler.
- Multi-Agent collaboration or complex long-term memory.
- A full recruitment-site frontend; only necessary configuration and runtime-status views are planned.

## 3. Success metrics and acceptance definitions

| Metric | MVP target | Measurement |
|---|---:|---|
| Source availability | ≥ 90% | Successful source runs among scheduled runs over the last seven days |
| Duplicate announcement rate | ≤ 2% | Duplicates within one source according to URL/content fingerprints |
| Core-field completeness | ≥ 85% | Completeness of organization, title, region, deadline, and source link |
| Attachment parsing success | ≥ 80% | Readable text PDFs and spreadsheet attachments; excludes corrupt/encrypted files |
| Report punctuality | ≥ 95% | Last 20 scheduled runs completed inside the target window |
| Traceability | 100% | Every recommendation links back to an announcement or attachment |
| Daily manual maintenance | ≤ 10 minutes | Time needed to inspect and handle ordinary exceptions |

LLM extraction must never overwrite raw source data. Critical dates must point to source evidence. Recommendation scores are ranking signals, not promises of selection.

## 4. Technical approach

### 4.1 Technology stack

| Module | V1 choice | Rationale |
|---|---|---|
| Language | Python 3.11+ | Reuse the existing Python environment and minimize maintenance |
| Web/API | FastAPI + Pydantic v2 | Health, configuration, and query APIs |
| ORM/migrations | SQLAlchemy 2 + Alembic | Explicit models and migration history |
| Database | PostgreSQL 16 | Structured data, JSONB, and possible future pgvector support |
| HTTP/HTML | httpx + selectolax/BeautifulSoup | Prefer static sites; add Playwright only when justified |
| Scheduling | APScheduler | Sufficient for a single V1 instance; no Celery/Redis yet |
| PDF | PyMuPDF | Text extraction with page-level evidence |
| Spreadsheets | pandas + openpyxl | XLSX cleanup and header detection |
| LLM | OpenAI-compatible, replaceable provider | Only for unstable extraction and explanations |
| Testing | pytest + pytest-asyncio | Unit, integration, and fixture regressions |
| Runtime | Docker Compose | Local API, worker, and PostgreSQL startup |
| Observability | Structured standard logs + database run records | Avoid premature monitoring infrastructure |

### 4.2 Suggested repository structure

```text
JOBAGENTV1.0/
├─ app/
│  ├─ api/                 # HTTP routes
│  ├─ core/                # Configuration, logging, exceptions
│  ├─ db/                  # ORM, migration entry points, repositories
│  ├─ crawlers/            # Source Adapters and concrete sources
│  ├─ parsers/             # HTML/PDF/Excel parsing
│  ├─ extraction/          # Rule and LLM extraction
│  ├─ matching/            # Filtering, scoring, explanations
│  ├─ reports/             # Daily-report rendering
│  ├─ notifications/       # Delivery channels
│  ├─ agent/               # Add in weeks 9–10
│  └─ jobs/                # Scheduling and pipeline orchestration
├─ migrations/
├─ tests/
│  ├─ fixtures/            # Sanitized real announcements and attachments
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
├─ data/                   # Local runtime data; ignored by Git
├─ docs/
├─ scripts/
├─ .env.example
├─ compose.yaml
├─ pyproject.toml
└─ README.md
```

### 4.3 Runtime architecture

```text
APScheduler / manual trigger
        │
        ▼
 Pipeline Orchestrator ──→ Crawl Run / Step Logs
        │
        ├─ Source Adapter → Raw Document → Attachment Store
        ├─ Parser → Extractor → Validator
        ├─ Matcher → Recommendation
        └─ Reporter → Notifier

FastAPI ──→ PostgreSQL ←── Agent Tools (weeks 9–10)
```

Collection, parsing, scoring, and delivery remain normal Python services. The Agent calls these existing services so stable business logic is not embedded in prompts.

## 5. Core data model

| Entity | Purpose | Key fields |
|---|---|---|
| `sources` | Source configuration | name, base_url, category, adapter, enabled, crawl_interval |
| `crawl_runs` | One source run | source_id, status, started_at, finished_at, stats, error |
| `raw_documents` | Immutable announcement source | source_id, canonical_url, title, raw_html/text, published_at, content_hash |
| `attachments` | Attachment and parsing state | document_id, url, file_name, mime_type, sha256, local_path, parse_status |
| `job_posts` | Structured announcement | document_id, organization, category, region, apply_url, start_at, deadline |
| `job_positions` | Positions under an announcement | post_id, name, department, location, education, major, headcount, requirements |
| `field_evidence` | Field provenance | entity_type, entity_id, field_name, source_type, quote/page/cell, confidence |
| `user_preferences` | Single-user profile | regions, education, majors, job_keywords, organization_types, exclusions |
| `match_results` | Recomputable score | position_id, score, score_version, components, matched_rules, generated_at |
| `reports` | Daily report snapshot | report_date, format, content, item_count, status |
| `notifications` | Delivery record | report_id, channel, status, attempts, sent_at, error |

Key constraints:

- `raw_documents(source_id, canonical_url)` is unique; content fingerprints also detect moved or updated pages.
- Source and attachment parsing results are appendable/versioned and never overwrite evidence in place.
- `job_positions` may be empty; retain announcement-level data and place it in the needs-review group.
- Persist all timestamps in UTC; display and schedule in `Asia/Shanghai`.
- Disabling a source never cascades into deleting historical announcements.

## 6. Core process design

### 6.1 Incremental collection

1. The scheduler creates a `crawl_run` for each enabled source.
2. The Adapter loads list pages and emits candidate URLs.
3. Canonical URLs and content fingerprints remove duplicates.
4. New or changed pages are fetched and stored as source documents.
5. Attachments are downloaded to a local object directory and recorded with SHA-256.
6. One item failure does not stop the source; threshold breaches mark the run failed.

Minimum Adapter interface:

```python
class SourceAdapter(Protocol):
    async def discover(self, cursor: dict | None) -> list[DiscoveredItem]: ...
    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput: ...
```

Storage, de-duplication, retries, and logging belong to the common pipeline, not individual Adapters.

Starting with JAI-011, the manually maintained `config/source_catalog.toml` records candidate sites, regions, integration status, and title keywords. It does not replace the runtime `sources` table. Only entries with `implementation_status = "active"`, `enabled = true`, and an explicitly registered Adapter may run. Unverified dynamic portals remain `planned` and disabled. Categories cover campus recruitment, public examinations, state-owned enterprises, and official foreign-enterprise career sites. Commercial platforms are excluded from the executable catalog; see [`../REFERENCE_SOURCES.md`](../REFERENCE_SOURCES.md). Catalog targets and maintenance rules are documented in [`../SOURCE_CATALOG.md`](../SOURCE_CATALOG.md).

### 6.2 Parsing and extraction

Priority: deterministic rules > table mappings > LLM supplementation.

1. Remove navigation, footers, and repeated text from HTML.
2. Extract PDF text page by page; low text density becomes `ocr_required`, and V1 does not require OCR.
3. Detect spreadsheet sheets, title rows, and merged cells while preserving original rows/cells.
4. Extract dates, links, organizations, and regions with rules first.
5. Send irregular body fragments to an LLM with strict JSON Schema output.
6. Validate date logic, enums, required fields, and evidence; route anomalies to manual review.

### 6.3 Matching and ranking

V1 uses explainable rules rather than an LLM-generated total score:

```text
Total = hard-condition pass × (
  Region match 25 +
  Job keyword/direction 30 +
  Major match 15 +
  Organization preference 10 +
  Deadline urgency 10 +
  Information completeness 10
)
```

- Insufficient education, explicit exclusion terms, and closed deadlines are hard filters.
- Persist each component's rule, input, and score for explanations and recomputation.
- Evaluate embedding retrieval or LLM reranking only after week 10; neither may replace hard conditions.

### 6.4 Daily reports and notifications

Every report has four groups:

1. **Apply first**: high match and open application window.
2. **Closing soon**: deadline within 72 hours.
3. **Added today**: first observed today and not in the first two groups.
4. **Needs confirmation**: missing deadline, failed position-table parsing, or critical conflicts.

Each item includes title, organization, region, deadline, recommendation reason, risks/missing fields, application entry point, and source link. Delivery is idempotent: one report/channel combination succeeds at most once by default.

## 7. Ten-week delivery plan

### Week 1: engineering baseline and vertical technical validation

**Goal**: start the project and prove “web page → raw source → PDF text” with one real sample.

- Initialize structure, dependencies, configuration, and logging.
- Add API + PostgreSQL Docker Compose.
- Provide `/health/live` and `/health/ready`.
- Establish testing and CI.
- Validate one static HTML/PDF source.

**Acceptance**: a new environment starts from the README; migrations run; one real announcement and its PDF can be stored and parsed.

### Week 2: data model and collection framework

**Goal**: stabilize the common pipeline and make sources pluggable.

- Implement core tables, constraints, indexes, and the first migration.
- Implement Adapter protocol, HTTP client, rate limiting, retries, and timeouts.
- Implement URL canonicalization, fingerprints, and idempotent writes.
- Implement attachment discovery, download, validation, and storage.
- Establish a maintainable site catalog and source-specific include/exclude terms.
- Integrate source 1, prioritizing the public SASAC recruitment column.

**Acceptance**: two identical runs create no duplicates; item failures are logged without stopping the batch.

### Week 3: initial sources and run records

**Goal**: cover at least three page structures and make collection observable.

- Integrate sources 2 and 3.
- Add `crawl_runs` statistics, error classes, and failed-item reruns.
- Add a manual run command/API.
- Add offline HTML fixtures for all three sources.
- Choose official, public, login-free, stable, high-value sources; do not enable application systems or unverified dynamic portals.

**Acceptance**: all three sources run incrementally and report discovered, created, updated, skipped, and failed counts.

### Week 4: PDF/Excel attachment parsing

**Goal**: convert attachments into a traceable standard intermediate representation.

- Extract PDF page text and identify encryption/scans/errors.
- Process XLSX/XLS sheets, headers, and merged cells.
- Add parser registry and a common output protocol.
- Add at least ten sanitized real attachment fixtures.

**Acceptance**: supported attachment batch success reaches 80%, and output points to page, row, or cell evidence.

### Week 5: structured announcement and position extraction

**Goal**: create `job_posts` and `job_positions` from body text and attachments.

- Add rule extraction for dates, region, organization, and application links.
- Add replaceable LLM providers, JSON Schema, timeouts, and retries.
- Merge body/attachment results and handle conflicts.
- Store field evidence, confidence, and extraction version.
- Add extraction regressions.

**Acceptance**: core-field completeness reaches 85% on golden samples; invalid dates never enter silently.

### Week 6: quality control and five-source coverage

**Goal**: reach the MVP source count and make failures recoverable.

- Prefer the National College Student Employment Service Platform and Shanghai public-institution notices for sources 4 and 5. If dynamic entry points violate the public-access boundary, use a stable official announcement endpoint or record a blocker.
- Add field validation, review state, and reparsing.
- Add source health and consecutive-failure data.
- Backfill and check duplicates.

**Acceptance**: five sources run for three consecutive days; every failure has a class and retry path.

### Week 7: preferences, scoring, and reports

**Goal**: turn the data pipeline into a useful personal information product.

- Add single-user preference configuration.
- Add hard filters, component scoring, versions, and explanations.
- Add report queries, groups, and Markdown/HTML templates.
- Manually review Top 20 rankings on historical data.

**Acceptance**: every recommendation has an explanation and source link; preference changes support full recomputation.

### Week 8: scheduling, WeChat delivery, and MVP release

**Goal**: complete the daily loop unattended.

- Add daily scheduling, concurrency locks, and misfire handling.
- Integrate one WeChat channel.
- Add idempotent delivery, retries, and failure records.
- Complete end-to-end tests, backup/restore guidance, and operations documentation.
- Prepare the `v0.1.0-mvp` checklist.

**Acceptance**: five consecutive unattended runs complete collection → parsing → matching → report → delivery without duplicate notifications.

### Week 9: minimal configuration console and query API

**Goal**: reduce daily maintenance and expose a stable tool layer for the Agent.

- Add source listing/toggling, preference editing, run history, and failure APIs.
- Add a minimal configuration page rather than a general admin console.
- Add job search, job detail, and score explanation services.
- Add authorization boundaries and audit logs for tools.

**Acceptance**: ordinary configuration and troubleshooting require neither database edits nor direct configuration-file edits.

### Week 10: Agent integration and stability finish

**Goal**: query and operate the existing system through controlled natural language.

- Implement `search_jobs`, `get_job_detail`, `explain_match`, `generate_report`, and `run_crawl` tools.
- Define Agent instructions, tool parameter Schemas, confirmation rules, and step limits.
- Evaluate query, explanation, report regeneration, and manual collection tasks.
- Fix stability issues and release `v0.2.0-agent`.

**Acceptance**: predefined tasks succeed at least 90%; writes are audited and duplicate requests remain idempotent.

## 8. Testing strategy

### 8.1 Test pyramid

- **Unit**: URL canonicalization, date parsing, header recognition, scoring rules, templates.
- **Contract**: each Adapter produces stable output from fixed HTML/JSON fixtures.
- **Integration**: database, attachment store, LLM mock, notification mock.
- **End-to-end**: fixed source fixture through report generation; CI does not depend on live sites.
- **Live smoke**: a few pages/selectors only, never high-frequency target-site access in CI.

### 8.2 Golden samples

- Keep at least three list and three detail fixtures per integrated source.
- Keep at least ten PDF/Excel samples covering multi-page tables, merged cells, blank rows, and date formats.
- Sanitize personal data and confirm permission before committing samples.
- Run the complete regression set after parser rules or prompts change.

## 9. Security, compliance, and cost

- Follow site terms, robots rules, and reasonable request rates; never bypass login, CAPTCHA, or access controls.
- Identify the application in User-Agent and configure per-source limits, timeouts, and exponential backoff.
- Keep tokens, database passwords, and delivery secrets in environment variables; never commit `.env`.
- Do not log secrets, complete resumes, or unnecessary personal data.
- Send only required announcement fragments to LLMs and record token/cost data.
- Apply a daily LLM budget and circuit breaker; move failures to review rather than retrying forever.

## 10. Risks and responses

| Risk | Probability/impact | Response and exit condition |
|---|---|---|
| Site structure changes | High/high | Adapter contracts and selector health; disable and alert after consecutive failures |
| Dynamic site/CAPTCHA | Medium/high | Prefer public static sources; replace after one day without stable access |
| Complex attachments | High/high | Preserve source/evidence; route scans to manual handling without blocking announcements |
| LLM hallucination | Medium/high | Schema, evidence, deterministic validation; omit unsupported critical dates |
| Scope expansion | High/high | Complete P0 work per week; defer P1 when needed and keep P2 out of the Sprint |
| Delivery instability | Medium/medium | Idempotency, retries, persisted reports, and direct report viewing |
| Maintenance cost exceeds value | Medium/high | Enforce ≤10 minutes/day and remove unstable low-value sources |

## 11. Project-management conventions

### 11.1 Milestones

| Milestone | Period | Completion signal |
|---|---|---|
| M1 Foundation | W1 | Project starts and vertical validation is complete |
| M2 Collection | W2–W3 | Three sources collect incrementally and reliably |
| M3 Extraction | W4–W6 | Five sources support parsing, extraction, and quality control |
| M4 Intelligence | W7 | Matching and daily reports are usable |
| M5 MVP Release | W8 | Scheduled delivery loop is live |
| M6 Agent | W9–W10 | Configuration console and Agent tools are released |

### 11.2 Priority

- `priority:P0`: blocks the active milestone or MVP core loop.
- `priority:P1`: materially improves reliability or maintenance and may fit if capacity permits.
- `priority:P2`: enhancement work; default to post-MVP backlog.

### 11.3 Definition of Ready

Before starting, an Issue must define goal, scope, acceptance criteria, dependencies, test method, and non-goals. A source Issue must also record entry URL, page type, expected request frequency, and compliance review.

### 11.4 Definition of Done

- Implementation matches acceptance criteria without hidden scope.
- Critical logic has automated tests and all checks pass.
- Database changes include an executable migration.
- Configuration is reflected in `.env.example`; no secrets are committed.
- Logs and errors identify the failed source and step.
- User-visible and operational behavior is documented.
- Verification evidence is recorded before the corresponding Issue closes.

## 12. Stage gates and adjustment rules

- **W2 gate**: if source 1 is not idempotent, do not add sources; fix the common pipeline first.
- **W4 gate**: if attachment parsing is below 60%, move OCR explicitly out of MVP and validate with higher-value samples.
- **W6 gate**: if five sources are too expensive to maintain, ship MVP with three stable sources; stability outranks count.
- **Source-expansion gate**: 11 official candidates and the foreign-enterprise section do not block MVP. Keep any source disabled when it requires login, CAPTCHA, anti-bot evasion, or terms violations, and record the reason in the catalog and WORKLOG.
- **W8 gate**: do not mark MVP complete until five unattended runs succeed.
- **Agent gate**: if the MVP data loop is unstable, use weeks 9–10 to fix it instead of adding the Agent early.

## 13. Current next step

JAI-011, JAI-037, JAI-046, JAI-047, and JAI-012 through JAI-020 have been merged and normally pushed to `develop` in order. The current baseline is JAI-020 non-fast-forward merge `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`. JAI-021 source 4-5 implementation is complete and its dedicated branch continues the consecutive-calendar-day stability acceptance.

The user explicitly approved starting JAI-022 in parallel while JAI-021 waits only for calendar-day observations. `feature/jai-022-single-user-preferences` was created directly from three-way-verified `develop` and contains no unmerged JAI-021 commit. The singleton model, read/full-replacement API, schema/enum validation, recomputation signal, unrestricted defaults, migration, tests, and paired JAI-022 documentation were completed on 2026-08-30 and passed the PostgreSQL-enabled full gate. JAI-021 must complete and merge first; then normally merge the latest `develop` into JAI-022, preserve both WORKLOG histories, resolve paired-document conflicts explicitly, and rerun the full gate. Never rebase or rewrite published history. OCR remains deferred to JAI-B01. Execute JAI-048 as a separate documentation Issue and never mix broad legacy-document migration into feature branches. Integrate remaining official and foreign-enterprise sources one by one under JAI-038–JAI-045 without bypassing login, CAPTCHA, anti-bot controls, or platform terms.

The user subsequently approved continuing JAI-021 acceptance observation in parallel with downstream development and required an explicit integration record. `feature/jai-023-hard-filter-versioned-scoring` was created from the three-way-verified, published JAI-022 tip `44ed50292aa6609c7c4eaa1fb16e0793082d4e0a`. Integration order is fixed: merge JAI-021 into `develop` first; normally merge that `develop` into JAI-022 and complete the JAI-022 merge; then normally merge the updated `develop` into JAI-023, preserving every bilingual WORKLOG history, resolving conflicts explicitly, and rerunning the complete PostgreSQL-enabled gate. Rebase and published-history rewriting are prohibited. JAI-023 is limited to hard filters, versioned rule scoring, persisted component explanations, and preference-triggered full recomputation; JAI-024 reports and notifications remain out of scope.

The JAI-023 implementation, migration, boundary tests, and paired documentation completed on 2026-08-30. The PostgreSQL-enabled complete gate passed all 241 tests with no skips and 88.47% coverage. This feature branch must still follow the recorded merge train: after JAI-021 and JAI-022 integrate into `develop` in order, normally merge the latest `develop`, preserve the logs, and pass the complete gate again before integration. JAI-024 must not start early on this branch.

The user approved continuing downstream development while preserving explicit version boundaries and records. `feature/jai-024-daily-report-rendering` was created as an isolated worktree from published JAI-023 tip `9592a16d7dee12fbe6c555407a3607a492b2cd03`; the merge train is extended to JAI-021 → JAI-022 → JAI-023 → JAI-024. JAI-024 deterministic four-section reports, Markdown/HTML rendering, immutable snapshots, original-source links, and APIs are implemented. After a Windows restart recovered Docker/PostgreSQL, seven focused database tests passed; the final complete gate passed all 252 tests with no skips and 88.53% coverage. Feature commit `ffa065f` was normally pushed and verified across all three refs. JAI-025 weight tuning, JAI-026 scheduling, and JAI-027 notifications remain deferred, and JAI-024 stays isolated until it enters the recorded merge train in order.
