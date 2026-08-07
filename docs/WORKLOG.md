# JOBAGENT Development Work Log

> Purpose: a concise, continuously updated record of progress, decisions, verification, blockers, and user actions.  
> Last updated: 2026-08-07  
> Active branch: `feature/jai-003-api-postgres-health`

## 1. Current status

| Issue | Status | Branch / commit | Notes |
|---|---|---|---|
| Project planning | Complete | `main` / `e72f50e` | Development plan and Issue backlog published |
| JAI-001 Project bootstrap | Complete, awaiting merge | `feature/jai-001-project-bootstrap` / `b965a47` | Python package, `.venv` workflow, Ruff, Mypy, Pytest |
| JAI-002 Configuration/logging/errors | Complete, awaiting merge | `feature/jai-002-config-logging` / `c6fea0e` | Typed settings, JSON logs, redaction, error taxonomy; 7 tests passed, 95% coverage |
| JAI-003 API/PostgreSQL/health | Started | `feature/jai-003-api-postgres-health` | Branch created; implementation not started |

## 2. Current blocker and user action

### Docker is not installed or not available on PATH

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
| Docker | Not installed or not on PATH as of 2026-08-07 |

## 4. Decisions

### D-001 Data pipeline before Agent

The MVP prioritizes collection, immutable raw data, attachment parsing, validation, matching, and reports. Agent capabilities remain scheduled for JAI-033 onward.

### D-002 One Issue per feature branch

Changes use `feature/<issue>-<description>` branches. JAI-002 and JAI-003 are temporarily stacked because earlier branches have not yet been merged into `develop`.

### D-003 Python environment policy

Reuse the existing Python installation and maintain dependencies in repository-local `.venv`. Do not download a new Python version unless explicitly requested.

### D-004 Persistent development record

`docs/WORKLOG.md` is updated at Issue start, meaningful decisions/blockers, verification, and completion. `AGENTS.md` makes this requirement durable for future Codex work in the repository.

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

## 6. Next actions

### Codex

1. Implement FastAPI application factory and lifecycle.
2. Add PostgreSQL async connection pool.
3. Add `/health/live` and `/health/ready` with database-aware readiness.
4. Add Dockerfile, Compose, configuration, tests, and operating instructions.
5. Run all checks that do not require Docker.
6. After Docker becomes available, run the real API + PostgreSQL acceptance test and record results here.

### User

1. Install and start Docker Desktop using the checklist above.
2. Merge the JAI-001 and JAI-002 Pull Requests in order when ready.
3. Tell Codex when Docker verification succeeds so the JAI-003 container test can run.

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
