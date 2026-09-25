# Manual owner actions

> 简体中文：[需要项目负责人手动执行的事项](zh-CN/MANUAL_ACTIONS.md)

This is the single queue for actions that must be performed or explicitly approved by the project
owner. It contains no credential values and is not a substitute for Issue-specific approval gates.
Update the paired files whenever an item is added, completed, deferred, or superseded.

## Current queue

| ID | Status | Owner action | Unblocks |
|---|---|---|---|
| `M-001` | Completed: 2026-09-25 | Prepare the PushPlus account and OpenAPI settings | JAI-027 G5 credential validation |
| `M-002` | Completed: 2026-09-25 | Create the local `.env` and enter both PushPlus secrets | JAI-027 G5 controlled live test |
| `A-001` | Approved and executed once: 2026-09-25 | Explicitly approve JAI-027 G5 | Business migration `0010` and one named live test |
| `A-002` | Approved: 2026-09-14 | Approve D-038/U1-R, stacked-branch order, and append-only persisted-feedback direction | Bilingual plan update and independent JAI-050 design/implementation |
| `A-003` | Completed: option 1 | Selected the “Morning Briefing” direction from three U2 options | Visual baseline for JAI-050 after A-002/U1-R |
| `A-004` | Future | Approve the JAI-051 feedback schema/API/retention boundary at U3 | Feedback migration and writes |
| `M-003` | Completed and verified | `node:24-alpine` pulled and `docker compose build api` passed | JAI-050 technical acceptance complete |
| `A-005` | Superseded: slot elapsed | The restored scheduler executed the 2026-09-15 slot before a decision was recorded | Factual record only; no retrospective approval inferred |
| `A-006` | Completed: stop only scheduler | Owner approved stopping only the scheduler; `db`/`api` remain running | No 2026-09-26 live-source slot while stopped |
| `A-007` | Partially executed: 2026-09-25 | Deploy the JAI-050 API image and approve the JAI-028 operating window | JAI-050 `/app/` is live; scheduler start is now gated by A-008 |
| `A-008` | Approved and activated: 2026-09-25 | Authorize generated report/job content through PushPlus on up to five automatic JAI-028 runs | Sole scheduler is running; count the five live trials |

`A-007` authorized the normal scheduled JAI-028 window, including public-source requests, resulting
business writes, and possible PushPlus notifications. The API deployment completed, but the runtime
safety gate requires the narrower `A-008` authorization before generated report/job content may be
sent to the external PushPlus destination on up to five automatic runs. No makeup, manual
delivery/resend, scheduler scaling, JAI-051, or JAI-029 release work is authorized. The earlier
JAI-027 one-off live notification allowance remains consumed and is not reused.

## A-007 — Deploy JAI-050 and run JAI-028 unattended acceptance

The owner approved recreating only the `api` service from the verified JAI-050 image, accepting a
brief API interruption while keeping the scheduler stopped. After `/app/`, health, and container
identity are verified, the owner also approved starting exactly one scheduler for JAI-028's five
consecutive automatic trials. Only actual scheduled runs evidenced by `pipeline_runs`, all required
stage rows, report identity, and notification ledgers count. Missing dates are not inferred, and no
manual makeup is authorized. A failure, duplicate, non-terminal run, ambiguous delivery, or loss of
the single-scheduler invariant pauses acceptance for read-only diagnosis before any further action.

If uninterrupted, the retained job row currently makes 2026-09-26 through 2026-09-30 the expected
five-run observation window. This is an expectation, not a pre-recorded result; each day is recorded
only after database evidence exists.

The API portion completed with the verified `sha256:1662d4ec...` image: the recreated container is
healthy and `/health/live`, `/health/ready`, `/app/`, and `/dashboard/briefing` all return HTTP 200.
The scheduler-start command was rejected before execution because external-content authorization was
not specific enough. Read-only verification confirmed the scheduler remains `Exited (143)`, the
next stored time remains 2026-09-26 08:00, and pipeline/delivery ledgers are unchanged. The owner then
explicitly approved `A-008`: up to five automatic scheduled runs may send their generated job/report
content to the configured PushPlus destination and may access approved public sources and write
business data. Makeup, manual send/resend, extra notification, and scheduler scaling remain forbidden;
any failure, duplicate, non-terminal state, or ambiguous delivery must pause the trial and be reported.

