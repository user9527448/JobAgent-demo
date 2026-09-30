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
| `A-008` | Paused after first run: 2026-09-26 | Authorize generated report/job content through PushPlus on up to five automatic JAI-028 runs | First run failed with an ambiguous delivery; 0/5 counted |
| `A-009` | Anomaly action executed: 2026-09-26 | Authorize a five-day thread automation to audit each run, stop scheduler on anomalies, and commit/push bilingual evidence | Scheduler stopped; failed/unknown evidence preserved |
| `A-010` | Retest failed: provider `403` | Verify PushPlus OpenAPI credentials/IP allowlist locally and approve any remediation test, scheduler restart, and replacement observation window | Security-IP configuration still blocks AccessKey |
| `A-011` | G1 complete; G2 returned provider `403`; G2.1 lookup complete and the owner confirmed the security IP was saved | Preserve the append-only recovery controls; use them only under a separately recorded execution gate | G3 later applied `0011`; authentication remains unverified and resend/scheduler restart remain gated |
| `A-012` | G3 executed once; delivery remained `unknown` | Decide provider allowlist remediation versus a separately designed finality strategy; approve any later real call separately | Business DB is at `0011`; run `6` failed safely after one PushPlus submission; scheduler remains stopped and JAI-028 is 0/5 |
| `A-013` | G2 completed; replacement window interrupted | Apply terminal `accepted`, migrate the business DB, deploy the runtime, and restart five visible observations | Business DB/API/page are at `0012`; 2026-09-29/30 scheduled runs are missing, scheduler stopped, and a new window needs approval |
| `A-014` | G1 approved and executed once: 2026-09-28 | Run one controlled production-like full-flow makeup for 2026-09-28 | Run `8` succeeded; snapshot `6` and delivery/attempt `4` are terminal `accepted`; it does not count toward the unattended 0/5 |
| `A-015` | Approved and consumed once: 2026-09-30 | Run one date-specific production-like makeup without starting scheduler | Run `9` is `partial` after China Mobile discovery failure; snapshot `7` and delivery/attempt `5` are terminal `accepted`; still 0/5 |

`A-007` authorized the normal scheduled JAI-028 window, including public-source requests, resulting
business writes, and possible PushPlus notifications. The API deployment completed, but the runtime
safety gate requires the narrower `A-008` authorization before generated report/job content may be
sent to the external PushPlus destination on up to five automatic runs. A-012 G3 later authorized
and consumed one diagnostic makeup/submission without changing the 0/5 acceptance count. A-014 and
A-015 each later authorized and consumed one separate date-specific makeup. No further
business migration, runtime replacement, makeup, manual delivery/resend, scheduler start/scaling,
JAI-051, or JAI-029 release work is authorized.
The earlier JAI-027 one-off live notification allowance remains consumed and is not reused.

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

An attempt to create the five-day verification heartbeat was rejected before creation because the
owner had not separately authorized recurring ledger reads, anomaly-triggered scheduler stops,
paired-document edits, and normal Git commits/pushes. No automation exists yet and the scheduler was
not changed. `A-009` is required to make daily verification itself unattended.

The owner explicitly approved `A-009` for 2026-09-26 through 2026-09-30. After each planned run,
the thread automation may read Docker and business-ledger state; on success it may update paired
WORKLOG/planning status, run documentation checks, and normally commit/push the JAI-028 feature
branch. On failure, duplicate, non-terminal timeout, ambiguous delivery, multiple schedulers, or image
anomaly it must immediately stop the scheduler and notify the owner, with no makeup or resend. After
the fifth success it must stop the scheduler, run final JAI-028 gates, and push closure evidence, but
must not merge `develop` or start a later Issue.

On 2026-09-27 the owner expanded JAI-028 acceptance into an initial full-flow quality baseline. A
counted day must include evidence that the real crawler checked every enabled source, distinguish a
successful zero-change check from collection failure, and score collection freshness/change,
deduplication, extraction/validation, matching, report, delivery, retries, and duration. The fifth
successful observation produces prioritized recommendations only. This scope refinement does not
restore any consumed or paused runtime approval and does not authorize an authentication retest,
container/scheduler start, makeup, resend, migration, or external call.

The thread heartbeat was created successfully as automation `jai-028`, active for five daily checks
at 08:15 `Asia/Shanghai`. Because creation occurred after the 2026-09-25 check time, its five
occurrences cover 2026-09-26 through 2026-09-30. Viewing the saved automation confirmed it remains
active. The first two creation attempts made no automation or runtime change: one had a local call
syntax error, and one was rejected because immediate creation must omit an explicit DTSTART.

