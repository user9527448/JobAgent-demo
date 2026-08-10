# JOBAGENT Development Work Log

> Purpose: a concise, continuously updated record of progress, decisions, verification, blockers, and user actions.
>
> Last updated: 2026-08-10
>
> Active branch: `feature/jai-011-source-catalog-sasac`

## 1. Current status

| Issue | Status | Branch / commit | Notes |
|---|---|---|---|
| Project planning | Complete | `main` / `e72f50e` | Development plan and Issue backlog published |
| JAI-001 Project bootstrap | Complete, merged to develop | `develop` / `9c8b3ca` | Python package, `.venv` workflow, Ruff, Mypy, Pytest |
| JAI-002 Configuration/logging/errors | Complete, merged to develop | `develop` / `0ffd008` | Typed settings, JSON logs, redaction, error taxonomy; 7 tests passed, 95% coverage |
| JAI-003 API/PostgreSQL/health | Complete, merged to develop | `develop` / `40821f7` | FastAPI, PostgreSQL pool, health checks and Compose verified |
| JAI-004 Test/CI baseline | Complete, merged to develop | `develop` / `ae6c5a8` | Unified quality gate, isolated PostgreSQL integration test, GitHub Actions |
| JAI-005 Real-source vertical Spike | Complete, merged to develop | `develop` / `548be94` | Jining public recruitment list/detail/PDF technical validation |
| JAI-006 Core models/first migration | Complete, merged to develop | `develop` / `1690dd9` | Seven core tables, constraints, relationships, UTC persistence and Alembic |
| JAI-007 Source Adapter/orchestrator | Complete, merged to develop | `develop` / `33241fd` | Adapter registry/protocol, batch orchestration, persisted run statistics and item-level error isolation |
| JAI-008 HTTP client policy | Complete, merged to develop | `develop` / `9016fb3` | Source-level timeout, concurrency/rate limiting, retries, User-Agent and conditional cache headers |
| JAI-009 URL/fingerprint/idempotency | Complete, merged to develop | `develop` / `020e0b7` | Canonical URLs, normalized content fingerprints, version-preserving idempotent persistence |
| JAI-010 Attachment storage | Complete, merged to develop | `develop` / `e0ea5d9` | PDF/XLS/XLSX discovery, streamed validation, SHA-256 content addressing and atomic idempotent storage |
| JAI-036 Simplified Chinese documentation | Complete, merged to develop | `develop` / `82adb73` | Nine Chinese mirrors, bilingual navigation and durable synchronization rules, based on JAI-010 |
| JAI-011 来源网站库与首批 Adapter | 进行中 | `feature/jai-011-source-catalog-sasac` | 建立可手工维护的网站与关键词配置，首个接入国资委公开招聘栏目 |

## 2. Environment readiness

### Git for Windows installation completed

Verified on 2026-08-09:

- Git for Windows 2.55.0 is installed at `C:\Program Files\Git\cmd\git.exe`.
- The HTTPS remote helper is present and Git Credential Manager 2.9.0 is enabled through the system Git configuration.
- The global Git author name and email are configured; credentials remain outside the repository.
- Codex may place its bundled Git earlier on `PATH`; use the installed executable above explicitly for remote operations if the bundled runtime lacks an HTTPS helper.
- Repository discovery, branch inspection and local status checks pass. Earlier `github.com:443` timeouts were transient; the explicitly authorized JAI-007 push later succeeded with Git for Windows.

### Docker installation completed

Verified on 2026-08-08:

- WSL 2.7.11
- Docker Desktop 4.85.0
- Docker Engine 29.6.2, Linux containers
- Docker Compose 5.3.1
- PostgreSQL 16 and the JOBAGENT API run as healthy Compose services

The previous blocker below is resolved and retained for history.

### Resolved: Docker was not installed or available on PATH

Observed on 2026-08-07:

```text
docker: command not found
```

JAI-003 code and isolated tests can proceed without Docker, but the acceptance test that starts the API and PostgreSQL together cannot be completed until Docker is available.

User setup checklist:

1. Confirm hardware virtualization is enabled in BIOS/UEFI.
2. Update WSL. The current `wsl --version` command is unsupported on this machine and prints the legacy inbox help, which indicates that the modern WSL package still needs to be installed or updated. Docker currently requires WSL 2.1.5 or newer and recommends a current WSL release.
3. If WSL is absent or outdated, use an Administrator PowerShell to run `wsl --install` or `wsl --update`, then restart Windows if prompted.
4. Install Docker Desktop for Windows using the WSL 2 backend and Linux containers.
5. Start Docker Desktop and wait until the engine reports that it is running.
6. Open a new PowerShell window and verify:

   ```powershell
   docker version
   docker compose version
   docker run --rm hello-world
   ```