The first scheduler recreation exposed that the cached `jobagent-scheduler` image had the current
pipeline but an older notification-service source hash. It was stopped before the 08:00 slot and
before any pipeline or delivery row changed. A fresh image was built from the current branch; an
offline no-network check matched both critical source hashes. Exactly one scheduler now runs image
`sha256:7138bffe...` with restart count zero, and the retained next time remains 2026-09-26 08:00.

## M-003 — Restore the Docker build prerequisite

The JAI-050 Dockerfile now builds the locked frontend in a `node:24-alpine` stage. The first
`docker compose build api` reached Docker Hub but timed out while obtaining its anonymous token over
IPv6; Compose syntax is valid and no local copy of that image exists. Do not change repository
remotes, Git proxy settings, or committed Docker configuration to work around this.

When Docker Hub access is available, run this from any directory:

```powershell
docker pull node:24-alpine
```

M-003 completed on 2026-09-25. The local `node:24-alpine` digest was verified, and
`docker compose build api` completed the locked pnpm install, Vite production build, Python wheel
build, and final image export. An ephemeral image check found the built index plus JavaScript and CSS
assets. Existing `api`/`db` container IDs remained unchanged and healthy; scheduler stayed stopped.

## A-005/A-006 — Decide the restored scheduler state

Starting Docker Desktop on 2026-09-15 caused Compose's existing `restart: unless-stopped` policy to
restore the sole scheduler automatically. Read-only evidence shows its next slot is
2026-09-15 08:00 `Asia/Shanghai`. Leaving it running permits the existing four-stage production
pipeline to contact approved live sources and write business data at that time. It is not a JAI-028
trial and does not apply migration `0010`.

The 2026-09-15 slot elapsed before a decision was recorded. Read-only evidence now shows one
scheduled run for that date, succeeded once across the existing four stages, and the fixed job next
points to 2026-09-16 08:00. This fact does not retroactively approve the run and is not a JAI-028
trial.

The 2026-09-16 decision deadline elapsed without a recorded owner decision. Docker was unavailable
earlier on 2026-09-25 and was later started manually. The completed read-only audit shows one healthy
database, one healthy API, one scheduler, business Alembic `0009_pipeline_scheduling`, and exactly one
fixed job next scheduled for 2026-09-26 08:00 `Asia/Shanghai`. The only runs remain the successful
2026-09-06 makeup and successful 2026-09-15 scheduled run, each with four successful stages. There are
no run rows for 2026-09-16 through 2026-09-25, and startup logs contain no explicit misfire event.

The owner explicitly approved stopping only the scheduler. `docker compose stop scheduler` completed;
the scheduler exited with code 143 while `db` and `api` remained healthy. Read-only SQL confirmed
Alembic `0009_pipeline_scheduling`, one retained fixed job row, two succeeded runs, and eight succeeded
stage rows. The stored 2026-09-26 08:00 time is durable job state, not an active execution while the
scheduler container is stopped. Any scheduler restart requires fresh explicit approval. No makeup,
migration, delivery, or source command was performed.

## M-001 — Prepare PushPlus

Perform these steps in the PushPlus website; do not send the resulting values through chat:

1. Register/sign in, bind the receiving WeChat account, and complete provider-required identity
   verification.
2. Open **Personal Center → One-to-one push** and copy the **user token**. Do not use a message
   token: PushPlus permits either token type for basic sending, but its OpenAPI requires the user
   token, and JOBAGENT needs OpenAPI final-result reconciliation.
3. Open **Personal Center → Developer settings**, enable OpenAPI, and create a random `secretKey`
   of at least 32 mixed alphanumeric characters. Generate and store it with a password manager.
