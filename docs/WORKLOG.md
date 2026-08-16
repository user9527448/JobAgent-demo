# JOBAGENT Development Work Log

> Language: English. Simplified Chinese mirror: [`zh-CN/WORKLOG.md`](zh-CN/WORKLOG.md).
>
> The original mixed-language history through JAI-046 is preserved byte-for-byte in
> [`archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`](archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)
> with SHA-256 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`.
>
> Last updated: 2026-08-16
>
> Active branch: `feature/jai-013-parser-protocol-intermediate-format`

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
| JAI-013 | Complete, feature branch pushed; pending `develop` merge | `feature/jai-013-parser-protocol-intermediate-format` / `269648a` | MIME registry, traceable text/table schemas, statuses, error codes, tests, and bilingual documentation verified |

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

## 4. Verification and blockers

- JAI-046 final gate: Ruff format/lint passed; Mypy passed across 56 source files; 89 tests passed with PostgreSQL; coverage 88.35%.
- JAI-046 push verification: local `develop`, `origin/develop`, and `git ls-remote --heads origin develop` matched `f07b6d50ed9abda08d38883eefa3904b98b99455`.
- One pre-push read-only GitHub check failed during a temporary port 443 outage; the later normal push and explicit `ls-remote` verification succeeded.
- JAI-047 verification passed: 35 Markdown files had no broken relative links; bilingual heading and Issue-ID parity passed; `git diff --check` passed; Ruff format/lint, Mypy, all 89 PostgreSQL-enabled tests, and 88.35% coverage passed.
- Pre-push formatting correction: four staged trailing-space findings in `docs/en-US/DEVELOPMENT_PLAN.md` were removed; final staged and worktree diff checks must pass before push.
- JAI-012 final gate: Ruff format/lint passed; Mypy passed across 62 source files; 105 tests passed with PostgreSQL; coverage 88.38%. The offline JAI-012 acceptance performed no live-source request and left no repository runtime data.
- JAI-012 handoff recheck on 2026-08-15: the first Mypy invocation named the non-existent planned `app` directory and was corrected to the repository-configured targets; the first test run omitted `JOBAGENT_TEST_DATABASE_URL`, so 98 tests passed, 7 PostgreSQL tests skipped, and coverage was 83.18%. After starting the existing Docker Desktop installation and using the existing `jobagent_test` database, Ruff format/lint, Mypy, all 105 tests, and 88.38% coverage passed.

## 5. Next actions

1. Commit and normally push this JAI-013 handoff-status update, then re-verify local, tracking, and GitHub branch hashes.
2. Merge JAI-013 into `develop`, normally push, then start JAI-014 from the latest synchronized `develop`.
3. Execute JAI-048 as a separate documentation Issue; do not mix broad legacy-document migration into feature work.

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