7. Confirm local ports `5432` and `8000` are not occupied. The Compose file can be adjusted if either port is already in use.

Docker Desktop already includes Docker Compose, so a separate Compose installation is not required. A separate local PostgreSQL installation is also not planned; PostgreSQL will run in a container.

References:

- [Docker Desktop for Windows installation and requirements](https://docs.docker.com/desktop/setup/install/windows-install/)
- [Docker Desktop WSL 2 backend](https://docs.docker.com/desktop/features/wsl/)
- [Docker Compose installation](https://docs.docker.com/compose/install/)

## 3. Environment baseline

| Component | Current state |
|---|---|
| Operating system | Windows / PowerShell |
| Project path | `F:\CXG\JOBAGENTV1.0` |
| Python installation | Existing `F:\py3.11.9\python.exe` |
| Project environment | `.venv`, created from the existing Python 3.11.9 installation |
| Git | Git for Windows 2.55.0; Git Credential Manager 2.9.0; installed at `C:\Program Files\Git\cmd\git.exe` |
| Git remote | `https://github.com/user9527448/JobAgent-demo.git` |
| Docker | Desktop 4.85.0; Engine 29.6.2; Compose 5.3.1; Linux containers |

## 4. Decisions

### D-001 Data pipeline before Agent

The MVP prioritizes collection, immutable raw data, attachment parsing, validation, matching, and reports. Agent capabilities remain scheduled for JAI-033 onward.

### D-002 One Issue per feature branch

Changes use `feature/<issue>-<description>` branches. JAI-002 and JAI-003 are temporarily stacked because earlier branches have not yet been merged into `develop`.

### D-003 Python environment policy

Reuse the existing Python installation and maintain dependencies in repository-local `.venv`. Do not download a new Python version unless explicitly requested.

### D-004 Persistent development record

`docs/WORKLOG.md` is updated at Issue start, meaningful decisions/blockers, verification, and completion. `AGENTS.md` makes this requirement durable for future Codex work in the repository.

### D-005 One quality-gate entry point

Local development and GitHub Actions both invoke `python scripts/check.py`. PostgreSQL integration tests require `JOBAGENT_TEST_DATABASE_URL`; CI supplies a dedicated test database and local runs skip only that integration test when the variable is absent.

### D-006 First source for the vertical Spike

Use the Jining Human Resources and Social Security Bureau's public institution recruitment column for JAI-005. It exposes a public HTML list, static announcement detail pages, and direct PDF attachments without login or CAPTCHA. The Spike will use a descriptive User-Agent, low request rate, no parallel requests, and offline fixtures for regression tests.

### D-007 Historical data is deletion-resistant

JAI-006 uses `RESTRICT` foreign keys and no ORM delete cascades for source documents, attachments, structured posts or field evidence. Sources are disabled with `enabled=false`; once historical records reference a source, accidental physical deletion is rejected by PostgreSQL.

### D-008 Destructive database tests require an explicit test database

Migration integration tests reset the public schema and therefore refuse to run unless `JOBAGENT_TEST_DATABASE_URL` names a database ending in `_test`. CI and local verification use `jobagent_test`; development and production database names cannot pass this guard.

### D-009 Collection orchestration stops before raw-document persistence

JAI-007 returns successful `RawDocumentInput` values from the common batch flow and persists only `crawl_runs`. URL normalization, content fingerprinting and immutable/idempotent raw-document writes remain in JAI-009, preventing premature duplication of that policy inside Adapters.

### D-010 HTTP policy is isolated per source client

JAI-008 gives each source its own HTTP client policy, concurrency semaphore and request-spacing clock so timeout, rate and concurrency settings cannot leak between sources. Conditional validators are returned with the response for JAI-009 to persist alongside raw-document state; no database schema was added early.

### D-011 Content updates create immutable raw-document versions

Each `raw_documents` row is one source-evidence version. A partial unique index exposes exactly one current row per source/canonical URL, while positive version numbers and `supersedes_id` preserve the prior chain. A transaction-scoped PostgreSQL advisory lock serializes concurrent first writes for the same source URL; identical content reuses the current row and changed content inserts a new version.

### D-012 Attachment download and parsing states remain separate

JAI-010 stores validated source bytes in a same-volume, SHA-256-addressed object store and records `download_status` independently from `parse_status`. A file is published only after the complete streamed body is size-checked, synchronized and signature/MIME-validated; parsing, OCR and spreadsheet interpretation cannot be implied by download success and remain in JAI-013 through JAI-016.

### D-013 中文文档采用显式镜像，不重复已经是中文的文档

从 JAI-036 起，纯英文技术文档在 `docs/zh-CN/` 下维护简体中文镜像，并由中文索引提供中英文双向导航；根 README、开发计划、Issue 清单和配置说明等原本已经是中文的文档继续只维护一份。修改英文原文时必须在同一提交中同步对应中文镜像。历史 WORKLOG 不整篇回译，本 Issue 及后续新增日志改用中文。

### D-014 网站库是版本化人工配置，不是自动发现器

`config/source_catalog.toml` 记录经核验的官方候选来源、地区、接入状态和关键词；只有已有显式 Adapter 的 `active`/`enabled` 来源可运行。系统不自动发现或执行任意网站配置，报名系统和未验证动态门户默认停用。

## 5. Completed work history

### 2026-08-07 — Planning and repository setup

- Created the 10-week development plan and 35-Issue backlog.
- Initialized Git and configured `main` and `develop`.
- Published the repository planning baseline.

### 2026-08-07 — JAI-001 Project bootstrap

- Added installable Python project structure, CLI smoke command, development dependencies, formatting/type/test configuration, `.env.example`, ignore rules, and README workflow.
- Initially interpreted the environment requirement incorrectly and removed `.venv`; corrected after user clarification.
- Final approach: create `.venv` from the existing Python 3.11.9 installation without downloading another Python version.
- Verification: Ruff format/check passed; Mypy passed; Pytest passed.
- Note: development packages were briefly installed into the existing global Python environment before clarification. They were not automatically removed to avoid affecting other projects.

### 2026-08-07 — JAI-002 Configuration, logging, and errors

- Added required environment validation with `pydantic-settings`.
- Added Windows-compatible IANA time zone data.
- Added structured JSON logs, correlation context, and recursive secret-field redaction.
- Added configuration, transient, and permanent error categories.
- Verification: Ruff passed; Mypy passed; 7 tests passed; total coverage 95%.

### 2026-08-07 — JAI-003 started

- Created `feature/jai-003-api-postgres-health` from the JAI-002 branch.
- Checked local Docker availability and found Docker unavailable.
- Paused implementation to clarify environment setup and durable work-log requirements.

### 2026-08-08 — JAI-003 completed

- Added a FastAPI application factory with lifecycle-managed infrastructure.
- Added an asynchronous SQLAlchemy PostgreSQL pool using psycopg 3.
- Added `/health/live` and database-aware `/health/ready` endpoints.
- Added a non-root API image, PostgreSQL 16 Compose service, persistent database volume, dependency health checks, and restart policies.
- Added required database configuration while keeping the URL secret in settings and logs.
- Replaced the deprecated Starlette `httpx` test path with `httpx2` and removed all test warnings.
- Verification: Ruff passed; Mypy passed across 18 files; 10 tests passed; coverage 93%.
- Container verification: both services healthy; live returned 200; ready returned 200 with PostgreSQL available.
- Failure verification: stopping PostgreSQL caused ready to return 503 with a sanitized response; after restart it returned 200 again.
- First API image pull failed because Docker Hub authentication timed out; a targeted retry succeeded.
- Two GitHub push attempts timed out on port 443; all commits remain safe in the local repository.
- GitHub connectivity recovered later on 2026-08-08 and the branch was pushed successfully.
- Containers were left running for local inspection at `http://localhost:8000`.

### 2026-08-08 — JAI-004 completed

- Created `feature/jai-004-ci-test-baseline` from the verified JAI-003 branch after the user explicitly approved continuing to the next stacked Issue.
- Started a shared local/CI quality-gate command, an isolated PostgreSQL integration test, an 85% coverage threshold, and a GitHub Actions workflow.
- The workflow uses an ephemeral `jobagent_test` PostgreSQL service; no production or personal data is in scope.
- The first real database run exposed psycopg's incompatibility with the default Windows Proactor event loop; the integration test now explicitly uses the compatible Selector event loop while remaining portable to Linux CI.
- Verification with PostgreSQL enabled: Ruff formatting/lint passed, Mypy passed across 20 files, 11 tests passed, and coverage was 95.17% against an 85% threshold.
- Repeatability verification without a local database URL: 10 tests passed, one integration test skipped as designed, and coverage remained 92.75%.
- Gate verification: a temporary deliberately failing test made `python scripts/check.py` exit with status 1 at Pytest; the temporary test was then removed and the full gate returned to green.

### 2026-08-09 — JAI-005 completed

- Created `feature/jai-005-source-spike` from the verified JAI-004 branch after the user approved continuing the next planned Issue.
- Corrected the task boundary after checking the Issue backlog: JAI-005 is the first real-source HTML/PDF vertical Spike; database models and migrations are JAI-006.
- Selected the official Jining public institution recruitment column for investigation. Initial web inspection confirmed discoverable announcement pages, publication metadata, body text, and direct PDF attachments.
- Compliance/access verification: `robots.txt` declared no disallowed paths; public list, detail and PDF resources returned HTTP 200 without login, CAPTCHA or browser automation. Requests were sequential, identified and spaced one second apart.
- Added deterministic CDATA list parsing, metadata/body/attachment detail parsing and page-numbered PyMuPDF extraction. Added one immutable list/detail/PDF fixture set with SHA-256 provenance and five offline regression tests.
- Added Git attributes that preserve captured HTML/PDF fixtures byte-for-byte; all three committed fixture hashes match their provenance record.
- The first static check rejected import ordering and PyMuPDF's untyped constructor boundary. Imports were normalized and the third-party call received a narrow documented Mypy suppression; subsequent checks passed.
- Offline quality gate: Ruff format/lint passed, Mypy passed across 24 files, 15 tests passed and one unrelated PostgreSQL integration test skipped; coverage was 87.57% against the 85% threshold.
- Live Spike: discovered 21 list records, extracted the selected title, publication time and 4,815 body characters, found three PDF attachments, and extracted non-empty text from all four selected PDF pages.
- Docker Desktop was initially unavailable during the first final check; the user started it and requested full verification.
- Rebuilt the API image with the new HTML/PDF dependencies and started the Compose stack. Both API and PostgreSQL reported healthy; `/health/live` returned `alive` and `/health/ready` reported the database available.
- Docker-backed final gate: Ruff format/lint passed, Mypy passed across 24 files, all 16 tests passed including the real PostgreSQL integration test, and coverage was 88.95% against the 85% threshold.
- Final audit found no current container errors and reconfirmed that every committed HTML/PDF fixture SHA-256 matches its provenance record. JAI-005 now has no outstanding verification gaps.

### 2026-08-09 — JAI-006 completed

- Created `feature/jai-006-core-models-migration` from the fully verified JAI-005 branch after the user approved continuing.
- Scope confirmed: `sources`, `crawl_runs`, `raw_documents`, `attachments`, `job_posts`, `job_positions` and `field_evidence`, plus their first Alembic migration and documentation.
- Planned invariants: timezone-aware UTC model boundaries, unique `(source_id, canonical_url)`, explicit check/index constraints, and deletion-resistant historical relationships.
- Added all seven SQLAlchemy 2 models, deterministic naming conventions, UTC-aware datetime normalization, PostgreSQL JSONB fields, relationships, indexes, and validation constraints.
- Added Alembic configuration and revision `0001_core_models`; credentials remain in normal JOBAGENT settings rather than `alembic.ini`. The API image now carries Alembic and the migration directory.
- Added model documentation and eight JAI-006 checks: four unit tests plus a PostgreSQL migration acceptance test that upgrades an empty schema, checks model drift, verifies UTC conversion, duplicate URL rejection and deletion resistance, then downgrades to base.
- The first Alembic drift check exposed double-prefixed check-constraint names and two mismatched unique-constraint names. Migration names were corrected with `op.f(...)`, and `alembic check` now reports no new upgrade operations; this check is retained in CI.
- A first local test-database creation command mishandled an empty query result; the idempotent command was corrected and `jobagent_test` was created without touching the development database.
- Quality gate: Ruff format/lint passed, Mypy passed across 29 files, all 21 tests passed with PostgreSQL, and coverage was 91.30% against the 85% threshold.
- Container verification: the Linux image built successfully; inside it, upgrade/check/current/downgrade passed on `jobagent_test`. A health request made in the first second of API recreation raced startup, then the container became healthy and readiness repeatedly returned 200.
- The local development database was non-destructively upgraded to `0001_core_models (head)` and both Compose services remain healthy.
- Three non-force push attempts failed at the GitHub HTTPS transport layer (one connection reset and two port 443 timeouts). Commits remain safe locally; no remote history was rewritten or partially updated.
- GitHub HTTPS connectivity later recovered and `feature/jai-006-core-models-migration` was pushed successfully without rewriting history.

### 2026-08-09 — JAI-007 started

- Created `feature/jai-007-source-adapter-orchestrator` from the verified JAI-006 branch because JAI-006 has not been merged into `main` or `develop`.
- Scope confirmed: Adapter registry, typed `discover`/`fetch_detail` protocol, batch orchestration, persisted step/run status and item-level error isolation.
- Planned acceptance checks: a fake Adapter completes with persisted statistics, one detail failure does not stop remaining items, and an unknown Adapter fails clearly before a crawl run starts.
- Added explicit Adapter factories, typed source/discovery/raw-document contracts, the common collection orchestrator and a SQLAlchemy crawl-run repository backed by reusable async sessions.
- Unknown/disabled/missing sources fail before a run is created; discovery failures mark the run failed and re-raise; detail failures are sanitized, persisted in statistics and isolated from later items; cancellation is persisted then propagated.
- Added ten unit acceptance checks plus a PostgreSQL repository test, and documented the batch flow, statistics schema and JAI-008 through JAI-010 boundaries.
- The first full quality gate stopped because Ruff reformats Python examples inside Markdown; `docs/COLLECTION.md` was formatted and the repeat gate passed.
- Final database-enabled gate: Ruff format/lint passed, Mypy passed across 38 files, all 32 tests passed and coverage was 91.77% against the 85% threshold.
- Production image rebuilt successfully; the recreated API and PostgreSQL containers are healthy, and `/health/ready` reports the database available.
- No migration was required because JAI-006 already provided the compatible `crawl_runs.status`, `stats`, `error_message` and timestamp columns.
- The first non-force push and a follow-up read-only `git ls-remote` check both failed because GitHub port 443 was unreachable after 21 seconds. All commits remain safe locally and no remote history changed.
- After Git for Windows was installed, the database-enabled quality gate was rerun successfully: Ruff format/lint and Mypy passed, all 32 tests passed, and coverage remained 91.77%. The next non-force push was stopped before execution because the environment requires explicit user authorization to export the branch contents to the configured GitHub remote; no remote state changed.
- After the user explicitly authorized the destination and payload, `feature/jai-007-source-adapter-orchestrator` was pushed successfully with Git for Windows and now tracks its matching origin branch. No history was rewritten.

### 2026-08-09 — JAI-001 through JAI-007 merged locally to develop

- Three fetch attempts around the merge failed because GitHub port 443 was unreachable. The local `develop` and current `origin/develop` reference both pointed to planning baseline `e72f50e`; local merges proceeded without pushing so any later remote divergence will still be rejected safely.
- Merged JAI-001 through JAI-007 in Issue order with seven non-fast-forward merge commits. Every feature tip is now an ancestor of local `develop`, and `main` remains unchanged.
- The first combined quality gate stopped at Ruff format because JAI-005 had replaced JAI-001's general `.gitattributes` line-ending policy with only fixture overrides. This made a fresh Windows checkout use CRLF for 22 code/document files.
- Restored the LF text, CRLF Windows-script and binary rules while preserving byte-exact HTML/PDF fixture overrides; `git add --renormalize .` confirmed no business-content changes were required. Integration fix commit: `b95998f`.
- Final database-enabled gate: Ruff format/lint passed, Mypy passed across 38 files, all 32 tests passed and coverage was 91.77% against the 85% threshold.
- A non-force `develop` push was stopped before execution because the environment requires explicit user authorization to export the complete merged history to the GitHub remote. No remote state changed.
- The user then explicitly authorized the `develop` push. Two non-force push attempts still timed out on GitHub port 443; DNS resolved `github.com` to `20.205.243.166`, but a direct TCP 443 diagnostic failed. The local merge history remains safe and the remote branch is unchanged.
- GitHub connectivity later recovered and the authorized non-force push succeeded, advancing remote `develop` from `e72f50e` to `1ebc071`. JAI-001 through JAI-007 are now merged remotely in order; `main` remains unchanged.

### 2026-08-09 — JAI-008 HTTP client policy completed

- Created `feature/jai-008-http-client-policy` from the verified and remotely synchronized `develop` branch.
- Scope confirmed: asynchronous HTTP client lifecycle, explicit User-Agent, source-level timeout/concurrency/minimum interval, exponential backoff, retry classification and ETag/Last-Modified conditional requests.
- Boundaries: URL normalization and idempotent raw-document persistence remain JAI-009; attachment validation and storage remain JAI-010.
- Added `SourceHttpClient`, validated source policy and cache-validator/result contracts. Retryable transport errors, HTTP 429 and 5xx responses use capped exponential backoff; permanent 4xx responses fail once; logs expose attempt counts while sanitizing request URLs.
- Added seven deterministic unit checks covering transient recovery/exhaustion, permanent 404 behavior, validator round-trips and 304 responses, independent source policy values, concurrency caps and invalid configuration.
- The first targeted static check found only import ordering/export formatting and an invariant JSON-dictionary annotation; those were corrected without suppressions. The repeated targeted Ruff, Mypy and Pytest checks passed.
- Final database-enabled quality gate: Ruff format/lint passed, Mypy passed across 40 source files, all 39 tests passed and coverage was 91.08% against the 85% threshold.
- The production image rebuilt successfully; the recreated API and PostgreSQL containers are healthy, and `/health/ready` reports the database available.
- No dependency or migration change was required: the project already depends on `httpx`, and persistent URL/cache state remains in JAI-009.
- Merged `feature/jai-008-http-client-policy` into `develop` with a non-fast-forward merge after confirming both local branches matched their remote counterparts.
- The database-enabled quality gate was rerun after the merge: Ruff format/lint and Mypy passed, all 39 tests passed, and coverage remained 91.08%. Four non-force `develop` push attempts then failed because GitHub port 443 was unreachable after about 21 seconds each; the merge remains safe locally and remote history did not change.
- GitHub connectivity later recovered and the non-force push advanced remote `develop` to merge commit `9016fb3`; local and remote `develop` were verified identical before JAI-009 started.

### 2026-08-10 — JAI-009 URL/fingerprint/idempotency completed

- Created `feature/jai-009-url-fingerprint-idempotency` from the verified and remotely synchronized `develop` branch.
- Scope confirmed: tracking-parameter removal, relative-link resolution, deterministic canonical URLs, normalized-body SHA-256 fingerprints, update detection and idempotent raw-document persistence.
- Evidence boundary: a changed page must preserve the prior raw source evidence rather than overwrite it; attachment discovery/download/storage remains JAI-010.
- Added deterministic HTTP(S) URL canonicalization with relative resolution, IDNA/default-port/path normalization, explicit tracking-parameter removal and preservation of unknown business parameters.
- Added visible-body normalization and SHA-256 fingerprints while retaining untouched HTML/text. Empty visible content and invalid URLs fail with safe permanent error codes.
- Added migration `0002_raw_document_versions`, immutable version chains, one-current-row enforcement, ETag/Last-Modified persistence and a PostgreSQL repository with advisory-lock concurrency protection.
- Added fourteen URL/content unit checks plus a PostgreSQL acceptance check proving concurrent duplicates resolve to one version, changed content creates a linked version, old evidence remains intact and cache validators round-trip.
- The first database test attempt timed out because the PostgreSQL container was stopped. After starting it, the migration test exposed an incorrect assumed predecessor revision ID; `down_revision` was corrected to the actual `0001_core_models`. A concurrency assertion was also corrected to allow either equivalent request to acquire the lock first.
- Final database-enabled quality gate: Ruff format/lint passed, Mypy passed across 43 source files, all 54 tests passed and coverage was 91.35% against the 85% threshold.
- Docker Desktop restarted during the first image build attempt, causing a 184-second timeout and temporarily invalidating the old API image reference. After the engine recovered, the production image built successfully.
- The local development database upgraded non-destructively to `0002_raw_document_versions (head)`; `alembic check` found no schema drift. The recreated API and PostgreSQL containers are healthy, and `/health/ready` reports the database available.
- Merged `feature/jai-009-url-fingerprint-idempotency` into `develop` with a non-fast-forward merge after confirming both local branches matched their remote counterparts.
- The non-force push advanced remote `develop` to merge commit `020e0b7`; local and remote `develop` were verified identical before JAI-010 started.

### 2026-08-10 — JAI-010 attachment storage completed

- Created `feature/jai-010-attachment-storage` from the verified and remotely synchronized `develop` branch.
- Scope confirmed: discover PDF/XLS/XLSX links from announcement HTML, validate URL/extension/MIME/signature, enforce a configured byte limit, compute SHA-256, persist attachment metadata and atomically place content in the local object store.
- Boundaries: document parsing, OCR, spreadsheet interpretation and golden parsing samples remain JAI-013 through JAI-016; JAI-010 stores source bytes only.
- Added canonical PDF/XLS/XLSX link discovery, safe filename handling, shared-policy streaming HTTP responses, configured header/actual-byte limits, file-signature and MIME validation, SHA-256 hashing and same-volume atomic object publication.
- Added an idempotent PostgreSQL attachment repository and migration `0003_attachment_storage`. Download state, safe failure information, byte count and timestamp are stored separately from parsing state; an advisory lock and the existing unique key prevent duplicate metadata rows.
- Added the named Compose attachment volume and verified that the non-root API user owns its configured path. Completed files use relative content-addressed paths; failed or interrupted transfers remove their temporary `.part` file.
- Added unit and PostgreSQL acceptance coverage for canonical de-duplication, invalid links, PDF/XLSX validation, generic MIME handling, both declared and streamed size overflow, HTML masquerades, interrupted bodies and repeated storage reuse.
- The first targeted static run found export ordering, a platform-safe path replacement rule and one invariant dictionary type; all were corrected without suppressions. One initial HTTP test incorrectly assumed an in-memory response remained open after its body was fully consumed; the assertion was removed and the repeated test passed.
- The first Docker inspection inside the restricted sandbox could not access the Docker named pipe. Re-running the required checks with authorized Docker access succeeded; no product change was needed.
- Final database-enabled quality gate: Ruff format/lint passed, Mypy passed across 46 source files, all 64 tests passed and coverage was 89.34% against the 85% threshold.
- Final container verification: the production image built from the completed source, the development database is at `0003_attachment_storage (head)`, API user `uid=100` can write and clean up `/app/data/attachments`, both services are healthy and `/health/ready` reports the database available.
- Implementation commit: `4176187` (`feat: add atomic attachment storage`). No known blocker remains; the feature branch is ready for review and merge.
- The first non-force feature-branch push timed out on GitHub HTTPS port 443 after 21 seconds and changed no remote state. An immediate retry succeeded; the local branch now tracks `origin/feature/jai-010-attachment-storage`.

### 2026-08-10 — JAI-036 简体中文文档同步开始

- 用户明确将简体中文文档同步提升为当前优先事项；因此在 JAI-011 之前先执行这个独立文档 Issue。
- 从尚未合并的 JAI-010 完成提交创建 `feature/jai-036-zh-cn-docs`，使中文基线包含当前附件存储版本，同时不把新范围追加到已完成的 JAI-010 分支。
- 范围确认：为纯英文的仓库说明、采集、HTTP、数据库、原始公告、附件、来源 Spike、迁移和固定样本说明建立中文镜像；已有中文文档不重复复制，历史 WORKLOG 不回译。
- 计划检查：中英文导航与相对链接、镜像清单完整性、Markdown 格式、全仓质量门禁和工作区状态。
- 已在 `docs/zh-CN/` 建立中文索引及九组镜像，保持英文原文的章节结构、代码标识符、环境变量、错误码、URL 和命令不变；每组文档提供双向链接。
- 已把同步要求写入根 `AGENTS.md` 及其中文镜像：修改英文技术文档时必须在同一提交更新中文版本；已有中文文档继续只维护一份，新增 WORKLOG 使用中文。
- 第一次相对链接检查发现中文索引指向固定样本英文说明时多返回了一层目录；修正后检查了 24 份 Markdown，所有相对链接均可解析，10 份中文文档均包含中文内容。
- 九组中英文镜像的标题层级数量逐组一致：仓库规范 7/7、采集 5/5、数据库 6/6、HTTP 4/4、原始公告 5/5、附件 6/6、来源验证 10/10、迁移 1/1、固定样本 1/1。
- 最终质量门禁：Ruff format 检查 74 个文件、Ruff lint 和 Mypy 均通过；包含 PostgreSQL 集成测试的 64 项测试全部通过，覆盖率 89.34%。
- 文档基线提交：`2b745f9`（`docs: add Simplified Chinese mirrors`）。无已知阻塞，分支可按依赖顺序在 JAI-010 之后合并。
- `feature/jai-036-zh-cn-docs` 已非强制推送并跟踪同名远程分支；远程未改写任何已有历史。
- 按用户要求先将 JAI-010 以非快进方式合并到本地 `develop`（`e0ea5d9`），再合并 JAI-036（`82adb73`）；两次合并均无冲突，两个 feature tip 均已验证为 `develop` 的祖先。
- 合并前两次 `git fetch origin` 和一次精确 `git ls-remote` 均因 GitHub HTTPS 443 在约 21 秒后超时，缓存的 `origin/develop` 仍为 `020e0b7`。最终只允许普通非强制推送，因此任何未获取到的远程分歧都会由 Git 拒绝，而不会覆盖远程历史。
- 合并后质量门禁再次通过：Ruff format 检查 74 个文件、Ruff lint 和 Mypy 通过，包含 PostgreSQL 集成测试的 64 项测试全部通过，覆盖率 89.34%。

### 2026-08-10 — JAI-011 来源网站库与首批 Adapter 开始

- 已确认本地 `develop`、缓存的 `origin/develop` 与当前 feature 分支均从 `ab4ad13` 开始；该提交包含 JAI-010、JAI-036 的有序合并，不从未合并的前序分支继续开发。
- 用户调整 JAI-011 的首阶段范围：先维护校招、江浙沪公职考试、央国企招聘官方目标网站名单，再实现可手工更新的网站库、来源级关键词过滤和初步爬虫；开发计划与 Issue 文档必须同步更新。
- 已创建 `feature/jai-011-source-catalog-sasac`。首个启用来源选用国务院国资委公开招聘栏目；动态招聘门户与报名系统只登记为待接入来源，不进行登录、表单提交、验证码处理或访问控制绕过。
- 官方来源核验覆盖全国大学生就业公共服务平台、上海学生就业创业服务网、江苏/浙江/上海人事考试与公务员主管部门、国务院国资委及代表性央企招聘门户。
- 环境限制：PowerShell 访问国资委页面时遇到 Windows TLS 连接错误；授权的 `curl.exe` 尝试未在审批窗口内完成；只读浏览器 DOM 检查被安全策略自动拒绝。不得绕过限制，改用官方公开链接、保守语义解析和可替换的离线契约样本，待网络环境可用后再执行低频线上冒烟。
- 新增 `config/source_catalog.toml`，登记 11 个官方候选来源，覆盖全国校招、江苏/浙江/上海公职考试和央国企招聘；配置加载器校验唯一标识、HTTPS、分类、地区、状态、启停关系、间隔和关键词。当前只有 `sasac-recruitment` 为 `active`/启用。
- 新增 `SasacRecruitmentAdapter`：使用公共 `SourceHttpClient`，限制详情链接为配置域名与公开招聘路径，规范化并去重 URL，按来源配置执行包含/排除关键词，支持发布时间游标，保留详情 HTML、可读文本和来源信息。`scripts/run_source_preview.py` 提供不写数据库的网站库列表与低频预览入口。
- 新增 1 个最小列表样本和 3 个详情样本；契约测试覆盖关键词优先级、URL 去重、跨域伪装链接拒绝、三种标题/日期结构、游标发现、共享 HTTP 客户端和详情获取。样本说明明确记录无法逐字节抓取的环境原因。
- 同步更新 `DEVELOPMENT_PLAN.md`、`GITHUB_ISSUES.md`、中英文 `COLLECTION.md`、中文网站库说明和中文文档索引；JAI-011 继续保持进行中，来源 2、3、完整持久化幂等验收和国资委线上冒烟尚未完成。
- 第一轮全仓门禁中，Ruff format/lint、Mypy 和 68 项非数据库测试通过，但因未设置 `JOBAGENT_TEST_DATABASE_URL` 跳过 5 项 PostgreSQL 测试，覆盖率 82.37% 未达到 85%；这是测试环境缺项，不是产品断言失败。
- Docker Desktop 原本未运行，且默认安装路径与预期不同；在授权范围内定位并后台启动实际安装程序，启动仓库 PostgreSQL 容器，确认隔离数据库 `jobagent_test` 已存在后重跑。最终门禁：81 个文件格式检查、Ruff lint、51 个源文件 Mypy 均通过，74 项测试（含 5 项 PostgreSQL 集成测试）全部通过，覆盖率 88.69%。文档相对链接检查和 `git diff --check` 通过。
- 第一阶段提交：`d693680`（`feat: add maintainable source catalog and SASAC adapter`）。提交保持在 `feature/jai-011-source-catalog-sasac`，不提前合并未完成的 JAI-011。
- WORKLOG 检查点提交：`02167f1`（`docs: record JAI-011 first source checkpoint`）。普通推送到 `https://github.com/user9527448/JobAgent-demo.git` 被安全审查拒绝，原因是需要用户再次明确确认把本次具体代码与文档发送到该具体远程；未改用 SSH 或其他方式绕过。

## 6. Next actions

### Codex

1. 获得用户对上述具体 GitHub 远程和本次提交载荷的明确授权后，非强制推送当前 JAI-011 feature 分支。
2. 网络可用时对国资委公开列表执行一次低频只读冒烟，再按网站库优先级继续来源 2、3 及持久化幂等验收。

### User

1. 不再需要本地服务时可运行 `docker compose down`；PostgreSQL 和附件卷会保留。

## 7. Update template

Use this compact format for future entries:

```markdown
### YYYY-MM-DD — JAI-XXX title

- Status/branch:
- Work completed:
- Decisions/deviations:
- Verification:
- Blockers/user action:
- Next action:
```