The first scheduled trial ran once at 08:00 on 2026-09-26. Collection recovered on its third attempt,
and extraction, matching, and report generation succeeded, but delivery reconciliation returned
`pushplus.access_key_rejected`. Pipeline run `4` is therefore `failed`, while delivery `2` and its
only attempt `2` remain `unknown` with the durable provider identity intact. Under A-009 the sole
scheduler was stopped and verified `Exited (143)`; `api` and `db` remain healthy. No makeup, resend,
status repair, or duplicate attempt occurred, and the acceptance count remains 0/5. At the 09:30
audit no 08:15 automation evidence commit was present, so future unattended monitoring must also be
diagnosed before reliance.

## A-010 — Resolve the PushPlus OpenAPI blocker before resuming JAI-028

The owner confirmed a user token, enabled OpenAPI, matching `secretKey`, and reported adding the
Docker public egress IPv4. A single real credential-only check then called only `getAccessKey`; it
returned HTTP 200 with provider code `403` and no AccessKey. It made no `/send` call or database
write, and its disposable container was removed. The formal scheduler was separately found running
from 12:12 and was stopped again at 12:42; no new ledger row appeared. The PushPlus security-IP
configuration must therefore be corrected and re-saved before another separately approved check.

## A-011 — Add an audited development-only makeup/resend path

The owner approved G1 on 2026-09-26: implement additive migration `0011`, the append-only operator
event ledger, and an explicit development-only resend CLI, and verify them only with an `_test`
database and synthetic provider. The implementation creates a new attempt instead of mutating the
prior `unknown` attempt, writes authorization and start events before provider interaction, appends
the safe completion result, and leaves production deny-by-default. Existing makeup remains explicit
and is audited by its immutable run identity, `trigger=makeup`, and numbered stage rows.

G1 does not permit applying `0011` to the business database, calling PushPlus, performing a real
resend or makeup, checking real credentials, or restarting the scheduler. Those effects require a
separately approved next gate after authentication is known to work.

The owner then approved G2 for exactly one credential-only `getAccessKey` retest. The disposable
container received HTTP 200 but provider business code `403`, with no AccessKey. It was removed
automatically; the formal scheduler remained `Exited (143)`. No `/send`, business-database write,
migration, makeup, or scheduler start occurred. Work stopped as required, and no real recovery gate
is available until the PushPlus security-IP/credential configuration is corrected and another
credential-only retest is separately approved.

The owner approved G2.1 for one public-egress IPv4 lookup from a disposable scheduler-service
container. The lookup succeeded and the value was reported directly to the owner for manual
comparison; it is intentionally not committed because repository history must not retain personal
network metadata. The container was removed automatically, `db`/`api` remained healthy, and the
formal scheduler remained `Exited (143)`. The owner later confirmed that the matching PushPlus
security-IP entry was saved, but that configuration action is not proof that authentication now
works. G2.1 made no PushPlus or business request and unlocks no credential retest or recovery action.

## A-012 — Controlled real full-flow diagnosis

The owner approved a direct JAI-028 diagnostic from live official-source collection through
extraction/validation, matching, report generation, and PushPlus notification, followed by scoped
defect diagnosis and repair. Execute it in gates: first one credential-only `getAccessKey` check; if
that succeeds, take a read-only business-ledger baseline, apply additive migration `0011`, verify
schema and runtime image identity, and trigger at most one current-date full-flow run. Preserve every
attempt and stop on ambiguous delivery instead of silently resending. Code fixes may use offline,
`_test`, and synthetic-provider verification; another real provider submission still needs a new
recorded execution decision when duplicate risk exists.

“Delivery” in this approval means PushPlus delivery of the generated briefing. It does not authorize
automatic job applications, résumé submission, form filling, account login, CAPTCHA handling, or
any action on recruitment portals. Product output must provide evidenced official announcement and
application links for the user to open and act on manually. JAI-028 scorecards therefore include
official-link presence, provenance, safety, and completeness without submitting any application.

On execution, Docker Desktop had automatically restored one scheduler together with healthy `db`
and `api`. Read-only evidence showed no 2026-09-27 pipeline/crawl row and the fixed job next at
2026-09-28 08:00, so the scheduler was stopped before diagnosis. The actual credential request still
returned provider `403`. PushPlus documents `403` as an unauthorized request IP; the current egress
IPv4 was reported directly to the owner and intentionally omitted here. No migration, source access,
report generation, provider submission, or job application followed.

The owner then approved `A-012 G3` despite the remaining credential-only `403`. This one-time gate
allowed the additive business migration to `0011`, exactly one 2026-09-27 makeup, approved public
source access and business writes, and exactly one PushPlus submission for the newly generated
report. It explicitly continued to prohibit historical resend, duplicate submission, scheduler
restart, and automatic job application, and declared that this diagnostic could not count toward the
five unattended successes.

