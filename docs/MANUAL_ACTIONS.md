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
| `M-003` | Pending | Restore Docker Hub access or pre-pull `node:24-alpine` | JAI-050 container-build verification |
| `A-005` | Superseded: slot elapsed | The restored scheduler executed the 2026-09-15 slot before a decision was recorded | Factual record only; no retrospective approval inferred |
| `A-006` | Expired unresolved; runtime unavailable 2026-09-23 | After Docker returns, review the read-only ledger audit before deciding whether the scheduler remains enabled | Current operating state; no retrospective inference or makeup |
| `M-004` | Completed: 2026-09-23 | Supplied the shared Feishu Bitable link and authorized read-only G1 inspection | JAI-052 G1 structural/source audit |
| `A-007` | Pending after completed G1 | Approve the bounded JAI-052 G2 source scope, identity, canonical reuse, normalization, disappearance, and offline implementation rules | Offline importer implementation against synthetic fixtures |

No current queue item authorizes a makeup run, a live recruitment-source request, a second live
notification, JAI-028's five unattended runs, or JAI-029 release work.

## M-003 — Restore the Docker build prerequisite

The JAI-050 Dockerfile now builds the locked frontend in a `node:24-alpine` stage. The first
`docker compose build api` reached Docker Hub but timed out while obtaining its anonymous token over
IPv6; Compose syntax is valid and no local copy of that image exists. Do not change repository
remotes, Git proxy settings, or committed Docker configuration to work around this.

When Docker Hub access is available, run this from any directory:

```powershell
docker pull node:24-alpine
```

Report only `M-003 complete`. The agent will rerun `docker compose build api`; do not recreate or
restart the current Compose services as part of this item.

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

The 2026-09-16 decision deadline elapsed without a recorded decision. On 2026-09-23 the Docker
Desktop Linux engine was unavailable, so no read-only evidence exists here for scheduled records
from 2026-09-16 through 2026-09-23. The earlier running/next-slot statement is stale and must not be
used to infer success, failure, misfire, or current scheduler state. After Docker returns, the agent
must first read Compose, Alembic, APScheduler, `pipeline_runs`, and `pipeline_stage_runs` evidence.
The owner then decides the scheduler state; no makeup, migration, delivery, or source command is
authorized by A-006.

## M-004/A-007 — Supply and approve the spreadsheet source

For `M-004`, send only the workbook link and state that read-only G1 inspection is authorized. If
the link requires a login, token, cookie, password, or private sharing grant, do not paste it into
chat or commit it. State only that authentication is required; G1 will record the provider boundary
and propose an environment-variable or approved connector approach for separate approval.

G1 may inspect workbook structure and update semantics only. It does not authorize a database
migration, production import, recurring fetch, workbook write, Agent implementation, crawler
change, or access-control bypass. After G1, the agent will present an evidence-based mapping for
`A-007/G2`, including row identity, missing-row semantics, refresh frequency, and credential
boundary. Approving G2 permits implementation with synthetic fixtures only; production activation
remains behind later JAI-052 gates.

`M-004/G1` completed on 2026-09-23. The public share proved view/preview-only access, a 10,082-record
main jobs table, 18 fields, and daily modification metadata. No source state, database, file, or
scheduler was changed. The exact shared URL and response data remain outside Git. The shared source
is permanently non-writable from JOBAGENT: no later gate may authorize cell, view, filter, sort,
comment, sharing, or permission changes.

The recommended `A-007/G2` approval statement is:

```text
Approve JAI-052 A-007/G2: ingest only the main jobs table initially; use provider/workbook/table/record
identity; reuse the existing source, crawl-run, raw-document, job-post, and job-position domain; build
only a provider-neutral read-only snapshot reader, deterministic feishu-rollup-v1 mapping, synthetic
fixtures, and _test-database tests; treat missing records as not_observed without deletion; never write
back to Feishu. Real recurring retrieval, business-database changes, Agent/UI work, and all source
writes remain unauthorized.
```

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
