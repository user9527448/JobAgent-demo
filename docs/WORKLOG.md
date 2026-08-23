# JOBAGENT Development Work Log

> Language: English. Simplified Chinese mirror: [`zh-CN/WORKLOG.md`](zh-CN/WORKLOG.md).
>
> The original mixed-language history through JAI-046 is preserved byte-for-byte in
> [`archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`](archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)
> with SHA-256 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`.
>
> Last updated: 2026-08-23
>
> Active branch: `feature/jai-019-field-evidence-merging`

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
| JAI-019 | Complete and normally pushed | `feature/jai-019-field-evidence-merging` / `a2c41fe` | Deterministic body/attachment precedence, explicit conflicts, extraction versions, and durable field evidence verified |

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

## 4. Verification and blockers

- JAI-046 final gate: Ruff format/lint passed; Mypy passed across 56 source files; 89 tests passed with PostgreSQL; coverage 88.35%.
- JAI-046 push verification: local `develop`, `origin/develop`, and `git ls-remote --heads origin develop` matched `f07b6d50ed9abda08d38883eefa3904b98b99455`.
- One pre-push read-only GitHub check failed during a temporary port 443 outage; the later normal push and explicit `ls-remote` verification succeeded.
- JAI-047 verification passed: 35 Markdown files had no broken relative links; bilingual heading and Issue-ID parity passed; `git diff --check` passed; Ruff format/lint, Mypy, all 89 PostgreSQL-enabled tests, and 88.35% coverage passed.
- Pre-push formatting correction: four staged trailing-space findings in `docs/en-US/DEVELOPMENT_PLAN.md` were removed; final staged and worktree diff checks must pass before push.
- JAI-012 final gate: Ruff format/lint passed; Mypy passed across 62 source files; 105 tests passed with PostgreSQL; coverage 88.38%. The offline JAI-012 acceptance performed no live-source request and left no repository runtime data.
- JAI-012 handoff recheck on 2026-08-15: the first Mypy invocation named the non-existent planned `app` directory and was corrected to the repository-configured targets; the first test run omitted `JOBAGENT_TEST_DATABASE_URL`, so 98 tests passed, 7 PostgreSQL tests skipped, and coverage was 83.18%. After starting the existing Docker Desktop installation and using the existing `jobagent_test` database, Ruff format/lint, Mypy, all 105 tests, and 88.38% coverage passed.

## 5. Next actions

1. Merge JAI-019 only in the next authorized integration step and verify synchronized `develop` afterward.
2. Start JAI-020 from that synchronized `develop`; keep its validation/review/reparse scope separate from JAI-019.
3. Keep OCR deferred to JAI-B01 and execute JAI-048 as a separate documentation Issue.

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