G3 completed within that boundary. Business Alembic is `0011_delivery_operator_audit`; the formal
scheduler remained stopped. Pipeline run `6` ultimately collected all five sources after two
transient China Mobile failures, generated snapshot `5`, and submitted its single message part once.
The provider identity was retained, but the final-status lookup still returned
`pushplus.access_key_rejected`, so delivery/attempt `3` are terminal `unknown` and the pipeline is
`failed`. No operator resend event, second provider submission, or job-application action occurred.
Any later provider call, makeup/resend, or scheduler restart needs a new recorded approval.

## A-013 — Provider-accepted terminal delivery

The owner approved G1 for the PushPlus `accepted` terminal strategy. When `/send` has returned and a
durable provider message identity is stored, bounded receipt-query failure or exhaustion terminates
the attempt and parent as `accepted`, not `unknown`. Only provider-confirmed final success is
`succeeded`; `unknown` is reserved for ambiguous submission acceptance. `accepted`, `succeeded`, and
`unknown` all block automatic resubmission. The pipeline may complete on `accepted`, while the page
must explicitly say that final delivery is unconfirmed.

G1 is limited to migration `0012`, the state machine, read-only page presentation, and offline/
`_test` tests. It does not migrate or reclassify the populated business database, rebuild/recreate a
runtime container, call PushPlus, start the scheduler, run makeup, or resend. Historical run `6` and
delivery/attempt `3` remain authoritative and unchanged. A later gate must separately approve the
business migration, runtime image replacement, and any replacement observation window.

The post-run offline audit matched the repository request shape to the current official PushPlus
OpenAPI contract and found no client-side path, JSON-field, header, or result-query mismatch.
Provider code `403` remains documented as unauthorized request IP. The next owner action is therefore
to resolve provider-side allowlist recognition or approve a separately designed finality strategy;
neither choice authorizes another real call by itself.

The owner subsequently approved G2. The business database migrated from `0011` to
`0012_delivery_accepted` with no drift; all three historical delivery/attempt pairs remained
`unknown`. New API and scheduler images were built, the API and `/app/` were recreated and verified,
and the sole scheduler was recreated while stopped. After G2 verification, the same approval
activated exactly one scheduler and replaced the observation window with 2026-09-29 through
2026-10-03. The pipeline runs at 08:00 and automation `jai-028` audits at 08:15, both explicitly in
`Asia/Shanghai`. Success, failure, missing, and still-running outcomes must all be visible. No
2026-09-28 makeup, historical resend, manual send, scheduler expansion, automatic application,
JAI-051/JAI-029 start, or develop merge is approved.

## A-014 — One controlled production full-flow test

The owner explicitly approved exactly one 2026-09-28 `makeup` after clarifying that “full test”
meant the real production feature path, not only the repository regression suite. This gate allowed
all enabled public sources, business writes, and exactly one PushPlus submission for the new report.
It did not authorize a second invocation, historical resend, duplicate submission, automatic job
application, or counting the result in the replacement five-day unattended sequence. Failure,
ambiguous delivery, or a non-terminal ledger required stopping the sole scheduler.

Execution created run `8`, which completed all five stages once and succeeded. All 5/5 sources
succeeded; 30 details succeeded, two documents were created, 28 were skipped by deduplication, and
none failed. Snapshot `6` contains 13 items. Delivery/attempt `4` each have one row and end as
`accepted` with a durable provider identity; no duplicate group or operator resend event exists.
The page shows the accepted evidence. Because `accepted` is the A-013 safe terminal and is not an
ambiguous submission, the scheduler remains running for the 2026-09-29 unattended start.

## A-015 — One controlled 2026-09-30 makeup after missing scheduled runs

The owner approved exactly one 2026-09-30 makeup after a read-only audit found no scheduled run on
either 2026-09-29 or 2026-09-30 and the formal scheduler already stopped. This gate allowed reads
from enabled public sources, business writes, and exactly one PushPlus submission for the new
report. It did not authorize a second makeup, historical resend, automatic job application,
scheduler activation, or unattended-trial credit.

The single invocation created run `9`, which ended `partial` after the China Mobile list discovery
failed in all three bounded collection attempts. Four other sources succeeded; six new raw
versions were extracted, matched, and included in snapshot `7`. Delivery/attempt `5` each have
one row and safely ended `accepted` with a durable provider identity after one submission, but
final delivery is unconfirmed. The scheduler remains stopped and JAI-028 remains 0/5. Any new
five-day window, scheduler start, makeup, or resend requires a separate owner decision.

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
