# JOBAGENT Development Work Log

> Language: English. Simplified Chinese mirror: [`zh-CN/WORKLOG.md`](zh-CN/WORKLOG.md).
>
> The original mixed-language history through JAI-046 is preserved byte-for-byte in
> [`archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`](archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)
> with SHA-256 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`.
>
> Last updated: 2026-09-05
>
> Active branch: `feature/jai-025-top-20-quality-review`

## 1. Current status

| Issue | Status | Branch / commit | Notes |
|---|---|---|---|
| JAI-001 through JAI-010 | Complete, merged to `develop` | See legacy archive | Foundation, collection framework, raw-document versioning, and attachment storage |
| JAI-036 | Complete, merged to `develop` | `develop` / `82adb73` | Initial Simplified Chinese mirrors and bilingual navigation |
| JAI-011 | Complete, merged to `develop` | `develop` / `368c369` | Three official-source adapters, fixtures, persistence, and idempotency acceptance |
| JAI-037 | Complete, merged to `develop` | `develop` / `c649862` | Official-source expansion roadmap, foreign-enterprise candidates, and reference-source boundary |
| JAI-046 | Complete, merged and pushed to `develop` | `develop` / `f07b6d5` | Separate bilingual-file rules and repository-local Git authorship policy |
| JAI-047 | Complete, merged and pushed to `develop` | `develop` / `87cd753` | Legacy-document migration baseline, separate bilingual work logs, and JAI-048 inventory |
| JAI-012 | Complete, merged and pushed to `develop` | `develop` / `70dd3b2` | Manual source runs, persistence counters, run summaries, and failed-URL-only idempotent retries verified |
| JAI-013 | Complete, merged and pushed to `develop` | `develop` / `36d389f` | MIME registry, traceable text/table schemas, statuses, error codes, tests, and bilingual documentation verified |
| JAI-014 | Complete, merged and pushed to `develop` | `develop` / `8f21745` | Page text, metadata, deterministic scan detection, encrypted/corrupt diagnostics, tests, and bilingual docs verified |
| JAI-015 | Complete, merged and pushed to `develop` | `develop` / `fca197d` | XLSX multi-sheet/header/data parsing, merged-cell evidence, review diagnostics, tests, and bilingual docs verified |
| JAI-016 | Complete, merged and pushed to `develop` | `develop` / `1dc7a10` | Ten sanitized PDF/XLSX fixtures, reviewed intermediate snapshots, offline evaluation, tests, and bilingual docs verified |
| JAI-017 | Complete, merged and pushed to `develop` | `develop` / `c7a2ebe` | Deterministic dates/timezones, regions, URLs, headcount, education/categories, raw/normalized values, and parser evidence verified |
| JAI-018 | Complete, merged and pushed to `develop` | `develop` / `c013544` | Replaceable provider, strict structured output, versioned prompts, bounded retries, usage/cost records, and daily-budget queueing verified |
| JAI-019 | Complete, merged and pushed to `develop` | `develop` / `82797d1` | Deterministic body/attachment precedence, explicit conflicts, extraction versions, and durable field evidence verified |
| JAI-020 | Complete, merged and pushed to `develop` | `develop` / `f56365f` | Validation severity, review eligibility, and idempotent document reparsing verified |
| JAI-021 | Complete, merged and pushed to `develop` | `develop` / `8cc0b2e` | Day 3 accepted under the recorded external-endpoint waiver; actual 4/5 result retained; post-merge PostgreSQL gate passed |
| JAI-022 | Complete, merged and pushed to `develop` | `develop` / `e7948c9` | JAI-021/JAI-022 histories preserved; post-merge PostgreSQL gate passed with 254 tests |
| JAI-023 | Complete, merged and pushed to `develop` | `develop` / `5935b52` | JAI-021–JAI-023 histories preserved; post-merge PostgreSQL gate passed with 271 tests |
| JAI-024 | Complete, merged and pushed to `develop` | `develop` / `0aa6b23` | Post-merge PostgreSQL gate passed with 282 tests and 87.96% coverage |
| JAI-025 | In progress; flow evidence complete, full gate and G5 pending | `feature/jai-025-top-20-quality-review` | Owner-approved flow-first exception is explicit; live human-review volume is deferred to JAI-049 |

## 2. Current decisions

### D-015 Separate language files are mandatory

English and Simplified Chinese documentation are maintained as separate files. Existing documents keep their established language; missing counterparts are added without changing the original document's primary language. Both versions are updated in the same commit.

### D-016 Preserve the mixed WORKLOG as an immutable archive

The former `docs/WORKLOG.md` mixed English and Chinese history. JAI-047 preserves its exact bytes under `docs/archive/` and starts new active English and Simplified Chinese logs. The archive is historical evidence and must not receive new entries.

### D-017 Migrate legacy documents in bounded Issues

JAI-047 covers the planning/backlog mirrors, bilingual indexes, and WORKLOG split needed to make the new policy executable. Remaining legacy single-language documents are inventoried and assigned to JAI-048; they are not rewritten opportunistically in feature Issues.

### D-018 JAI-012 exposes a command boundary, not the later maintenance API

JAI-012 provides `scripts/manage_crawl.py run/show/retry` over reusable orchestrator and repository contracts. Source/run maintenance APIs remain JAI-030, and scheduling/locks remain JAI-026, avoiding premature overlap with later Issues.

### D-019 Failed-item retries rediscover and filter

A retry repeats the source's public list discovery to reconstruct source-specific metadata, then fetches only URLs persisted in the prior run's structured failures. The command never accepts an arbitrary retry URL, never directly fetches an item that is no longer rediscovered, and never re-fetches prior successful URLs.

### D-020 Manual collection persists before counting item success

Manual runs pass each fetched detail through `SqlAlchemyRawDocumentRepository`. Run statistics count `created`, `updated`, `skipped`, and all failures while retaining detail-only failure counters. Repeating an uncertain or already completed write returns `skipped`, preserving raw-document idempotency.

### D-021 Parser output is a strict in-memory contract before persistence orchestration

JAI-013 defines immutable `ParseSource`, location, block, issue, and result contracts plus explicit MIME registration. It does not add an intermediate-block table, attachment parsing worker, PDF/Excel implementation, or field extraction. Later Issues may map the completed result status and safe diagnostics onto existing attachment fields.

### D-022 Evidence coordinates belong to every intermediate block

Text and table blocks retain a persisted source reference and a one-based page, inclusive line range, or worksheet/A1 cell range. Table cells carry their own locations, and both table/result construction reject mixed-source output before downstream extraction can consume it.

### D-023 PDF scan detection uses a configurable deterministic text threshold

`PdfTextPolicy` defaults to 40 non-whitespace characters per page averaged across the document. Results below the threshold become `ocr_required` while retaining any partial page blocks for manual review. The parser does not invoke OCR; broader threshold evaluation remains JAI-016 and OCR implementation remains JAI-B01.

### D-024 PDF failures return safe status objects instead of third-party exceptions

Password-protected PDFs return `parser.encrypted_document`; empty, invalid, damaged, or unreadable PDFs return `parser.corrupt_document`; wrong MIME input returns `parser.invalid_input`. Results contain safe fixed messages without file content, passwords, or raw PyMuPDF exception text.

### D-025 JAI-017 extraction remains an evidence-preserving in-memory boundary

Deterministic extraction groups output by parser text block or table row. Every field carries its raw value, normalized value, source quote, and parser location. Cross-block/body/attachment merging and database `field_evidence` persistence remain JAI-019 so JAI-017 cannot silently choose between sources.

### D-026 Contradictory or unsupported evidenced values become diagnostics

Invalid dates, inverted date ranges, relative URLs without an explicit base, non-exact headcounts, and unknown region/education/category values do not produce normalized fields. Safe `ExtractionIssue` objects retain raw values and evidence; unlabeled critical-looking text is ignored rather than guessed.

### D-027 Review and recommendation eligibility are derived from persisted validation

JAI-020 uses `approved`, `review_required`, and `blocked` as deterministic outcomes. Warnings require review but remain eligible; any error blocks automatic recommendation. Legacy rows are explicitly `legacy-unvalidated` and ineligible rather than silently approved.

### D-028 Reparse versions are explicit idempotency keys

The same document/extraction version may be repeated only when its merged result hash is unchanged. A rule correction uses a new version and appends post, position, evidence, and validation history. The default stored-document pipeline performs no live-source or LLM request.

### D-029 Parallel matching work keeps an explicit merge train

The user approved JAI-023 development while JAI-021 remains in calendar-day observation. The JAI-023 branch starts at published JAI-022 tip `44ed50292aa6609c7c4eaa1fb16e0793082d4e0a`. Integration order is JAI-021 into `develop`, updated `develop` into JAI-022 followed by the JAI-022 merge, and then the newly updated `develop` into JAI-023. Every boundary preserves both bilingual logs, resolves conflicts explicitly, and reruns the complete PostgreSQL gate. Rebase and published-history rewriting remain prohibited.

### D-030 Missing evidence never becomes a guessed hard-filter failure

An explicit insufficient education, reached deadline, exclusion hit, or JAI-020 recommendation block filters a position. Missing education or deadline evidence remains eligible and loses only the corresponding urgency/completeness signal. This keeps needs-confirmation data available for JAI-024 without inventing values.

### D-031 Evaluation time and preference acknowledgement are transactional inputs

The matching engine receives timezone-aware `evaluated_at`; it never reads the process clock, so urgency and hashes remain reproducible. Full recomputation locks the JAI-022 singleton and acknowledges its sticky signal only in the same transaction as all current-position results. A failure rolls back both writes and acknowledgement, while successful acknowledgement preserves the preference-value `updated_at` identity.

### D-032 JAI-024 extends the isolated merge train without changing its ancestors

The user approved continued downstream development while JAI-021 waits for calendar-day observations. JAI-024 starts from published JAI-023 tip `9592a16d7dee12fbe6c555407a3607a492b2cd03` in its own worktree. Integration order is JAI-021 → JAI-022 → JAI-023 → JAI-024; each downstream branch receives the newly updated `develop` through a normal merge, preserves both bilingual logs, resolves conflicts explicitly, and reruns the complete PostgreSQL gate. Rebase, force push, and published-history rewriting remain prohibited.

### D-033 JAI-025 preserves the v1 baseline and evaluates an explicit v2

The quality review must replay `jai-023-v1` unchanged and compare it with a new score version over the same fixed, sanitized, manually reviewable sample set. Labels, reasons, Top 20 false positives, and misses remain explicit artifacts; tuning may change only the new version. Scheduling, delivery, LLM reranking, embeddings, and live-source collection remain outside JAI-025.

### D-034 Approved recovery path for the missing historical review set

The project owner approved this recovery path and G1 on 2026-09-05. It keeps JAI-025's original historical/manual-review intent instead of declaring the synthetic dry-run set sufficient. Use the local `jobagent` database as the controlled evidence store: upgrade it from Alembic `0003_attachment_storage` to repository head, transactionally bootstrap only the five catalog entries already marked `active` and `enabled`, and add a backward-compatible optional detail limit to the existing manual crawl path before any persistent live run. Collect public data only, with concurrency 1, at least one second pacing, no login/CAPTCHA/access-control bypass, a maximum of 60 detail attempts, at least three contributing sources, and no source contributing more than 30 accepted review candidates.

Persist immutable raw documents and deterministic extraction/evidence through existing services. Keep the source-facing review sheet and source URL mapping under ignored `data/`; commit only a sanitized benchmark after the project owner labels at least 50 distinct positions and confirms each relevance category/rationale. Do not delete rejected source records; exclude them through the review manifest. The published feature history is not rewritten: if real labels require changing the provisional `jai-025-v2` rules, the final candidate receives a new score version rather than silently changing v2. JAI-026 scheduling, JAI-027 delivery, JAI-030 source-maintenance APIs, LLM calls, and new source adapters remain out of scope.

Approval gates are mandatory: G1 approves the database upgrade, active-source bootstrap, and bounded-crawl code change; G2 approves the read-only discovery counts and per-source allocation before persistent HTTP detail requests; G3 confirms the human labels and sanitized transformation before tuning; G4 approves any final weight/rule change and version identifier after seeing before/after Top 20 false positives and misses; G5 approves completion and safe merge after paired documentation and the PostgreSQL full gate. A mismatch, access restriction, insufficient distinct positions, or quality tradeoff stops at its current gate and is recorded; no automatic scope expansion or destructive rollback is allowed.

### D-035 Close the executable MVP flow before quality-volume optimization

On 2026-09-05 the project owner changed the immediate priority from blocking on the 50-position live-review volume to completing and validating the existing end-to-end flow. G2 allocation `3/0/2/5/0` is approved for source IDs 1–5. The run remains bounded to ten public details across three reachable sources, with the existing concurrency, pacing, evidence, and access-control rules unchanged.

If this bounded run yields fewer than 50 distinct live positions, the shortfall is recorded as explicit quality debt rather than concealed or guessed. The current synthetic 60-case set may continue to verify deterministic evaluation mechanics, but it must remain labelled synthetic and cannot be represented as historical human review. Source-volume expansion, Firstjob's empty discovery, China Mobile connectivity, and a future >=50 live human-labelled benchmark are deferred optimization items; they do not authorize new adapters, larger quotas, or changes to published score versions in this step.

## 3. Active work history

### 2026-08-14 — JAI-046 bilingual documentation and Git identity rules completed

- Verified the handoff branch `feature/jai-046-bilingual-docs-git-identity` at `29071dff1a80d26bac892d7bce548cf593c78eec`; the worktree was clean and the branch was not yet merged into `develop`.
- Verified JAI-037 was merged at `c649862`, `main` remained at `e72f50e`, and `develop` had no divergence from its cached tracking reference.
- Verified repository-local and global Git authorship as `user9527448 <2537759248@qq.com>`; no prior commit or author history was rewritten.
- The first quality-gate run passed Ruff and Mypy and 83 non-database tests, but skipped six PostgreSQL tests because Docker was not running; coverage was 83.06%, below the 85% gate.
- After Docker Desktop was started, the database-enabled gate passed: Ruff format/lint, Mypy, all 89 tests, and 88.35% coverage.
- Merged JAI-046 into `develop` with non-fast-forward merge `f07b6d5` and pushed normally. Local HEAD, `origin/develop`, and GitHub `ls-remote` all matched `f07b6d50ed9abda08d38883eefa3904b98b99455`.

### 2026-08-14 — JAI-047 bilingual documentation migration baseline started

- Created `feature/jai-047-bilingual-docs-migration` from synchronized `develop` commit `f07b6d5`; no work started from `main` or an unmerged feature branch.
- Inventory found that `docs/DEVELOPMENT_PLAN.md`, `docs/GITHUB_ISSUES.md`, and the mixed-language `docs/WORKLOG.md` have no independent English/Simplified Chinese pair, while several other repository-authored documents remain legacy single-language files.
- Scope is limited to registering JAI-046 through JAI-048, adding English mirrors for the substantively updated plan and backlog, splitting the active work log without losing history, and synchronizing the bilingual indexes.
- The legacy WORKLOG was copied byte-for-byte to `docs/archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`; source and archive SHA-256 both equal `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`.
- No application code, source adapter, database schema, network collection behavior, or deferred technology is in scope.
- Added reciprocal English/Simplified Chinese mirrors for the development plan, Issue backlog, and active WORKLOG; both documentation indexes now separate paired documents, the immutable archive, and the JAI-048 inventory.
- Structural verification passed: plan headings 45/45, backlog headings 70/70, active-log headings 13/13, index headings 5/5, and identical JAI identifier order in both backlogs.
- Relative-link verification checked 35 Markdown files with no broken links. `git diff --check` passed, and the archive SHA-256 remained unchanged.
- Database-enabled final gate passed: Ruff format checked 94 files, Ruff lint passed, Mypy passed across 56 source files, all 89 tests passed, and coverage was 88.35%.
- The first staged `git diff --cached --check` found four trailing-space lines in the new English plan header. PowerShell continued to the local commit despite that non-zero native-command result; the commit had not been pushed. The four lines were corrected immediately and a separate scoped fix commit was prepared without rewriting history.

### 2026-08-14 — JAI-012 run statistics, manual trigger, and failed-item retry started

- Normally pushed JAI-047 at `b428e43`, merged it into `develop` with non-fast-forward merge `87cd753`, and verified local `develop`, `origin/develop`, and GitHub `ls-remote` all match `87cd7538af5cc3da41a811e1d48051358e6c6977`.
- Created `feature/jai-012-run-stats-retry` from that synchronized `develop`; no work started from `main` or an unmerged feature branch.
- Scope follows the backlog: manual source trigger returning a run ID, readable run summary and failed items, and retry behavior that does not duplicate successful data.
- Before implementation, inspect the existing orchestrator, run repository/model, API/CLI boundaries, source registry, collection documentation, and current tests. Do not add scheduling, parser/extraction work, or deferred source integrations.
- Implemented persisted `CrawlRunSummary` retrieval and tolerant structured failure parsing, including compatibility with pre-JAI-012 failure records that lack a `step` field.
- Extended collection orchestration with idempotent raw-document persistence counters and item-isolated persistence errors. `created`, `updated`, `skipped`, and total `failed` are stored alongside detail-only counters and per-step state.
- Added failed-run retry semantics: require a terminal run, derive URLs only from persisted failures, rediscover the public list to restore metadata, filter to failed URLs, record missing rediscovery safely, and create a new run linked by `retry_of_run_id`.
- Added explicit runtime catalog matching and Adapter wiring for the three active official sources. A database source must match exactly one runnable catalog entry; dynamic imports and arbitrary configured Adapter execution remain prohibited.
- Added `scripts/manage_crawl.py` with synchronous `run`, read-only `show`, and failed-item `retry` commands. The command uses the existing configured PostgreSQL database and low-frequency public-source HTTP policy; no maintenance API or scheduler was added.
- First targeted Ruff check found only `__all__` ordering and test import grouping; both were corrected. The first Mypy run found the script under two module names; adding `scripts/__init__.py` established one importable command package. A second Mypy run exposed narrow JSON-value typing in failure parsing/test setup; explicit checks fixed it without suppressions.
- Targeted verification then passed: Ruff, Mypy across 62 source files, and 23 focused tests including PostgreSQL.
- PostgreSQL acceptance proved: the first run created two documents and recorded one failure; retry rediscovered three items but fetched only the failed URL and created one document; repeating that retry again fetched only the same failed URL, returned `skipped`, and left exactly three raw documents.
- Final review identified that cancellation during raw-document persistence could otherwise leave a run in `running`. The orchestrator now marks the run `cancelled`, records safe progress, and re-raises cancellation; a dedicated unit test covers this path.
- Final database-enabled gate passed: Ruff format checked 100 files, Ruff lint passed, Mypy passed across 62 source files, all 105 tests passed, and coverage was 88.38%.
- Synchronized English/Chinese collection documentation, plan/backlog status, and active WORKLOG. No dependency, schema migration, credential, runtime data, live-source request, or deferred technology was added.
- After transient GitHub port 443 timeouts, normally pushed the feature branch and verified local HEAD, `origin/feature/jai-012-run-stats-retry`, and GitHub `ls-remote` all matched `7e5e888a09ff8bd13094f277631e87d021c27f7a`; no history or remote configuration was rewritten.

### 2026-08-15 — JAI-013 parser protocol and standard intermediate format completed

- Merged JAI-012 into `develop` with non-fast-forward merge `70dd3b2` and normally pushed it; local `develop`, `origin/develop`, and GitHub `ls-remote` all match `70dd3b2144c12aff8e483ec89420ee4486374c2e`.
- Created `feature/jai-013-parser-protocol-intermediate-format` from that synchronized `develop`; no work started from `main` or an unmerged feature branch.
- Scope is limited to MIME-based parser selection, traceable document/table intermediate schemas, parser statuses and error codes, unsupported-format handling, tests, and synchronized documentation. PDF extraction, OCR, Excel table heuristics, and field extraction remain later Issues.
- Added `jobagent.parsers` with immutable source/request contracts, one-based page/line/A1 cell locators, text/table blocks, stable status/error enums, diagnostics, and result invariants. No dependency or schema migration was required.
- Added an explicit registry that normalizes MIME parameters, prevents duplicate parser names/media types, rejects inconsistent source/name output, and returns `unsupported` with `parser.unsupported_media_type` when no parser is registered.
- Added 31 focused tests covering HTML, PDF, XLS/XLSX selection; source and coordinate validation; block/cell traceability; registry conflicts; and unsupported or inconsistent output.
- Added paired English/Chinese parser documentation and index entries, and synchronized the attachment guide, development plan, backlog, and active logs.
- The first unified gate exposed duplicate `test_contracts` module names; making `tests/parsers` a package resolved it. The second gate exposed narrow regex-group typing in the new A1 validator; passing explicit capture groups resolved it without suppression.
- Final PostgreSQL-enabled `scripts/check.py` gate passed: Ruff format checked 108 files, Ruff lint passed, Mypy passed across 68 source files, all 136 tests passed, and coverage was 88.85%.
- Normally pushed JAI-013 and verified local HEAD, `origin/feature/jai-013-parser-protocol-intermediate-format`, and GitHub `ls-remote` all match `269648a384027de772b2fa2c4dd5661cb183594c`.

### 2026-08-16 — JAI-014 PDF text parsing and scan detection completed

- Merged JAI-013 into `develop` with non-fast-forward merge `36d389f` and normally pushed it; local `develop`, `origin/develop`, and GitHub `ls-remote` all match `36d389fbe1edffe5131eba09ea16a21623d0f3d6`.
- Created `feature/jai-014-pdf-text-scan-detection` from that synchronized `develop`; no work started from `main` or an unmerged feature branch.
- Scope is limited to a registered PDF parser, page-level text and metadata, deterministic scan/low-text detection, encrypted/corrupt diagnostics, tests, and synchronized documentation. OCR implementation, Excel parsing, parser-worker persistence, and field extraction remain out of scope.
- Added `PdfTextParser`, `PdfTextPolicy`, and explicit production registry construction. Normal PDFs produce normalized page blocks with one-based evidence; result metadata preserves page counts, character statistics, and non-empty standard PDF metadata.
- Image-only and low-text PDFs return `ocr_required` without running OCR. Encrypted, corrupt, empty/unreadable, and wrong-MIME inputs return stable safe issues instead of leaking third-party exceptions.
- Added 11 PDF tests using the existing real four-page fixture plus generated image-only, low-text, encrypted, and corrupt inputs. All 42 parser tests pass offline without live source access or committed runtime files.
- Synchronized the English/Chinese parsing and attachment documentation, plan, backlog, and active logs. No dependency, database migration, worker, network collector, OCR engine, or Excel behavior was added.
- The first targeted static pass found only formatting/export order plus narrow PyMuPDF and JSON-union typing boundaries; explicit type narrowing and the same limited third-party suppressions already established by the Spike resolved them. Behavior tests passed throughout.
- Docker Desktop and the existing Compose database were initially stopped; starting the existing installation and `db` service restored the existing `jobagent_test` database without rebuilding or deleting data.
- Final PostgreSQL-enabled `scripts/check.py` gate passed: Ruff format checked 111 files, Ruff lint passed, Mypy passed across 71 source files, all 147 tests passed, and coverage was 89.07%.
- Normally pushed JAI-014 and verified local HEAD, `origin/feature/jai-014-pdf-text-scan-detection`, and GitHub `ls-remote` all matched `8964272973ef581ec3cc2ff36425810b7998e22e` at push time. A later pre-merge `ls-remote` retry was reset by the network; no repository state changed.

### 2026-08-16 — JAI-015 Excel position-table parsing started

- Pushed the JAI-014 handoff commit `028bbfb`, verified the local, tracking, and GitHub feature refs matched, then merged it into `develop` with non-fast-forward merge `8f21745` and normally pushed it. Local `develop`, `origin/develop`, and GitHub `ls-remote` all match `8f21745bf0d7f3b0ca6736c3bebe2db86e9fdf86`.
- Created `feature/jai-015-excel-position-table-parsing` from that synchronized `develop`; no work started from `main` or an unmerged feature branch.
- Scope is limited to XLSX worksheets, deterministic header/data-region recognition, blank rows, merged cells, traceable cell/row evidence, review diagnostics, tests, and synchronized documentation. Golden-fixture batch evaluation remains JAI-016; field extraction remains JAI-017.
- The existing `.venv` contains no `openpyxl`, `xlrd`, or `pandas`. JAI-015 will use the minimum declared `openpyxl` dependency for XLSX; legacy XLS will remain explicitly unsupported rather than adding an unproven second parser dependency.
- Added the declared `openpyxl>=3.1,<4` runtime dependency and installed version 3.1.5 into the existing `.venv`; no Python installation, `pandas`, or `xlrd` was downloaded.
- Added `ExcelPositionTableParser`, bounded `ExcelTablePolicy`, XLSX production registration, and `parser.header_not_recognized`. A valid header requires a position label plus another known recruitment label; candidate choice is deterministic.
- Each recognized worksheet emits a `TableBlock` whose cells preserve worksheet/A1 evidence. Blank data rows are skipped but recorded, and values inherited from merged cells point to the full original merged range. Multiple tables remain in workbook order.
- Unrecognized or header-only worksheets carry `review_required=true`. If another worksheet parses, these remain issues on a `parsed` result; if no worksheet parses, the result is `failed`. This reuses the persisted status vocabulary until JAI-020 instead of adding an unplanned database state.
- Legacy XLS is not registered because the environment has no existing XLS dependency and JAI-015 has no representative XLS fixture. Registry dispatch returns explicit `unsupported`; JAI-016 can supply evidence for a later dependency choice.
- Added eight XLSX tests covering Chinese/English and two-level merged headers, multiple worksheets, blank rows, vertical merged cells, cell/range evidence, review diagnostics, corrupt/wrong inputs, policy validation, and XLS registry behavior. The initial targeted pass found only export ordering, JSON-union narrowing, date normalization, and the existing PDF registry expectation; all were corrected and 50 parser tests passed.
- Synchronized the English/Chinese parsing docs, plan, backlog acceptance, and active work logs. Final PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 113 files, Ruff lint passed, Mypy passed across 73 source files, all 155 tests passed, and coverage was 89.51%.
- Final documentation verification found no broken relative links across 37 Markdown files; heading counts match across the four modified bilingual pairs, the two backlogs preserve the same 161 Issue-ID occurrences in order, and `git diff --check` passed.
- Normally pushed JAI-015 and verified local HEAD, `origin/feature/jai-015-excel-position-table-parsing`, and GitHub `ls-remote` all match `7a5f3a3d29d7bb40459dbaa10fb30ce6c2835f5b`.

### 2026-08-16 — JAI-016 attachment golden samples and regression started

- Pushed the JAI-015 handoff commit `633ebc1`, verified the local, tracking, and GitHub feature refs matched, then merged it into `develop` with non-fast-forward merge `fca197d` and normally pushed it. Local `develop`, `origin/develop`, and GitHub `ls-remote` all match `fca197de89634517a0aac6fbd84f1e63cc5573f0`.
- Created `feature/jai-016-attachment-golden-samples-regression` from that synchronized `develop`; no work started from `main` or an unmerged feature branch.
- Scope is limited to at least ten sanitized PDF/XLSX fixtures, committed expected intermediate output, an offline batch evaluator, regression tests, and synchronized documentation. Parser feature expansion and field extraction remain out of scope.
- Added five synthetic PDF and five synthetic XLSX fixtures covering multiple pages, sparse/blank text, Chinese/English headers, multiple worksheets, merged cells, blank rows, three date representations, and unrecognized-header review. They contain no downloaded source material or real personal data.
- Added a reviewed `manifest.json` with complete normalized text/table blocks and page/A1 evidence. `serialize_parse_result()` excludes unstable source IDs and library metadata while retaining behaviorally relevant parser output.
- Added `evaluate_golden_fixtures()`, a stable aggregate/difference report, and `scripts/evaluate_attachment_fixtures.py`. The evaluator uses the production registry, performs no network access, reports total/matched/success rate plus full per-case expected/actual differences, and exits non-zero on regression.
- Kept a separate explicit generator so synthetic binary provenance is reviewable; normal regression tests never regenerate or silently approve snapshots. Added tests proving all ten committed fixtures match and a tampered expectation produces one detailed difference and a 90% success rate.
- Added separate English/Chinese fixture guides and updated both documentation indexes, parsing docs, plan, backlog acceptance, and active logs.
- Final offline evaluator result was 10/10 with 100% success and no differences. PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 119 files, Ruff lint passed, Mypy passed across 77 source files, all 157 tests passed, and coverage was 89.30%.
- Final documentation verification found no broken relative links across 39 Markdown files; heading counts match across all six modified bilingual pairs, both backlogs preserve the same 161 Issue-ID occurrences in order, and `git diff --check` passed.
- Normally pushed JAI-016 and verified local HEAD, `origin/feature/jai-016-attachment-golden-samples-regression`, and GitHub `ls-remote` all matched `819c63fa00d31225ad65723605e91c0b8366bc2d` at push time. A later pre-merge `ls-remote` retry timed out on GitHub port 443; no repository state changed.
- Pushed the JAI-016 handoff commit `7bb600e`, merged the verified feature branch into `develop` with non-fast-forward merge `76ecd4b`, and normally pushed it after a temporary GitHub 443 outage. Local `develop`, `origin/develop`, and GitHub `ls-remote` all matched `76ecd4b8bd087a277b4cc0ecc55135f0e11ae86d`; JAI-016 is its ancestor and the worktree was clean.

### 2026-08-22 — JAI-017 deterministic field extraction and normalization started

- Verified a clean `develop` at `1dc7a100d7dfb8b17ac33a2d03ee2255e4500b65`; local `develop`, `origin/develop`, and GitHub `ls-remote` matched, and JAI-016 feature commit `05bac9cf4fba48330fbab3424535a90422b17a4b` is merged.
- Verified repository-local authorship as `user9527448 <2537759248@qq.com>` and retained the existing HTTPS origin.
- Created `feature/jai-017-deterministic-field-extraction` from the synchronized `develop` head.
- Scope is limited to deterministic dates/timezones, region dictionary matching, URLs, headcount, education/enums, and outputs that retain raw values, normalized values, and source evidence. LLM providers/prompts/budgets, body/attachment merging, and database `field_evidence` persistence remain JAI-018/JAI-019.
- Next: inspect the parser intermediate contracts and golden fixtures, define the extraction contract, then implement focused tests before the full quality gate.
- Added `jobagent.extraction` contracts, bounded region/education/category dictionaries, and deterministic text/table rules. Date-only boundaries use the configured local day and all date-times normalize to UTC; invalid/inverted dates remain evidenced diagnostics.
- Added 16 focused tests, including real parsing of the committed XLSX golden fixtures with `YYYY-MM-DD`, `YYYY/MM/DD`, and `YYYY年M月D日` dates, explicit/default timezone handling, application URL normalization, unsupported-value diagnostics, and no-evidence/no-label behavior.
- Added paired English/Chinese extraction documentation and both documentation-index entries. No dependency, configuration field, database migration, LLM behavior, body/attachment merge, persistence code, OCR, credential, personal data, runtime data, or live-source request was added.
- The complete `scripts/check.py` gate passed: Ruff format checked 128 files, Ruff lint passed, Mypy passed across 84 source files, 166 tests passed, 7 PostgreSQL-only tests were skipped because Docker was not running, and coverage was 85.27%. This Issue has no database or migration change; the Docker limitation is recorded rather than treating skipped checks as passed.
- Documentation verification passed: plans have 45/45 headings, backlogs 70/70, the new extraction pair 6/6, active logs 28/28, and indexes 5/5; both backlogs preserve the same 161 Issue-ID occurrences in order, all Markdown relative links resolve, and `git diff --check` passed.
- Created feature commit `c1da6cec5969cdb40952fd2c0205b5ce196f6554` with repository-local author `user9527448 <2537759248@qq.com>`; the worktree was clean immediately after the commit.
- Two normal HTTPS push attempts and one read-only `git ls-remote` check each failed after about 21 seconds because GitHub port 443 was unreachable. No remote URL, protocol, branch history, or commit was changed; retry the same non-force push after connectivity recovers.
- The third identical normal push succeeded, created the remote JAI-017 branch, and established its tracking reference. Local HEAD and `origin/feature/jai-017-deterministic-field-extraction` both matched `c1da6cec5969cdb40952fd2c0205b5ce196f6554`; the immediate `ls-remote` verification then hit another port 443 connection failure, so final three-way verification remains required after the handoff-log commit.
- Normally pushed recovery-log commit `35f657e62f557182fc1af3590a820177a7e1a185`; after one more transient `ls-remote` failure, local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit. This final status-only log update closes the JAI-017 feature handoff; no merge to `develop` was performed.

### 2026-08-22 — JAI-018 replaceable LLM extraction service started

- Merged the verified JAI-017 feature branch into `develop` with non-fast-forward merge `c7a2ebe1082588257fd0353c04c650a698fd6e06` and normally pushed it after transient GitHub port 443 failures. Local `develop`, `origin/develop`, and GitHub `ls-remote` all match that commit, and JAI-017 is its ancestor.
- Created `feature/jai-018-replaceable-llm-extraction` from the synchronized `develop` head with repository-local author `user9527448 <2537759248@qq.com>` unchanged.
- Scope is limited to a configurable provider boundary, strict JSON Schema output validation, prompt versioning, timeout/retry behavior, token/cost call records, test doubles, and daily-budget queueing. Body/attachment result merging and database `field_evidence` persistence remain JAI-019.
- Next: define the in-memory contracts and provider adapter, implement focused mock-transport tests, then synchronize bilingual documentation and run the proportional quality gates.
- Added strict Pydantic candidate/payload contracts, single-source parser fragments, a provider-neutral protocol, and an `OpenAIResponsesProvider` built on the existing `httpx` dependency. The adapter sends strict `text.format` JSON Schema, parses output and usage defensively, classifies retryable failures, and never exposes provider response bodies or API keys.
- Added `LlmExtractionService` with explicit Prompt versioning, verbatim raw-value/quote/source-fragment validation, bounded exponential backoff, per-request model/Prompt/token/cost/status records, concurrency-safe maximum-cost reservations, and a pending queue when the daily budget would be crossed. Invalid output retains usage/cost metadata but exposes no candidate payload and cannot write business tables.
- Kept call records and pending tasks behind protocols with process-local defaults. No database migration, `field_evidence` persistence, body/attachment merging, precedence, conflict resolution, live provider request, new SDK dependency, credential, or provider pricing/model hard-code was added.
- Added 12 provider/contract tests and 7 service tests using scripted providers and `httpx.MockTransport`. The first full test run had 181 passes and 7 PostgreSQL skips but failed the unchanged 85% coverage gate at 84.90%; focused error/configuration tests raised coverage. A later combined run passed Pytest at 85.58% but exposed one Mypy-only dynamic test-dictionary type error, which was replaced with explicit typed parameters.
- Final `scripts/check.py` passed: Ruff format checked 136 files, Ruff lint passed, Mypy passed across 90 source files, 189 tests passed, 7 PostgreSQL-only tests were skipped because Docker was not running, and coverage was 85.58%. JAI-018 adds no database or migration behavior, so the environment limitation is recorded rather than treating skipped checks as passed.
- Documentation verification passed across 42 Markdown files with no broken relative links. Paired heading counts match for plans (45/45), backlogs (70/70), active logs (29/29), indexes (5/5), and the new LLM guide (6/6); both backlogs retain the same 161 Issue IDs in order, and `git diff --check` passed.
- Created implementation commit `d70b8a98fdc70fd65e9754451e563d33c5cd7336` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed it to the new tracking branch. The immediate `ls-remote` check hit one transient GitHub port 443 connection failure; a retry succeeded, and local HEAD, the tracking reference, and GitHub all matched `d70b8a98fdc70fd65e9754451e563d33c5cd7336` before this status-only handoff update.
- After the user started Docker Desktop, started the repository's existing `db` Compose service without rebuilding or deleting its volume. The service became healthy and the isolated `jobagent_test` database already existed. With `JOBAGENT_TEST_DATABASE_URL` targeting that `_test` database, the complete `scripts/check.py` gate passed again: Ruff format checked 136 files, Ruff lint passed, Mypy passed across 90 source files, all 196 tests including the seven PostgreSQL integration tests passed with no skips, and coverage was 88.64%.
- Created PostgreSQL verification commit `0aa57178e962b81d355d8edd7a0a927a8f77690e`. Three normal push attempts and two read-only `ls-remote` probes then failed because GitHub port 443 remained unreachable, including after a 15-second backoff. The worktree and published history were not changed; the local feature branch remains safely ahead of its tracking branch and must be normally pushed when HTTPS connectivity recovers.
- A system TCP probe later confirmed GitHub port 443 was reachable. The unchanged normal HTTPS push then advanced the remote feature branch through outage-log commit `ccc64a14bcd59df7d8d1677906e55f0ad9739705`; after one more transient read failure, a second TCP probe and `ls-remote` confirmed local HEAD, the tracking reference, and GitHub all matched that commit before this final status-only update.

### 2026-08-23 — JAI-019 field evidence merging and persistence started

- Reverified the clean JAI-018 feature branch at `3da9ccad55aeb9eb0962f220e3c500288208ed93` and `develop` at `c7a2ebe1082588257fd0353c04c650a698fd6e06`; local, tracking, and GitHub refs matched after transient port 443 failures.
- Merged JAI-018 into `develop` with non-fast-forward merge `c013544f3339efd776121c6792978f83d958062f`, normally pushed it, and verified local `develop`, `origin/develop`, and GitHub `ls-remote` all match. Repository-local authorship remains `user9527448 <2537759248@qq.com>`.
- Created `feature/jai-019-field-evidence-merging` from the synchronized `develop` head.
- Scope is limited to deterministic body/attachment precedence, explicit conflict retention, confidence and extraction-version metadata, `job_posts`/`job_positions` materialization, and durable `field_evidence`. JAI-020 validation/review/reparse APIs and all later source integration remain out of scope.
- Next: define merge and persistence contracts against the existing extraction models and PostgreSQL schema, add the minimal migration needed for versioned history, then implement unit and database acceptance tests before the complete gate.
- Added `ExtractionMergeInput`, LLM fragment binding, deterministic field-target precedence, semantic validation of LLM values, stable candidate deduplication, explicit losing conflict evidence, partial position records, and a SHA-256 merged-result hash. Rule evidence uses confidence 1.0000 and LLM method confidence 0.6000; no model self-score is trusted.
- Announcement fields prefer deterministic body evidence while position fields prefer deterministic attachment evidence; deterministic candidates always precede LLM candidates. All contradictory normalized values and exact coordinates remain queryable. Position rows from different sources remain separate when no evidenced identity can prove they are the same; no placeholder name is invented.
- Added migration `0004_versioned_field_evidence`: version/hash/current/supersedes metadata and per-version uniqueness for `job_posts`; stable record keys and nullable evidenced names for `job_positions`; raw/normalized values, method/version, selection/conflict flags, and page/line/sheet/cell coordinates for `field_evidence`. Existing rows are backfilled as `legacy-v1`.
- Added `SqlAlchemyExtractionRepository` with a per-document advisory lock, attachment-parent validation, atomic post/position/evidence writes, unchanged reuse for identical version/hash, rejection of same-version hash drift, and append-only new versions that retain prior entities and evidence.
- Added five merge unit tests, one PostgreSQL repository acceptance test, and one legacy-data migration test. They cover body/attachment conflicts, deterministic-over-LLM precedence, invalid LLM semantics, input-order-independent hashes, position/evidence coordinates, idempotent reruns, version chains, history retention, empty-schema upgrade/check/downgrade, and 0003 data backfill.
- During an early migration run Docker Desktop stopped and two repeated Pytest invocations remained waiting for the same test schema. Confirmed their command lines, terminated only those test processes, relaunched the registered Docker Desktop app, restarted the existing `db` service without rebuilding/deleting its volume, and reran each database test singly before the complete gate.
- The first complete PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 141 files, Ruff lint passed, Mypy passed across 94 source files, all 203 tests passed with no skips, and coverage was 88.07%.
- Added paired English/Chinese merge/evidence documentation and index entries, and synchronized database docs, plans, backlog acceptance, and active logs. Documentation verification found no broken relative links across 44 Markdown files; heading counts match for plans (45/45), backlogs (70/70), logs (30/30), indexes (5/5), database docs (6/6), and the new guide (6/6); both backlogs retain the same 161 Issue IDs in order, and `git diff --check` passed.
- A post-documentation gate first ran without `JOBAGENT_TEST_DATABASE_URL`: 194 tests passed, nine PostgreSQL tests were skipped, and coverage fell to 83.51%, so the gate correctly failed. After supplying the repository-documented test database URL, the final `scripts/check.py` passed with Ruff format over 143 files, Ruff lint, Mypy across 94 source files, all 203 tests with no skips, and 88.07% coverage.
- No JAI-020 validation severity, review state, recommendation eligibility, correction workflow, or reparse command/API was added. No live source/provider request, credential, personal data, downloaded file, or runtime data was committed.
- Created JAI-019 feature commit `a2c41fee65bfcbf0374af96f5b028ab40bf565a6` with the verified repository-local author. Three normal HTTPS push attempts failed at the network layer (two GitHub port 443 connection timeouts and one connection reset), including retries after TCP probes temporarily reported recovery. No remote, protocol, published history, or commit author was changed; the local feature commit remains safe and must be normally pushed when connectivity recovers.
- After another bounded backoff and successful TCP probe, the unchanged normal HTTPS push published the feature and blocker-log commits through `a7d5e17f44832acc774e86752be0421fdacb3adc`. A later recovered `ls-remote` confirmed local HEAD, the tracking reference, and GitHub all matched that commit before this final status-only update; GitHub `develop` remained at `c013544f3339efd776121c6792978f83d958062f`.

### 2026-08-25 — JAI-020 validation, review, and reparsing started

- Recovered GitHub connectivity and normally pushed the final JAI-019 handoff commit. Local HEAD, the tracking reference, and GitHub `ls-remote` all matched `01417b89256f8730f78317c17bb1101ed3707818`.
- Merged JAI-019 into `develop` with non-fast-forward merge `82797d1fa91b1f5e77296d04e3138a9fabe7b499`, normally pushed after one transient port 443 timeout, and verified local `develop`, `origin/develop`, and GitHub `ls-remote` all match. Repository-local authorship remains `user9527448 <2537759248@qq.com>`.
- Created `feature/jai-020-validation-review-reparse` from the synchronized `develop` head. JAI-020 is the next incomplete Issue in both backlogs.
- Scope is limited to required-field, temporal, URL, enum, and conflict validation; recorded reason/severity; review and automatic-recommendation eligibility; and an idempotent command/API for reparsing a specified document after rule correction. New source integration, scoring/matching, OCR, scheduler expansion, and bypassing source restrictions remain out of scope.
- Next: inspect the JAI-019 versioned entities and existing CLI/API patterns, define the minimum validation/reparse contracts and persistence changes, then implement focused unit/database/API tests before the complete PostgreSQL-enabled gate.
- Added deterministic `ExtractionValidator` findings with stable issue keys, warning/error severity, derived `approved`/`review_required`/`blocked` state, and automatic-recommendation eligibility. Missing critical fields, invalid dates/URLs/enums, and severe conflicts block recommendations; noncritical incompleteness/conflicts remain review warnings without guessed values.
- Added migration `0005_validation_review_reparse`: `job_posts` now stores validation/review metadata, while `validation_issues` stores version-specific safe reasons and severity under restricted foreign keys. Legacy posts are backfilled as `review_required`, ineligible, and `legacy-unvalidated`.
- Extended `SqlAlchemyExtractionRepository` so validation and issue rows are written atomically with every new extraction version; idempotent repeats reuse the same entities and counts. Added `StoredDocumentReparsePipeline`, shared `ReparseService`, `POST /extraction/documents/{document_id}/reparse`, and `scripts/manage_extraction.py reparse` with explicit safe version identifiers.
- Reparse uses stored `raw_text` or sanitized text from stored HTML and verifies every persisted attachment path, size, and SHA-256 before parsing. Missing/unparseable attachments fail explicitly. The default pipeline performs deterministic parsing/extraction/merging only and makes no source or LLM request.
- Static checks passed across 102 source files, and 11 focused validation/API/command tests passed. Docker Desktop was not running, so the installed application and existing `db` Compose service were started without rebuilding or deleting volumes; `jobagent_test` was healthy.
- The first PostgreSQL set had one pass and three failures: two Alembic drift failures exposed validation constraints accidentally attached to `raw_documents`, and one repository expectation used obsolete hand-built `CN-11`/`CN-31` values instead of the current `beijing`/`shanghai` dictionary. The constraints were moved to `job_posts` and tests aligned to the production dictionary without weakening validation; all four migration/repository/reparse database tests then passed.
- The first complete PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 152 files, Ruff lint passed, Mypy passed across 102 source files, all 215 tests passed with no skips, and coverage was 88.06%.
- Added paired validation/reparse documentation and index entries, synchronized database docs, plans, backlog acceptance, and active logs. No source 4/5 integration, matching/scoring, OCR, scheduling, manual value-editing/approval API, credentials, personal data, downloaded source file, or runtime data was added.
- Documentation verification found no broken relative links across 46 repository Markdown files; heading counts match for plans (45/45), backlogs (70/70), logs (33/33), indexes (5/5), database docs (6/6), and the new guide (7/7). Both backlogs retain the same 161 Issue IDs in order and `git diff --check` passed. The first repository-wide link-check command had a PowerShell variable-interpolation syntax error; the corrected read-only command passed without changing files.
- The malformed-URL defense test passed, while its first combined static command reported Ruff `B018` for accessing `parsed.port` only to trigger validation. The expression was changed to an explicit checked assignment; no suppression was added.
- The final PostgreSQL-enabled `scripts/check.py` passed after all documentation and defensive tests: Ruff format checked 154 files, Ruff lint passed, Mypy passed across 102 source files, all 216 tests passed with no skips, and coverage was 88.07%.
- Created feature commit `67120101ea0c926f327b781a6e69c05350d41df7` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed the new feature branch. Local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit before this final status-only update; GitHub `develop` remained at `82797d1fa91b1f5e77296d04e3138a9fabe7b499`.

### 2026-08-29 — JAI-022 single-user preferences started in parallel

- Verified JAI-020 is merged: local `develop`, `origin/develop`, and GitHub `ls-remote` all matched non-fast-forward merge `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`, whose second parent is JAI-020 feature tip `9c86cad8eb621b20fa70e1e6a07a377f929608a3`.
- The user explicitly approved one bounded WIP exception while JAI-021 waits only for calendar-day observations. Created `feature/jai-022-single-user-preferences` directly from verified `develop`; `git log` ancestry therefore contains no unmerged JAI-021 commit.
- Merge boundary is fixed: JAI-021 continues only on its own branch and must complete/merge first. Then normally merge the latest `develop` into JAI-022, preserve both bilingual WORKLOG histories, resolve any documentation conflict explicitly, and rerun the complete PostgreSQL-enabled gate. Never rebase or rewrite published history.
- JAI-022 scope remains limited to one structured user preference model and read/update API for regions, education, majors, job keywords, organization types, and exclusions; validation, update timestamps, recalculation signaling, and a non-filtering default are required. JAI-023 scoring/filtering remains out of scope.
- Next action: inspect existing models, migrations, API conventions, and tests; define the smallest preference contract and persistence boundary before implementation.

### 2026-08-30 — JAI-022 implementation and feature-branch acceptance completed

- Added migration `0006_single_user_preferences` and an ORM singleton constrained to `id=1`. The migration inserts a non-filtering default: empty region/major/keyword/organization/exclusion arrays, `education=null`, and no pending recomputation. JSON array shape and education values are database-constrained.
- Added `GET /preferences` and full-replacement `PUT /preferences`. Region and education values reuse deterministic extraction enums; organization type intentionally uses the separate `government`/`public_institution`/`state_owned`/`private`/`foreign_enterprise` vocabulary rather than confusing source category with employer type. Text is NFKC/whitespace normalized and deduplicated in stable order.
- Updates lock the singleton row and store `updated_at`. `trigger_recompute=true` sets a sticky pending flag and request timestamp; a deferred update cannot erase an existing request. JAI-023 owns signal consumption, hard filtering, scoring, and recomputation execution and remains unimplemented here.
- Added API/model/migration/repository/enum-alignment tests and paired preference/database/index/plan/backlog/log documentation. The first focused repository run failed only because the new Windows test used the default Proactor event loop, which psycopg async rejects; it was corrected to the repository-standard `asyncio.SelectorEventLoop`, after which all three focused PostgreSQL tests passed. The first enum-test Mypy/full-gate attempt exposed the duplicate bare module name `test_contracts`; renaming it to `test_preference_contracts` fixed package discovery without changing assertions.
- Docker Desktop and the existing `db` service were started without rebuilding or deleting volumes; the existing isolated `jobagent_test` database was confirmed. Final `scripts/check.py` passed: Ruff format checked 164 files, Ruff lint passed, Mypy passed across 109 source files, all 224 tests passed with no skips, and coverage was 88.18%.
- Created feature commit `38cca14` with repository-local author `user9527448 <2537759248@qq.com>`. Two normal push attempts failed without updating the remote: the first connection was reset and the second timed out on GitHub port 443. A read-only `ls-remote` timed out as well; DNS still resolved `github.com` to `20.205.243.166`, no Git proxy was configured, and a direct TCP 443 probe failed. The local commit and branch remain intact and no force/rebase action was used.
- A continuation retry at 2026-08-30 01:27 +08:00 also timed out on GitHub 443. Read-only diagnostics found no `HTTP_PROXY`/`HTTPS_PROXY` environment setting, WinHTTP uses direct access, Windows user proxy is disabled, and no common local proxy port was listening. The current date is still JAI-021 qualified Day 2; Day 3 cannot truthfully run before 2026-08-31.
- The later normal push succeeded. Local HEAD, the tracking reference, and GitHub `ls-remote` all matched `e8e29610bfe3d84051b75defa83adcb8c72a9ad3`; GitHub `develop` remained unchanged at `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`.
- Next action: after JAI-021 completes and merges first, normally merge updated `develop` into this branch, preserve both bilingual logs, resolve paired-document conflicts, rerun the full PostgreSQL gate, and only then merge JAI-022.

### 2026-08-30 — JAI-023 hard filters and versioned rule scoring started in parallel

- The user explicitly approved continuing JAI-021 acceptance observation and downstream development in parallel, provided the dependency and merge boundaries remain documented and safe.
- Verified `feature/jai-023-hard-filter-versioned-scoring` at `44ed50292aa6609c7c4eaa1fb16e0793082d4e0a`; its HEAD and merge base with the published JAI-022 tip are identical. Repository-local authorship remains `user9527448 <2537759248@qq.com>` and the existing HTTPS origin is unchanged.
- Merge order is fixed: JAI-021 → `develop`; updated `develop` → JAI-022 and then merge JAI-022; newly updated `develop` → JAI-023. Preserve all bilingual WORKLOG history, resolve conflicts explicitly, rerun the complete PostgreSQL gate, and never rebase or rewrite published history.
- Scope is limited to education/deadline/exclusion hard filters; region/job direction/major/organization/urgency/completeness component scores; deterministic score versions; persisted rule/input/score/explanation components; and full recomputation triggered by the JAI-022 preference signal.
- JAI-024 report queries, rendering, snapshots, and notifications remain out of scope.
- Next action: inspect the JAI-022 preference contract and current job entities, then add the smallest matching contract, migration, deterministic engine, recomputation repository, and boundary tests.
- Added pure `DeterministicMatchingEngine` version `jai-023-v1`: explicit validation/education/deadline/exclusion decisions and fixed region 25, direction 30, major 15, organization 10, urgency 10, and completeness 10 components. Canonical UTC JSON produces separate input, preference, and result SHA-256 identities.
- Added migration `0007_versioned_match_results`, ORM history/current relationships, JSONB rule/component explanations, calculation uniqueness, score/hash checks, and restricted position/preference/self-history foreign keys.
- Added `SqlAlchemyMatchingService.recompute_if_requested()`. It locks the singleton preference, evaluates every position on current post versions in stable ID order, appends/supersedes results, and clears the sticky signal only when the complete transaction commits; signal acknowledgement does not change the preference-value update time.
- Employer type is derived only for direct category semantics (`civil_service`, `public_institution`, `state_owned`); `campus` and `social` remain unknown. No organization type, deadline, education, or missing value is guessed.
- Added 16 engine boundary tests and a PostgreSQL full-recomputation acceptance test. The first implementation gate passed before final documentation: Ruff format checked 172 files, Ruff lint passed, Mypy passed across 116 source files, all 241 tests passed without skips, and coverage was 88.47%.
- Added paired matching documentation and synchronized the database/preference guides and both indexes. Documentation verification passed: paired heading counts match, both backlogs retain the same 171 Issue identifiers in order, repository Markdown relative links resolve, and `git diff --check` passed.
- The final post-documentation `scripts/check.py` gate passed: Ruff format checked 174 files, Ruff lint passed, Mypy passed across 116 source files, all 241 tests passed with no skips, and coverage was 88.47%.
- No JAI-024 report query, grouping, rendering, snapshot, notification, scheduler, LLM reranking, embedding, public matching API, credential, personal data, downloaded source, or runtime data was added.
- Next action: commit and normally push this dedicated feature branch, verify local/tracking/GitHub refs, then wait for the recorded JAI-021/JAI-022 integration sequence before synchronizing from `develop`.
- Created feature commit `8a334e5` with repository-local author `user9527448 <2537759248@qq.com>`. The first normal HTTPS push failed after about 21 seconds because GitHub port 443 was unreachable; a read-only `ls-remote` failed the same way and a TCP probe resolved `github.com` to `20.205.243.166` but reported port 443 closed. No remote branch, protocol, history, or author was changed; retry the same non-force push when connectivity recovers.
- The later unchanged normal push succeeded. Local HEAD, the tracking reference, and GitHub `ls-remote` all matched blocker-record tip `18cdc97c16cc02fbb2cdd6383258c811bd062cea`; `develop`, JAI-021, and JAI-022 remained unchanged and isolated.

### 2026-09-03 — JAI-024 daily report query and rendering started in parallel

- Verified JAI-024 is the next incomplete planned Issue after JAI-023 and depends only on JAI-023. Created `feature/jai-024-daily-report-rendering` in isolated worktree `data/worktrees/jai024` from published JAI-023 tip `9592a16d7dee12fbe6c555407a3607a492b2cd03`; its merge base with JAI-023 is identical.
- Scope is limited to four action-oriented groups—priority applications, closing soon, added today, and needs confirmation—stable same-input/day ordering, Markdown/HTML rendering, report snapshots, and original-source links. JAI-025 quality review, JAI-026 scheduling, JAI-027 notification delivery, and all credential/channel behavior remain out of scope.
- Integration boundary is explicit: JAI-021 merges first, then JAI-022, JAI-023, and finally JAI-024. Each branch will normally merge the latest `develop`, preserve both WORKLOG histories, resolve paired-document conflicts, and rerun the full PostgreSQL-enabled gate before integration.
- Added pure report version `jai-024-v1`. The explicit report date and timezone define local-day windows without reading the process clock. Current hard-filter-passing matches enter stable, independently sorted priority (score at least 70), closing-within-seven-days, and added-today sections; review-required or evidence-incomplete records enter needs-confirmation. A position may appear in multiple action sections, and missing fields are displayed as missing rather than guessed.
- Added deterministic Chinese Markdown and escaped standalone HTML renderers. Every item carries organization, title, region, deadline, rule reason, evidence-derived risks, score, and its original-source link; all four sections remain present and explicitly state when empty.
- Added migration `0008_daily_report_snapshots`, the matching ORM model, canonical input/content SHA-256 identities, and an idempotent SQLAlchemy service. Identical date/timezone/version/input reuses the immutable snapshot and differing output under the same identity fails explicitly. Added generation, structured lookup, Markdown, and HTML API endpoints without scheduler or delivery behavior.
- Added builder/render/API/model/migration/PostgreSQL service tests and paired report/database/index documentation. Initial static work exposed Ruff ambiguity/import/performance findings and a Pydantic recursion error from using the recursive JSON alias as a response field; the code was corrected without suppressions, and the API now exposes the same structured object through a nonrecursive response annotation.
- The database-free gate passed Ruff format for 187 files, Ruff lint, and Mypy for 126 source files. The first complete-gate attempt executed 238 tests successfully and skipped the 13 PostgreSQL tests because `JOBAGENT_TEST_DATABASE_URL` was unavailable; expectedly, coverage was 81.58%, below the 85% threshold, so `scripts/check.py` remains failed rather than being reported as acceptance. A later explicit Asia/Shanghai local-midnight and seven-day right-boundary test brought the passing non-database set to 239.
- Docker Desktop 4.85.0 was present but its backend crashed before starting any engine. Logs first identified inaccessible Windows Unix-socket reparse points. The volatile `C:\Users\benbenhu\AppData\Local\Docker\run` and `C:\Users\benbenhu\AppData\Local\docker-secrets-engine` directories were renamed to timestamped `.stale-20260903-*` backups and Docker was restarted; no image, volume, project data, or configuration was deleted. A newly recreated `dockerInference` socket failed identically, proving the remaining blocker is the Docker Desktop/Windows runtime rather than stale project state. Port 5432 remains closed and no standalone local PostgreSQL service exists.
- JAI-024 is not marked complete, its acceptance boxes remain open, and the implementation is not committed or pushed. JAI-025 scoring review, JAI-026 scheduling/locks, and JAI-027 notification/channel logic remain out of scope.
- After Windows restarted, Docker Desktop 4.85.0 and the existing PostgreSQL container recovered without a factory reset; the database became healthy on port 5432. The first focused PostgreSQL run passed the migration/model checks but failed one report-service assertion because the test assumed the persisted human-confirmation reason was always the first risk, while the documented deterministic order places review status first. The assertion was corrected to require that reason anywhere in the retained risk set; production ordering and acceptance were not weakened.
- The corrected focused PostgreSQL migration/model/report-service set passed 7/7. The first complete-gate invocation then stopped at Ruff format because that corrected generator assertion required canonical one-line formatting; `ruff format` made only that mechanical change.
- Final PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 187 files, Ruff lint passed, Mypy passed across 126 source files, all 252 tests passed with no skips, and coverage was 88.53%. Paired JAI-024 acceptance is complete without implementing JAI-025, JAI-026, or JAI-027 behavior.
- Created scoped feature commit `ffa065f2877c833b5b98e48640a61aa891a0bb4f` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed the new branch. Local HEAD, its tracking reference, and GitHub `ls-remote` all matched that commit before this status-only record; no force push, rebase, remote change, or published-history rewrite occurred.
- Created paired acceptance/push status commit `1e60ee9`. Its first normal push and one unchanged retry failed because GitHub port 443 was unreachable; the direct TCP probe returned false and `ls-remote` failed identically. The published feature tip remains safely at `ffa065f`, the local branch is ahead only by status documentation, and no remote state or history was rewritten.
- Read-only diagnosis then found that Windows had an active local proxy at `127.0.0.1:7892`, while Git had no repository/global proxy and was attempting the failed direct route. A one-command `http.proxy` override used that already-running user proxy without persisting configuration or changing the HTTPS origin. The normal push succeeded, and local HEAD, the tracking reference, and GitHub `ls-remote` all matched `b1724881668540e6ec18b684079387c33d977b66` before this final status-only record.
- Next: keep JAI-024 isolated and unchanged until JAI-021, JAI-022, and JAI-023 integrate in order; then normally merge the latest `develop` into JAI-024, preserve both logs, resolve paired-document conflicts explicitly, and rerun the complete PostgreSQL gate before integration.

### 2026-08-26 — JAI-021 sources 4–5 and three-day stability started

- Reverified the clean JAI-020 feature branch at `9c86cad8eb621b20fa70e1e6a07a377f929608a3`; its local HEAD, tracking reference, and GitHub reference matched, and repository-local authorship remained `user9527448 <2537759248@qq.com>`.
- Merged JAI-020 into `develop` with non-fast-forward merge `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`, normally pushed it, and verified local `develop`, `origin/develop`, and GitHub `ls-remote` all match that commit.
- Confirmed JAI-021 is the next incomplete Issue in both language plans and backlogs, then created `feature/jai-021-sources-four-five-stability` from the synchronized `develop` head.
- Scope is limited to adding sources 4 and 5, bringing all five sources under Adapter contract tests, and recording success, duplicate, and core-field completeness metrics on three consecutive calendar days. Preferred sources are the National College Student Employment Service Platform and Shanghai public-institution announcements; only stable, public, read-only official endpoints may be used.
- Dynamic pages that require login, CAPTCHA, application-system access, browser automation, or access-control evasion will be marked blocked or replaced by a stable endpoint owned by the same official body. No JAI-022 matching/preferences or later scheduling and operations features will be added.
- The three-day acceptance period cannot be pre-recorded. Next: inspect the current catalog and Adapter contracts, verify official public endpoints, implement offline fixtures/contracts and proportional tests, then record day 1 only after a real bounded run succeeds.
- Verified the official public boundary with low-frequency reads. NCSS exposes the same unauthenticated GET list used by its public page plus public details; login prompts belong only to application actions and are never invoked. Shanghai exposes a narrower public-institution column; the Adapter accepts only recruitment paths and excludes proposed-hire notices.
- Added `NcssJobsAdapter` and `ShanghaiPublicInstitutionAdapter`, explicit manual/preview runtime wiring, active catalog entries, and three hand-authored synthetic detail contracts per source. No downloaded page, credential, applicant data, or runtime output was committed.
- Added bounded JSON-only daily evaluation for source-run/detail success, canonical-URL/content-fingerprint duplicates, and evidence-backed organization/title/region/deadline/source-link completeness. It uses concurrency 1, the shared pacing/retry policy, at most 1-10 details per source, and performs no database/file write.
- Extended deterministic dates only for directly evidenced official-notice formats: colon or `为`, a value on the next line, and a single explicit deadline after `即日起`/`自公告发布之日起`. The relative start remains absent. Shanghai organization is taken only from the exact title before a fixed recruitment suffix, with that title retained as evidence.
- The first 2026-08-26 all-source observation is not a qualified stability day: SASAC exhausted three retries with retryable `PoolTimeout`; four of five source runs and all 8 attempted details succeeded, duplicate rate was 0%, and pre-correction completeness was 55%. Diagnostic reruns showed NCSS 80%, Jiangsu 60%, and corrected Shanghai 100%; the comparable post-correction composite is 82.5%, not one all-source run.
- Registered JAI-049 as the explicit remediation Issue required by JAI-021 acceptance. It forbids treating publication time as deadline or publisher as hiring organization and must close the evidence-backed gap before the MVP release gate; JAI-022 remains the next main-line feature after JAI-021.
- Focused Adapter/extraction/stability tests passed, and the PostgreSQL JAI-021 acceptance passed: six synthetic source-4/5 documents were `created` on the first write, `unchanged` on the second, and remained six version-1 rows. The first database invocation used the obsolete example password and failed authentication; rerunning with the repository-documented `jobagent-dev-only` test URL passed. One Ruff EN DASH finding in the new test docstring was also corrected.
- The first complete PostgreSQL-enabled gate passed Ruff format/lint but stopped at one Mypy test narrowing error for `JsonValue`. After adding an explicit string check, the final `scripts/check.py` passed: Ruff format checked 168 files, Ruff lint passed, Mypy passed across 110 source files, all 238 tests passed with no skips, and coverage was 87.79%.
- Because JAI-021 substantively changed the legacy Chinese source catalog, the repository rule required its English counterpart in this same commit. Added `docs/en-US/SOURCE_CATALOG.md`, synchronized the five-source state and current environment limitation, updated both indexes, and removed only this document from the bounded JAI-048 inventory; no other legacy migration was mixed into the feature.
- Documentation verification passed across 54 Markdown files with no broken relative links. Paired heading counts match for plans (45/45), backlogs (71/71), active logs (34/34), indexes (5/5), the stability guide (7/7), and the source catalog (6/6). Both backlogs contain the same 168 Issue IDs in order, and `git diff --check` passed.
- Created implementation baseline commit `52d435f35b8fb2a7ac013ac3f7d783261a97e0e5` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed the new feature branch. Before this status-only handoff update, local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit; the worktree was clean. JAI-021 remains in progress because no qualified three-consecutive-calendar-day sequence exists yet.
- Created status-only bilingual handoff commit `da2d3c68f47a012177be1fdd9d5311c5baa32e8d`. Two unchanged normal HTTPS push attempts then failed because GitHub port 443 could not be reached after about 21 seconds; a direct read-only TCP probe also returned `TcpTestSucceeded=False`. No remote URL, protocol, branch history, or commit was changed. Retry the same non-force push after connectivity returns.
- A final TCP probe returned `True`; the unchanged normal HTTPS push then succeeded through outage-record commit `5d67be09bc294d15af325c9279446a40ed7bfa81`. Before this final status-only update, local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit and the worktree was clean.
- Normally pushed final baseline-status commit `a2e3a15da994c97439d449b4be54a3248f236267` and verified local HEAD, its tracking reference, and GitHub `ls-remote` matched. A later same-day bounded all-source re-observation still did not qualify: SASAC exhausted three `PoolTimeout` retries, while the other four source runs and all 7 attempted details succeeded; duplicate rate was 0% and evidence-backed completeness was 82.86% (29/35). A no-body IPv4 `curl` diagnostic independently failed to connect to the official SASAC port 443 after about 21 seconds and returned HTTP `000`; the user separately confirmed the same public URL would not open in a normal browser. This corroborates a source/network-path outage rather than a Python-only parser problem, so no parser or access-control workaround was attempted.
- Created observation-record commit `4efaf87a122c9a82e4e1378b9b3f4463b672e28e`. Its first unchanged normal HTTPS push was reset by the remote connection, and the immediate read-only GitHub port-443 probe returned `False`. The local commit and worktree remain safe; no remote URL, protocol, or history was changed.
- A later port-443 probe still returned `False`, but the bounded normal Git HTTPS retry succeeded and published through interruption-record commit `b3fa11a9e2ce8140fab90a71af37f28faf018ffa`. Before this final status-only update, local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit and the worktree was clean.

### 2026-08-27 — JAI-021 blocked-source replacement

- Resumed the clean `feature/jai-021-sources-four-five-stability` branch at `24af39c9c3a6ad39caadef3d6afd2060418251ca`; local HEAD, its tracking reference, and GitHub `ls-remote` matched, and repository-local authorship remained `user9527448 <2537759248@qq.com>`.
- The bounded pre-replacement five-source observation again failed only at SASAC after three retryable `PoolTimeout` attempts. Four of five sources and all 8 attempted details succeeded, duplicate rate was 0%, and evidence-backed completeness was 80% (32/40). This is not a qualified stability day.
- The user authorized replacing SASAC if it remained unavailable. The exact SASAC path is a public, search-indexed official URL rather than an intranet URL, but both the user browser and project environment still failed; the `www` CDN path could not establish port 443 and the official `wap` hostname presented an expired certificate. No TLS verification bypass or access-control workaround was attempted.
- Evaluated official login-free alternatives with bounded read-only probes. China Telecom's static column, State Grid, and CNPC returned HTTP 412 locally, while the China Telecom recruitment portal required a JavaScript/digest flow. China Mobile's official announcement page returned HTTP 200 and declared a same-origin static list JSON containing current announcements; its detail shells likewise declared public same-origin detail JSON, so it was selected as the fifth active source.
- Added `ChinaMobileRecruitmentAdapter`, runtime/preview registration, strict official URL and numeric-ID validation, title filtering, publication cursor support, and GET-only list/detail materialization. The Adapter preserves displayed organization, title, publication time, visible body, attachments, and provenance. The internal `text5`/`downTime` value is retained only as metadata because the public detail script does not display it; it is never guessed as an application deadline.
- Marked SASAC `blocked` and disabled in catalog version 3, activated China Mobile, and absorbed the bounded JAI-041 public-announcement scope into JAI-021 under the user's priority change. Added three purely synthetic fixture groups and contract/error tests, updated catalog/runtime tests, and expanded the JAI-021 PostgreSQL acceptance to nine documents. The first live China Mobile preview succeeded; its result exposed an overly narrow maintenance-title exclusion, which was corrected from `系统升级` to `升级公告`. A second preview encountered a transient first-request `PoolTimeout`; proxy environment variables were absent and WinHTTP reported direct access.
- The first PostgreSQL acceptance invocation stalled because Docker Desktop was not running and was interrupted without changing repository data. After starting the existing Docker Desktop installation and only the existing Compose `db` service, `jobagent-db-1` became healthy and the nine-document acceptance passed in 2.87 seconds. Focused tests and Mypy passed; Ruff's import-order and ambiguous full-width-colon findings were fixed without suppressions, and the focused rerun passed.
- The first post-replacement all-source run reached four fully successful sources and 10/11 successful details; China Mobile announcement `54614` failed because its public body was only a same-origin image without visible text. Added a synthetic regression test and retained the validated image URL as evidence without downloading or OCR. The first version of that test produced invalid JSON due to unescaped HTML quotes and one Ruff full-width-colon finding; it was corrected to construct JSON structurally, after which all 17 focused tests, Ruff, and Mypy passed.
- A subsequent all-source run again had four fully successful sources because China Mobile's list request transiently exhausted three `PoolTimeout` retries. One final bounded retry then qualified as day 1: 5/5 source runs and 11/11 attempted details succeeded, duplicate rate was 0%, and evidence-backed completeness was 78.18% (43/55). The completeness gap remains explicit under JAI-049; no missing organization, region, or deadline was invented.
- The first complete gate after the image-only fix stopped immediately because Ruff format would reflow two assertions in the new regression test. Formatting that one file resolved it; the final PostgreSQL-enabled `scripts/check.py` passed with Ruff format/lint, Mypy across 112 source files, all 246 tests with no skips, and 87.45% coverage.
- Documentation verification found no broken relative links across 55 Markdown files. The first read-only link-check command mishandled root-level files whose parent path was empty and emitted `Join-Path` errors; treating their parent as `.` fixed the command. Paired heading counts match for plans (45/45), backlogs (71/71), logs (35/35), stability guides (7/7), collection guides (11/11), source catalogs (6/6), and indexes (5/5); both backlogs contain the same 172 Issue references in order, and `git diff --check` passed.
- Created replacement implementation commit `ea690a40cfc02d149d08776dcd23774808eda643` with repository-local author `user9527448 <2537759248@qq.com>`. The first normal HTTPS push was reset by the remote connection; an immediate read-only `ls-remote` and the second unchanged normal push both failed to connect to GitHub port 443 after about 21 seconds. The local commit and worktree remain safe; no remote URL, protocol, history, or author was changed.
- Created bilingual outage-record commit `0f9102692735bd9995fd8244a6fb844ef208063e`. A third normal HTTPS push of the unchanged branch again failed to connect to GitHub port 443 after about 21 seconds. Local HEAD is two commits ahead of the unchanged tracking reference `24af39c9c3a6ad39caadef3d6afd2060418251ca`; both new commits retain the configured user author.
- A later fourth normal push from local head `550d7629bd28e23b446eda21878d6b23dcfc45b6` failed at the same GitHub port-443 boundary. Read-only diagnostics found no Git proxy, proxy environment variable, WinHTTP proxy, or enabled Windows user proxy. DNS resolved `github.com` to `20.205.243.166`, but its TCP 443 connection failed. Further direct retries require an external network-path change; repository configuration remains untouched.
- After the user restored a working external network path, the unchanged normal HTTPS push succeeded through network-diagnostic commit `6d30ad909e8af6c7947a4db7188d2081c22a9d75`. Local HEAD and the tracking reference matched immediately. The first sandboxed `ls-remote` check failed on its isolated network path after 11 ms; the read-only check in the same external network context as the push then succeeded and confirmed GitHub at the same commit.
- Next action: continue daily replacement five-source observations from 2026-08-28 for days 2 and 3; do not close JAI-021 before three consecutive qualified calendar days exist.

### 2026-08-29 — JAI-021 stability sequence restarted

- Resumed the clean `feature/jai-021-sources-four-five-stability` branch at `a6bdcfbe3e96c3ab7d1257873aacf2749f8a1c04`; local HEAD and its tracking reference matched, and repository-local authorship remained `user9527448 <2537759248@qq.com>`.
- No evidence-backed run was recorded on 2026-08-28. The qualified 2026-08-27 result therefore cannot be backfilled or extended into a consecutive sequence.
- The bounded 2026-08-29 replacement observation qualified: all 5 source runs and all 8 attempted details succeeded, duplicate rate was 0%, and evidence-backed completeness was 80% (32/40). NCSS and Firstjob returned valid empty lists; Jiangsu, Shanghai public institutions, and China Mobile returned 2, 3, and 3 details respectively. No database, runtime file, or source body was written.
- The consecutive sequence restarts at day 1 on 2026-08-29. Next action: record qualified runs on 2026-08-30 and 2026-08-31; any missing or failed day restarts the sequence again.
- The user explicitly approved parallel JAI-022 work while JAI-021 remains in observation-only acceptance. Verified JAI-020 is already in `develop`: local and tracking `develop` both point to non-fast-forward merge `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`, whose second parent is the JAI-020 final feature commit `9c86cad8eb621b20fa70e1e6a07a377f929608a3`. The active-branch status table already names the merge commit; the older `develop` copy seen by the user still shows the pre-JAI-021 wording and will receive the clarified table when JAI-021 merges.
- A live GitHub `ls-remote` recheck of `develop` encountered the known intermittent port-443 timeout; branch creation requires a successful retry. Version-control boundary: create JAI-022 only from three-way-verified `develop`, keep JAI-021 observations on their existing branch, merge JAI-021 into `develop` first, then normally merge updated `develop` into JAI-022 and preserve both bilingual WORKLOG histories before rerunning the complete gate. Published history will not be rebased or rewritten.

### 2026-08-30 — JAI-021 qualified stability day 2

- Switched from the clean, pushed JAI-022 startup branch back to `feature/jai-021-sources-four-five-stability`; no JAI-022 commit or file change entered this branch.
- The bounded read-only observation qualified: all 5 source runs and all 9 attempted details succeeded, duplicate rate was 0%, and evidence-backed completeness was 80% (36/45). Firstjob returned a valid empty list; NCSS, Jiangsu, Shanghai public institutions, and China Mobile returned 1, 2, 3, and 3 details respectively. No database, runtime file, or live source body was written.
- The sequence now contains qualified 2026-08-29 day 1 and 2026-08-30 day 2. Next action: run the same bounded observation on 2026-08-31; only a full-source success completes JAI-021 acceptance.

### 2026-08-30 — JAI-021 parallel verification lane prepared

- The user explicitly approved running the remaining JAI-021 verification and later development work in parallel, with records and version-control isolation. This lane now uses the independent worktree `data/worktrees/jai021` on `feature/jai-021-sources-four-five-stability`; no JAI-022/JAI-023 commit or file change is carried into it.
- The actual `Asia/Shanghai` time was `2026-08-30 11:47`. Day 2 had already been recorded today, so no repeated same-day run was executed or counted as day 3. The earliest valid day-3 observation remains 2026-08-31.
- Offline preparation passed with the main repository's existing `.venv` and this worktree's `src`: 32 NCSS, Shanghai public-institution, China Mobile, stability-metric, runtime, and catalog tests passed in 2.11 seconds. The command help exited 0, while `--limit 0` was rejected with exit 2, confirming the 1-10 bound. No live source, database, runtime file, or source-body write was involved.
- The exact 2026-08-31 command for this worktree is:

  ```powershell
  $env:PYTHONPATH = 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\src'
  & 'F:\CXG\JOBAGENTV1.0\.venv\Scripts\python.exe' 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\scripts\evaluate_source_stability.py' --catalog 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\config\source_catalog.toml' --limit 3
  ```

- The observation remains bounded to the five `active`/`enabled` public official sources, concurrency 1, shared pacing/retries, GET-only source access, and JSON stdout. It must not enter login, CAPTCHA, resume/application flows, write the database/files, or retain live source bodies.
- A qualified day 3 requires `observation_date=2026-08-31`, all 5 source runs to succeed, and no attempted detail failure; duplicates must remain within the MVP ceiling of 2%. Evidence-backed completeness is recorded without guessing: the 85% target or the already registered JAI-049 corrective path remains the documented acceptance alternative.
- Merge order is fixed: complete JAI-021 and its final gate, then merge JAI-021 into `develop` first. Only afterward may JAI-022/JAI-023 synchronize the latest `develop` through normal merges, preserve both bilingual WORKLOG histories, resolve paired-document conflicts, and rerun their complete gates before later `develop` merges. Rebase, force push, and published-history rewriting remain prohibited.
- Created the scoped preparation-record commit `dee0632` with repository-local author `user9527448 <2537759248@qq.com>`. Its first unchanged normal HTTPS push failed after about 21 seconds because GitHub port 443 was unreachable; a read-only `Test-NetConnection` resolved `github.com` to `20.205.243.166` but returned `TcpTestSucceeded=False`. The local commit remains safe, and no remote URL, protocol, branch history, or author was changed.
- The later unchanged normal push succeeded. Local HEAD, the tracking reference, and GitHub `ls-remote` all matched blocker-record tip `00de7d1423482d99695a1de99dd451dd79c93f85`; JAI-022 and JAI-023 remained isolated in their own worktrees.

### 2026-09-03 — JAI-021 stability sequence restarted

- Resumed the clean, pushed JAI-021 worktree at `05f41406693f9d659dc53550b31102f1e0ddd2e8`; JAI-022 and JAI-023 remain isolated and no downstream commit entered this branch. Repository-local authorship remains `user9527448 <2537759248@qq.com>`.
- No evidence-backed run was recorded on 2026-08-31, 2026-09-01, or 2026-09-02. The qualified 2026-08-29/30 pair therefore cannot be completed retroactively and the consecutive sequence restarts on 2026-09-03.
- The bounded read-only 2026-09-03 observation qualified as new day 1: all 5 source runs and all 9 attempted details succeeded, no detail failed, duplicate rate was 0%, and evidence-backed completeness was 80% (36/45). Firstjob returned a valid empty list; NCSS, Jiangsu, Shanghai public institutions, and China Mobile returned 1, 2, 3, and 3 details respectively.
- The command retained the approved boundary: at most 3 details per source, concurrency 1, shared pacing/retries, public official endpoints only, JSON stdout, and no database/file/source-body persistence. Missing deadlines, organizations, and regions remained empty rather than guessed.
- At the user's request, a second bounded observation was run on the same 2026-09-03 calendar day. It again passed all 5 source runs and 9/9 attempted details with zero failures, zero duplicates, and 80% evidence-backed completeness (36/45); source counts were unchanged at NCSS 1, Firstjob 0, Jiangsu 2, Shanghai public institutions 3, and China Mobile 3. It is recorded as supplementary repeatability evidence only and does not advance the sequence beyond day 1.
- The 32 focused offline adapter, stability-metric, runtime, and catalog tests passed in 1.68 seconds after the paired observation records were updated; bilingual heading parity and `git diff --check` also passed.
- Next qualified runs are required on 2026-09-04 and 2026-09-05. Any missing or failed calendar day restarts the sequence again; JAI-021 remains unmerged until the full sequence and final gate complete.

### 2026-09-04 — JAI-021 qualified stability day 2

- Resumed cleanly from pushed observation-record commit `816bee92d09d6f080e7e705e6ee75f5f2cc83ac5`; local HEAD and its tracking reference matched before the run, and no downstream-branch change entered this worktree.
- The bounded read-only observation qualified: all 5 source runs and 9/9 attempted details succeeded, no detail failed, duplicate rate was 0%, and evidence-backed completeness was 80% (36/45). Firstjob returned a valid empty list; NCSS, Jiangsu, Shanghai public institutions, and China Mobile returned 1, 2, 3, and 3 details respectively.
- The 32 focused offline adapter, stability-metric, runtime, and catalog tests passed in 1.67 seconds. Paired WORKLOG/stability-guide headings match and `git diff --check` passed.
- The current consecutive sequence is now 2026-09-03 day 1 plus 2026-09-04 day 2. Run the identical bounded observation once on 2026-09-05; only a fully qualified result may close JAI-021 and start its final gate/merge work.

### 2026-09-05 — JAI-021 stability observation failed

- Resumed the clean JAI-021 worktree at `94a0f7fba0c6630ae0cbaa80cdca9599e573abeb`; local HEAD and its tracking reference matched before the run, and no downstream-branch change entered this worktree.
- The bounded read-only observation did not qualify: 4/5 source runs completed because the China Mobile public announcement endpoint exhausted three retries with a retryable `crawler.http_retry_exhausted` / `PoolTimeout`. The other four sources completed; Firstjob returned a valid empty list, while NCSS, Jiangsu, and Shanghai public institutions produced 1, 2, and 3 details.
- All 6 attempted details succeeded, duplicate rate was 0%, and evidence-backed completeness was 86.67% (26/30). The command retained the approved limit of three details per source, concurrency 1, public GET-only access, and no database, file, or source-body persistence.
- This failed daily result interrupts the qualified 2026-09-03/04 pair. No second same-day run will be used to select a better outcome; the next qualified calendar-day observation restarts the sequence at day 1.
- All repository Markdown relative links passed. Paired WORKLOG, stability-guide, and plan heading counts matched at 41/41, 7/7, and 45/45; both backlogs retained identical Issue-ID order, and `git diff --check` passed.
- Created observation-record commit `8e5fbecac1a95d32d5ba79af84e88aaeb79fd7ba` with repository-local author `user9527448 <2537759248@qq.com>`. Its first normal HTTPS push failed because direct access to GitHub port 443 timed out after about 21 seconds; the unchanged push then succeeded through the previously verified command-local proxy `127.0.0.1:7892`, without changing `origin` or persistent Git configuration. Local HEAD, the tracking reference, and GitHub `ls-remote` matched that commit before this network-status update.

### 2026-09-05 — JAI-021 Day 3 waiver and merge-train authorization

- The user explicitly determined that the isolated China Mobile timeout was probably a link or external network-path anomaly rather than a crawler defect and accepted the recorded 2026-09-05 run as Day 3. The source remains monitored; this decision does not change the actual 4/5 source success, three exhausted retries, or error classification.
- JAI-021 acceptance is therefore complete by a documented product-owner exception across the 2026-09-03 through 2026-09-05 records. The user authorized the safe merge train in the established order JAI-021 → JAI-022 → JAI-023 → JAI-024.
- Before each merge, synchronize the latest `develop` into that feature branch with an ordinary merge, preserve both bilingual WORKLOG histories, resolve paired-document conflicts consistently, and rerun the complete proportional gate. Do not rebase, force push, rewrite published commits, or change authorship.
- The final PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 173 files, Ruff lint passed, Mypy passed across 112 source files, all 246 tests passed with no skips, and coverage was 87.45%.

### 2026-09-05 — JAI-022 synchronized after JAI-021 merge

- JAI-021 was merged into `develop` with non-fast-forward commit `8cc0b2eb37b5ec7e2c560ce35b687a687da47b43`; its post-merge PostgreSQL-enabled full gate passed with 246 tests, no skips, and 87.45% coverage. Local `develop`, `origin/develop`, and GitHub `ls-remote` matched before this synchronization.
- Normally merged the latest `develop` into JAI-022. Code merged without conflict; the expected conflicts were limited to paired plans, backlogs, indexes, and WORKLOG files. Resolution preserves both Issue histories, the actual JAI-021 Day 3 metrics/waiver, and the complete JAI-022 implementation record.
- Bilingual heading parity, backlog Issue-ID order, Markdown relative links, and `git diff --check` passed. The PostgreSQL-enabled combined `scripts/check.py` passed: Ruff format checked 183 files, Ruff lint passed, Mypy passed across 119 source files, all 254 tests passed with no skips, and coverage was 87.57%.
- Next: commit and normally push the synchronization before merging JAI-022 into `develop`.

### 2026-09-05 — JAI-023 synchronized after JAI-022 merge

- JAI-022 was merged into `develop` with non-fast-forward commit `e7948c9225fba32e499786cc8400cf0dd975e4ca`; its post-merge PostgreSQL-enabled full gate passed with 254 tests, no skips, and 87.57% coverage. Local `develop`, `origin/develop`, and GitHub `ls-remote` matched before this synchronization.
- Normally merged the latest `develop` into JAI-023. Code and migrations merged without conflict; expected conflicts were limited to paired plans, backlogs, indexes, and WORKLOG files. Resolution preserves all JAI-021, JAI-022, and JAI-023 histories and the Day 3 waiver's actual metrics.
- Bilingual heading parity, backlog Issue-ID order, Markdown relative links, and `git diff --check` passed. The PostgreSQL-enabled combined `scripts/check.py` passed: Ruff format checked 193 files, Ruff lint passed, Mypy passed across 126 source files, all 271 tests passed with no skips, and coverage was 87.86%.
- Next: commit and normally push before merging JAI-023 into `develop`.

### 2026-09-05 — JAI-024 synchronized after JAI-023 merge

- JAI-023 was merged into `develop` with non-fast-forward commit `5935b5206a933e8a14cb80b0421ed90f1a0e336c`; its post-merge PostgreSQL-enabled full gate passed with 271 tests, no skips, and 87.86% coverage. Local `develop`, `origin/develop`, and GitHub `ls-remote` matched before this synchronization.
- Normally merged the latest `develop` into JAI-024. Code, migrations, and the backlog merged without conflict; expected conflicts were limited to paired plans, indexes, and WORKLOG files. Resolution preserves all JAI-021 through JAI-024 histories and the Day 3 waiver's actual metrics.
- Bilingual heading parity, backlog Issue-ID order, Markdown relative links, and `git diff --check` passed. The PostgreSQL-enabled combined `scripts/check.py` passed: Ruff format checked 206 files, Ruff lint passed, Mypy passed across 136 source files, all 282 tests passed with no skips, and coverage was 87.96%.
- Next: commit and normally push before merging JAI-024 into `develop`.

### 2026-09-05 — Merge train completed and JAI-025 started

- JAI-024 synchronization tip `11551331a403942d9b78c758997c6ae7536a94e7` was normally pushed and then merged into `develop` with non-fast-forward commit `0aa6b233ea8216aecdbe1d1dce4031ad6884a442`.
- The post-merge PostgreSQL-enabled full gate passed: Ruff format checked 206 files, Ruff lint passed, Mypy passed across 136 source files, all 282 tests passed with no skips, and coverage was 87.96%. Local `develop`, `origin/develop`, and GitHub `ls-remote` all matched `0aa6b233ea8216aecdbe1d1dce4031ad6884a442`; ancestry checks for the final JAI-021 through JAI-024 feature tips all passed.
- Verified both backlogs identify JAI-025 as the next incomplete planned Issue, then created `feature/jai-025-top-20-quality-review` from the triple-verified `develop` baseline. Repository-local authorship remains `user9527448 <2537759248@qq.com>`.
- Scope is limited to at least 50 sanitized, manually reviewable relevance labels, deterministic Top 20/miss analysis, an unchanged v1 baseline, an explicit new score version, before/after evidence, and MVP limitations. JAI-026 scheduling and JAI-027 notification behavior remain out of scope.
- Next: implement the offline quality-review contracts and fixture, classify false positives/misses, tune only the new score version, and run focused tests before the complete PostgreSQL gate.

### 2026-09-05 — JAI-025 evaluation implementation and acceptance boundary

- Added an offline quality-review contract, strict JSON loader, stable Top-K evaluator, JSON command, and 60 entirely synthetic/sanitized proposed labels with explicit categories and rationales. The artifact is clearly marked as proposed pending project-owner review; it is not represented as historical human-labelled data.
- Preserved `jai-023-v1` as a supported replay baseline and added candidate `jai-025-v2`. V2 increases direct job-direction/major weight, reduces urgency/completeness weight, and excludes requirements-only mentions from positive direction scoring while retaining requirements in the exclusion hard filter.
- On the proposed fixed set, v1 has 15 true positives, 5 `requirements_context_false_positive` items, and 15 misses in Top 20 (Precision@20 0.75, Recall@20 0.50). V2 has 20 true positives, no Top 20 false positives, and 10 explicit misses (Precision@20 1.00, Recall@20 0.666667).
- The first focused check exposed one malformed `__all__` insertion and three v1 expectations that needed explicit v2 values; after correction, focused Ruff and Mypy passed and all 22 matching tests passed. This was a local implementation check, not a production failure.
- The PostgreSQL-enabled full `scripts/check.py` passed: Ruff format checked 213 files, Ruff lint passed, Mypy passed across 139 source files, all 288 tests passed with no skips, and coverage was 87.77%. `git diff --check` also passed.
- A read-only check of the existing local development database found `raw_documents=0`, `job_posts=0`, and `job_positions=0`; it also has not yet applied the JAI-023 `match_results` migration. There are therefore no 50 actual historical positions available locally, so the Issue's historical/human-labelled acceptance cannot be claimed honestly from current data.
- Created review-preparation commit `4fe0274cdc2fadbfe50c71086771fb50c0522a4b` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed the feature branch through the verified command-local proxy without changing `origin` or persistent Git settings. Local HEAD, its tracking reference, and GitHub `ls-remote` all matched that commit after the push.
- Next: obtain an explicit project-owner decision on whether the 60 sanitized proposed labels are accepted as a scoped substitute. Without that plan change—or a supplied/populated historical set with human labels—JAI-025 remains incomplete and must not merge to `develop`.

### 2026-09-05 — JAI-025 missing-data recovery proposal recorded for approval

- Rechecked the local state without writes: the business database is at Alembic `0003_attachment_storage`; `sources`, `raw_documents`, `job_posts`, and `job_positions` all contain zero rows. The repository head is `0008_daily_report_snapshots`.
- Existing `scripts/manage_crawl.py run` requires a matching enabled database source and persists every item returned by one source discovery; it has no operator-supplied item limit. The source catalog has five `active`/`enabled` public sources, but the empty runtime table means no persistent run can start yet.
- Recorded proposed decision D-034 and gates G1–G5. The recommended path preserves the original plan: upgrade the empty local business schema, transactionally bootstrap only already-approved active catalog sources, add a tested optional detail cap, collect at most 60 public details across at least three sources, run existing deterministic extraction/evidence persistence, keep source-facing review material ignored locally, and commit only the owner-confirmed sanitized benchmark.
- Alternative B is to accept the current synthetic set as a scope substitute; it is faster but does not meet the original historical-sample intent and is not recommended. Alternative C is to wait for JAI-026 to accumulate data; it reverses the planned JAI-025 → JAI-026 order and is also not recommended without an explicit priority change.
- No migration, database insert, persistent crawl, additional code change, score retuning, completion checkbox, merge, or destructive action was performed while awaiting approval.
- Next: project owner reviews and approves/rejects G1 and the overall D-034 path. Only after explicit approval may implementation begin; later gates still require separate evidence and approval.

### 2026-09-05 — D-034 and G1 approved

- The project owner explicitly instructed the team to execute the recorded design. This approves D-034 and G1 only: add the backward-compatible bounded manual-crawl option with tests/docs, upgrade the empty local business database from `0003_attachment_storage` to repository head, and transactionally initialize only the five catalog sources already marked `active` and `enabled`.
- G1 does not authorize a persistent live crawl, label confirmation, score retuning, completion status, or merge. No source detail request may be persisted until G1 evidence is recorded and the owner separately approves G2 discovery counts and allocations.
- Execution order: implement and verify the optional limit first; capture the pre-migration version/counts; run the existing tested Alembic upgrade without destructive downgrade; verify head/schema drift; insert the exact approved catalog/source identity rows in one transaction with post-insert equality checks; then rerun proportional/full gates and record final state.

### 2026-09-05 — JAI-025 G1 completed; G2 evidence prepared

- Added optional `run --limit N` support. It selects the first `N` discovered items in stable source order, records both selected and total discovery counts, rejects non-positive limits, and cannot be combined with failed-URL retry selection. Existing uncapped runs and retries retain their previous behavior. Paired collection documentation and regression tests were updated.
- The pre-upgrade business database was at `0003_attachment_storage` with zero source, raw-document, post, and position rows. The first post-upgrade verification attempt could not access the Docker named pipe inside the sandbox, so it supplied no password and Alembic failed authentication without writing the database. The check was rerun in the authorized host context with a process-only URL derived from the running container; no credential was printed, stored, or committed.
- Alembic now reports `0008_daily_report_snapshots (head)` and `alembic check` reports no pending upgrade operation. A guarded single transaction required `sources` to be empty, inserted exactly the five existing active/enabled catalog identities, verified the adapter set/count, and committed. Source IDs 1–5 are NCSS, Firstjob, Jiangsu personnel exam, Shanghai public institutions, and China Mobile respectively; all are enabled with their catalog intervals. `crawl_runs`, `raw_documents`, `job_posts`, and `job_positions` remain at zero.
- The final PostgreSQL-enabled full gate passed Ruff format/lint, Mypy across 139 source files, all 294 tests with no skips, and 87.80% coverage, including the direct invariant that a detail limit cannot truncate failed-item retries.
- Read-only list discovery was run only to prepare the next approval input. The sandbox attempt failed at its network boundary; the host-context retry found NCSS 3, Firstjob 0, Jiangsu 2, and Shanghai public institutions 5 items, while China Mobile exhausted its connection retries. It requested no detail and wrote neither the database nor files. Proposed G2 allocation is therefore 3/0/2/5/0 (10 details across three sources). Attachments may expand those announcements into at least 50 positions, but this is not guaranteed; if fewer than 50 distinct positions result, the workflow stops for a new owner decision instead of expanding sources automatically.
- G1 is complete. Persistent detail requests, extraction, label confirmation, score retuning, completion, and merge remain unauthorized until the project owner reviews and explicitly approves or revises G2.
- Created G1 implementation commit `4b737e4e8eeab3bda2e45af9c3adf0cd6d183c4c` with repository-local author `user9527448 <2537759248@qq.com>` and normally pushed it through the previously verified command-local proxy without changing `origin` or persistent Git configuration. Before this status-only update, local HEAD, the tracking reference, and GitHub `ls-remote` all matched that commit and the worktree was clean.

### 2026-09-05 — D-035 priority change and G2 approved

- The project owner directed the team to prioritize closing the executable flow and to record newly discovered optimization needs for later adjustment. This approves the proposed G2 allocation `3/0/2/5/0`, while retaining the ten-detail total, three-source coverage, concurrency 1, at least one-second pacing, public-only access, and no bypass boundary.
- The earlier requirement to stop immediately when the live run produces fewer than 50 distinct positions is superseded for flow validation only. Any shortfall remains visible quality debt; synthetic labels remain explicitly synthetic, and JAI-025 cannot claim a 50-position historical human review that did not occur.
- Execution boundary: persist only the approved reachable details, inspect run/database evidence, continue through existing deterministic parse/extract/match/report components where supported, and record each unsupported handoff or missing operator command. Do not expand quotas, add sources/adapters, retune scoring, or implement JAI-026/JAI-027 behavior without a later decision.

### 2026-09-05 — JAI-025 bounded live-flow validation completed

- Ran only the approved source IDs and limits. Crawl run 1 (NCSS, limit 3) discovered and created 2 documents; run 2 (Jiangsu, limit 2) created 2; run 3 (Shanghai public institutions, limit 5) created 5. All three runs succeeded, all 9 attempted details were persisted, and no detail failed. Firstjob and China Mobile received no persistent run, so the approved total was not expanded.
- All nine current documents contained visible body text. The attachment table remained empty because the current manual crawl stores detail bodies but does not hand discovered PDF/XLSX links to `AttachmentStorageService`. Deterministic reparse version `jai-025-live-v1` nevertheless completed for all documents: 9 posts, 2 positions, 38 field-evidence rows, and 41 validation issues. One position is recommendation-eligible and one is blocked; seven attachment-oriented notices produced no body-derived position. Missing values remained missing.
- Preserved the default empty/unrestricted preference values, triggered one recomputation, and deliberately used published baseline `jai-023-v1` before G4 rather than treating candidate v2 as an approved live rule. Matching processed 2 positions, passed 1, filtered 1, and created 2 results. Report version `jai-024-v1` created one 2026-09-05 snapshot with group counts 1 priority, 0 closing soon, 1 added today, and 2 needs confirmation.
- The first direct one-shot service invocation used Windows' default Proactor loop and failed before reading preferences because async psycopg requires a selector loop; it made no preference, match, or report write. The retry used the same `SelectorEventLoop` pattern as repository commands and succeeded. A repeat then returned matching `not_required`, processed zero rows, and reused report snapshot 1 with the same content hash.
- Added a synthetic PostgreSQL end-to-end regression that protects raw-document reparse, validation, unchanged default preference update, v1 matching, all four report groups, matching no-op, and immutable report reuse in one test. Its focused Ruff and PostgreSQL test passed. A direct single-file Mypy invocation resolved project imports as untyped installed modules and reported import errors; the repository-configured full Mypy target remains the authoritative check and will run in the final gate.
- Recorded deferred quality work in JAI-049: automatic bounded attachment handoff, Firstjob/China Mobile source diagnostics, at least 50 distinct live human labels, and a new score version if that benchmark requires rule changes. The synthetic 60-case result and the 2-position live smoke remain separately labelled and do not imply production quality.
- The final PostgreSQL-enabled `scripts/check.py` passed: Ruff format checked 214 files, Ruff lint passed, Mypy passed across 140 source files, all 295 tests passed with no skips, and coverage was 87.82%. The offline evaluator reproduced v1 Precision@20/Recall@20 of 0.75/0.50 and v2 of 1.00/0.666667. Bilingual headings match for plans 45/45, backlogs 71/71, work logs 63/63, and quality guides 7/7; both backlogs retain the same 183 Issue IDs in order, all 65 tracked Markdown links resolve, and `git diff --check` passed.

## 4. Verification and blockers

- JAI-046 final gate: Ruff format/lint passed; Mypy passed across 56 source files; 89 tests passed with PostgreSQL; coverage 88.35%.
- JAI-046 push verification: local `develop`, `origin/develop`, and `git ls-remote --heads origin develop` matched `f07b6d50ed9abda08d38883eefa3904b98b99455`.
- One pre-push read-only GitHub check failed during a temporary port 443 outage; the later normal push and explicit `ls-remote` verification succeeded.
- JAI-047 verification passed: 35 Markdown files had no broken relative links; bilingual heading and Issue-ID parity passed; `git diff --check` passed; Ruff format/lint, Mypy, all 89 PostgreSQL-enabled tests, and 88.35% coverage passed.
- Pre-push formatting correction: four staged trailing-space findings in `docs/en-US/DEVELOPMENT_PLAN.md` were removed; final staged and worktree diff checks must pass before push.
- JAI-012 final gate: Ruff format/lint passed; Mypy passed across 62 source files; 105 tests passed with PostgreSQL; coverage 88.38%. The offline JAI-012 acceptance performed no live-source request and left no repository runtime data.
- JAI-012 handoff recheck on 2026-08-15: the first Mypy invocation named the non-existent planned `app` directory and was corrected to the repository-configured targets; the first test run omitted `JOBAGENT_TEST_DATABASE_URL`, so 98 tests passed, 7 PostgreSQL tests skipped, and coverage was 83.18%. After starting the existing Docker Desktop installation and using the existing `jobagent_test` database, Ruff format/lint, Mypy, all 105 tests, and 88.38% coverage passed.
- JAI-025 G1: Alembic current/check passed at `0008_daily_report_snapshots`; exact five-source bootstrap postconditions passed; all business-data tables remain empty. The PostgreSQL full gate passed 294 tests with no skips and 87.80% coverage. The only current operational limitation is China Mobile list discovery connectivity; it is recorded as a zero allocation rather than bypassed.
- JAI-025 live flow: 9/9 approved details persisted across three successful runs; all nine reparses completed; 2 baseline matches and one immutable report snapshot were created; the repeat matching/report path was idempotent. The committed end-to-end regression passed against PostgreSQL.
- JAI-025 final preparation gate: Ruff format/lint and repository-configured Mypy passed; all 295 PostgreSQL-enabled tests passed with no skips at 87.82% coverage; bilingual structure, Issue-ID order, Markdown links, evaluator replay, and diff checks passed.

## 5. Next actions

1. Run the final PostgreSQL-enabled quality gate and documentation parity/link checks on the complete flow-closure tree, then commit and normally push the feature branch.
2. Present the exact final evidence for explicit G5 approval. Do not merge JAI-025 to `develop` or start JAI-026 before that approval.
3. Keep the deferred >=50 live human review, attachment handoff, and source diagnostics in JAI-049; do not silently change `jai-025-v2`.
4. Keep JAI-026 scheduling, JAI-027 notifications, JAI-030 maintenance APIs, OCR/JAI-B01, and JAI-048 outside the active Issue.

## 6. Update template

```markdown
### YYYY-MM-DD — JAI-XXX title

- Status/branch:
- Work completed:
- Decisions/deviations:
- Verification:
- Blockers/user action:
- Next action:
```
