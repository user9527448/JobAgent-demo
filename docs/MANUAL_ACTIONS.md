# Manual owner actions

> 简体中文：[需要项目负责人手动执行的事项](zh-CN/MANUAL_ACTIONS.md)

This is the single queue for actions that must be performed or explicitly approved by the project
owner. It contains no credential values and is not a substitute for Issue-specific approval gates.
Update the paired files whenever an item is added, completed, deferred, or superseded.

## Current queue

| ID | Status | Owner action | Unblocks |
|---|---|---|---|
| `M-001` | Deferred by owner | Prepare the PushPlus account and OpenAPI settings | JAI-027 G5 credential validation |
| `M-002` | Deferred by owner | Create the local `.env` and enter both PushPlus secrets | JAI-027 G5 controlled live test |
| `A-001` | Pending after `M-001`/`M-002` | Explicitly approve JAI-027 G5 | Business migration `0010` and one named live test |
| `A-002` | Approved: 2026-09-14 | Approve D-038/U1-R, stacked-branch order, and append-only persisted-feedback direction | Bilingual plan update and independent JAI-050 design/implementation |
| `A-003` | Completed: option 1 | Selected the “Morning Briefing” direction from three U2 options | Visual baseline for JAI-050 after A-002/U1-R |
| `A-004` | Future | Approve the JAI-051 feedback schema/API/retention boundary at U3 | Feedback migration and writes |

No current queue item authorizes a makeup run, a live recruitment-source request, a second live
notification, JAI-028's five unattended runs, or JAI-029 release work.

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
