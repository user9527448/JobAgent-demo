# JOBAGENT Repository Instructions

These instructions apply to the entire repository.

Simplified Chinese mirror: [`docs/zh-CN/AGENTS.md`](docs/zh-CN/AGENTS.md). Keep both versions synchronized.

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

## Documentation language synchronization

- Maintain project documentation in two separate files: one English version and one Simplified Chinese version.
- Never satisfy a translation requirement by changing an established English file into Chinese, or an established Chinese file into English. Preserve each file's language and update its counterpart instead.
- Existing English documents use mirrors under `docs/zh-CN/`; existing Chinese documents must gain English counterparts under `docs/en-US/` unless an established English path already exists.
- Update both language versions in the same commit. A new document must be created in both languages and added to the relevant indexes in that commit.
- A legacy single-language document must receive its missing counterpart no later than its next substantive update. Do not change its primary language while waiting for migration.
- Treat the current mixed-language `docs/WORKLOG.md` history as a legacy migration item. Do not continue switching languages inside one file as a substitute for separate English and Chinese logs; preserve existing history when the pair is split.
- Do not translate code identifiers, environment variables, error codes, URLs, or commands.

## Git workflow

- Do not commit directly to `main` or `develop`.
- Create one feature branch per Issue using `feature/<issue>-<description>`.
- Keep each commit scoped to the active Issue.
- Run formatting, lint, type checks, and tests before pushing.
- Never rewrite published history or force-push unless the user explicitly requests it.

## Git authorship

- Use the repository-local Git author identity copied from the user's existing machine-level Git configuration for new commits, unless the user explicitly requests another identity.
- Do not use placeholder identities such as `Codex Agent` or an `@local` email address for new commits.
- Verify `git config --local user.name` and `git config --local user.email` before committing after an environment or workspace change.
- Apply authorship changes only to future commits. Do not rewrite published history merely to change contributor attribution.
- Contributor attribution on GitHub requires the commit email to be associated with and verified by the user's GitHub account; never commit credentials or authentication tokens.

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