4. Add the current public egress IP of the machine running Docker to the PushPlus security-IP list.
   A missing or stale entry causes AccessKey acquisition to return 403.

Official references: [token types](https://pushplus.plus/doc/help/token.html) and
[OpenAPI setup](https://pushplus.plus/doc/guide/openApi.html).

## M-002 — Configure the ignored local file

The repository must contain a local `.env`, but Git must never contain it. If `.env` does not yet
exist, run this once from the repository root:

```powershell
Test-Path .env
Copy-Item .env.example .env
```

If `Test-Path` returns `True`, do not copy or overwrite the existing file. Open `.env` in a local
text editor and fill only the two existing empty lines:

```dotenv
JOBAGENT_PUSHPLUS_TOKEN=<PushPlus user token>
JOBAGENT_PUSHPLUS_SECRET_KEY=<PushPlus secretKey>
```

Do not put either value in `.env.example`, a command argument, shell history, a screenshot, a test
fixture, a log, a database row, Git, or chat. Do not manually create an AccessKey; JOBAGENT derives
it in memory and never persists it.

When `M-001` and `M-002` are complete, report only `M-001/M-002 complete`; do not include values.
The agent may then validate presence and pairing without printing them.

## A-001 — JAI-027 G5 approval

After credential presence is safely validated, the approval statement is:

```text
Approve JAI-027 G5 for business migration 0010 and exactly one live PushPlus test of report snapshot 2.
```

The agent-owned execution sequence is: capture a read-only business-ledger snapshot, stop the sole
scheduler, apply the additive migration, verify Alembic/drift/counts, build the approved runtime,
send snapshot ID `2` exactly once, reconcile the final provider result, and audit the delivery
ledger. The scheduler remains stopped afterward until JAI-028 activation is separately approved, so
the live test cannot silently begin the five-run acceptance period.

## A-002 — Production UI foundation approval

The recommended approval statement is:

```text
Approve D-038/U1-R: React, TypeScript, Vite, pnpm, Tailwind CSS v4, shadcn/ui with Radix, frontend/,
FastAPI same-origin production serving, JAI-050 before JAI-028, JAI-051 after JAI-028, and append-only
persisted recommendation feedback subject to U3.
```

This approval permits formal updates to both development plans and both backlogs after JAI-027 is
integrated. It does not install packages or choose a visual direction. JAI-050 must first create the
paired DESIGN.md draft and three U2 visual options.

On 2026-09-14 the project owner approved the technology, Issue insertion, and append-only persisted
feedback direction above, with one sequencing revision: because JAI-027 G5 is deferred, JAI-050 may
continue on the independent stacked branch `feature/jai-050-production-ui-foundation` created from
the current JAI-027 tip. That branch must not merge into `develop` before JAI-027 and must not absorb
JAI-027 G5, JAI-028, or JAI-051 runtime/migration acceptance. The concrete JAI-051 schema, API, and
retention boundary remain protected by separate `A-004/U3` approval.

## A-003 — JAI-050 visual-direction selection

On 2026-09-10 the project owner selected option 1, “Morning Briefing,” from three independent U2
directions. It makes the latest report and actionable job recommendations the primary reading flow,
with scheduler, pipeline, and delivery evidence as supporting information. Its restrained light
editorial layout is the visual baseline for the later production Tailwind CSS + shadcn/ui pages.

This selection completes only the visual-direction decision. It does not replace `A-002/U1-R`
approval for the technology, Issue insertion, and execution order, nor does it authorize creating a
JAI-050 branch, installing frontend dependencies, or implementing UI. When JAI-050 starts, this
direction must be translated into paired, version-controlled `docs/DESIGN.md` and
`docs/zh-CN/DESIGN.md` specifications; the preview image is neither a runtime asset nor the sole
implementation acceptance reference.

## Reusable Docker recovery

Start Docker Desktop manually when the engine is unavailable, then tell the agent only that Docker
is ready. Do not independently run migrations, makeup commands, live-source collection, scheduler
scaling, or notification commands. The agent will first perform read-only Compose and ledger checks
and will request the exact approval needed for any write.
