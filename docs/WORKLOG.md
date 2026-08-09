# JOBAGENT Development Work Log

> Purpose: a concise, continuously updated record of progress, decisions, verification, blockers, and user actions.
>
> Last updated: 2026-08-09
>
> Active branch: `feature/jai-007-source-adapter-orchestrator`

## 1. Current status

| Issue | Status | Branch / commit | Notes |
|---|---|---|---|
| Project planning | Complete | `main` / `e72f50e` | Development plan and Issue backlog published |
| JAI-001 Project bootstrap | Complete, awaiting merge | `feature/jai-001-project-bootstrap` / `b965a47` | Python package, `.venv` workflow, Ruff, Mypy, Pytest |
| JAI-002 Configuration/logging/errors | Complete, awaiting merge | `feature/jai-002-config-logging` / `c6fea0e` | Typed settings, JSON logs, redaction, error taxonomy; 7 tests passed, 95% coverage |
| JAI-003 API/PostgreSQL/health | Complete, awaiting merge | `feature/jai-003-api-postgres-health` / `ea794e9` | FastAPI, PostgreSQL pool, health checks and Compose verified |
| JAI-004 Test/CI baseline | Complete, awaiting merge | `feature/jai-004-ci-test-baseline` / `4de39a0` | Unified quality gate, isolated PostgreSQL integration test, GitHub Actions |
| JAI-005 Real-source vertical Spike | Complete, awaiting merge | `feature/jai-005-source-spike` / `4d63e02` | Jining public recruitment list/detail/PDF technical validation |
| JAI-006 Core models/first migration | Complete, awaiting merge | `feature/jai-006-core-models-migration` / `d8c7c4f` | Seven core tables, constraints, relationships, UTC persistence and Alembic |
| JAI-007 Source Adapter/orchestrator | In progress | `feature/jai-007-source-adapter-orchestrator` | Adapter registry/protocol, batch orchestration, run statistics and item-level error isolation |

## 2. Environment readiness

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

## 6. Next actions

### Codex

1. Implement and verify JAI-007 on `feature/jai-007-source-adapter-orchestrator`.

### User

1. Merge JAI-001 through JAI-006 in order when ready.
2. Use `docker compose down` when the local services are no longer needed; the PostgreSQL volume is retained.

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
