# JOBAGENT Repository Instructions

These instructions apply to the entire repository.

## Required context

Before changing code or project configuration, read:

1. `docs/DEVELOPMENT_PLAN.md`
2. `docs/GITHUB_ISSUES.md`
3. `docs/WORKLOG.md`

Use the planned Issue order unless the user explicitly changes the priority.

## Work log

Keep `docs/WORKLOG.md` current throughout development:

- Add an entry when an Issue starts.
- Record meaningful implementation decisions and deviations from the plan.
- Record failed checks, environment limitations, blockers, and user actions required.
- Record commands/checks and their final results when an Issue finishes.
- Update the current-status and next-action sections before handing work back.

Do not use the work log as a raw command transcript. Keep it concise, factual, and useful for resuming work.

## Git workflow

- Do not commit directly to `main` or `develop`.
- Create one feature branch per Issue using `feature/<issue>-<description>`.
- Keep each commit scoped to the active Issue.
- Run formatting, lint, type checks, and tests before pushing.
- Never rewrite published history or force-push unless the user explicitly requests it.

## Python environment

- Reuse an existing compatible Python installation; do not download a new Python version unless the user asks.
- Create and use the repository-local `.venv` for project dependencies.
- Keep `.venv`, secrets, runtime data, logs, and downloaded source files out of Git.

## Implementation boundaries

- Prefer the simplest architecture that satisfies the current MVP Issue.
- Do not add deferred technologies or features early.
- Preserve raw recruitment source data and traceability.
- Never bypass login, CAPTCHA, access controls, or source-site restrictions.
- Never commit real credentials or personal data.
