# JOBAGENT Development Work Log

> Purpose: a concise, continuously updated record of progress, decisions, verification, blockers, and user actions.
>
> Last updated: 2026-08-08
>
> Active branch: `feature/jai-004-ci-test-baseline`

## 1. Current status

| Issue | Status | Branch / commit | Notes |
|---|---|---|---|
| Project planning | Complete | `main` / `e72f50e` | Development plan and Issue backlog published |
| JAI-001 Project bootstrap | Complete, awaiting merge | `feature/jai-001-project-bootstrap` / `b965a47` | Python package, `.venv` workflow, Ruff, Mypy, Pytest |
| JAI-002 Configuration/logging/errors | Complete, awaiting merge | `feature/jai-002-config-logging` / `c6fea0e` | Typed settings, JSON logs, redaction, error taxonomy; 7 tests passed, 95% coverage |
| JAI-003 API/PostgreSQL/health | Complete, awaiting merge | `feature/jai-003-api-postgres-health` / `ea794e9` | FastAPI, PostgreSQL pool, health checks and Compose verified |
| JAI-004 Test/CI baseline | Complete, awaiting merge | `feature/jai-004-ci-test-baseline` / `4de39a0` | Unified quality gate, isolated PostgreSQL integration test, GitHub Actions |

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

## 6. Next actions

### Codex

1. Start JAI-005 SQLAlchemy base and Alembic setup after the stacked Pull Requests are merged or the user approves continued stacking.

### User

1. Merge the JAI-001 through JAI-004 Pull Requests in order when ready.
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
