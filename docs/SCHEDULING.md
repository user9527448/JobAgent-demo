# Daily scheduling, recovery, and makeup operations

> Simplified Chinese: [每日调度、恢复与补跑](zh-CN/SCHEDULING.md)

JAI-026 runs collection, deterministic extraction/validation, matching, and daily-report services
as one durable daily pipeline. JAI-027 adds explicit PushPlus delivery as the fifth stage.
Attachment handoff and live completeness work remain JAI-049.

## Runtime architecture

- One dedicated `AsyncIOScheduler` process is separate from FastAPI workers.
- APScheduler 3 stores its fixed job `jobagent.daily-pipeline.v1` in PostgreSQL table
  `apscheduler_jobs` with `replace_existing=True`, `coalesce=True`, `max_instances=1`, and a
  six-hour default misfire grace period.
- Exactly one scheduler service may run. APScheduler 3 does not coordinate multiple schedulers
  through a shared job store.
- A PostgreSQL session advisory lock is held across the full domain pipeline. Lock contention
  returns `locked` before a `pipeline_runs` row is written.
- `(job_name, scheduled_for)` is the immutable logical-run identity. Scheduled and manual makeup
  requests for the same local slot resume or reuse the same row.

The fixed order is:

```text
collection → deterministic extraction/validation → matching → report → delivery
```

Collection visits enabled sources in stable ID order through existing adapters and pacing.
Extraction handles current documents missing `jai-026-v1`. Matching forces the existing current
score version at the logical `scheduled_for` instant without changing user preferences. Reporting
uses the scheduled date in `Asia/Shanghai` and the existing immutable snapshot service.

Delivery resolves the exact `report_snapshot_id` from that same run's successful report-stage
output, then creates or reuses the unique report/channel ledger described in [DELIVERY.md](DELIVERY.md).
A prior terminal delivery is reused. Both provider-confirmed `succeeded` and durable-identity
`accepted` complete the pipeline successfully; permanent, retry-exhausted, or ambiguous `unknown`
delivery prevents success while preserving the report and safe delivery evidence.

## Configuration

| Variable | Default | Meaning |
|---|---:|---|
| `JOBAGENT_TIMEZONE` | `Asia/Shanghai` | IANA zone for schedule and report dates |
| `JOBAGENT_SOURCE_CATALOG_PATH` | `config/source_catalog.toml` | Approved source catalog |
| `JOBAGENT_SCHEDULER_HOUR` | `8` | Local daily hour, 0–23 |
| `JOBAGENT_SCHEDULER_MINUTE` | `0` | Local daily minute, 0–59 |
| `JOBAGENT_SCHEDULER_MISFIRE_GRACE_SECONDS` | `21600` | Latest accepted delay for a missed trigger |
| `JOBAGENT_SCHEDULER_STAGE_MAX_ATTEMPTS` | `3` | Maximum transient attempts per stage |
| `JOBAGENT_SCHEDULER_RETRY_DELAY_SECONDS` | `30` | Base delay for exponential retry |
| `JOBAGENT_PUSHPLUS_TOKEN` | Empty | PushPlus user token; requires the secret key |
| `JOBAGENT_PUSHPLUS_SECRET_KEY` | Empty | PushPlus OpenAPI secret key; requires the token |

Only `TransientJobAgentError` is retried, with default delays of 30 and 60 seconds. Permanent and
unexpected failures stop downstream work and retain a safe error code/type. A final collection
attempt that has at least one successful source continues as `partial` while preserving failures.
Delivery submission retries have their own persistent three-attempt ledger. A durable provider
identity with no obtainable final receipt becomes terminal `accepted`; ambiguous submission
acceptance becomes `unknown`. Neither is retried automatically.

## Operator commands

Apply the current source migration head (`0012_delivery_accepted`) before running this five-stage
scheduler build. The populated business database remains at `0011_delivery_operator_audit`; do not
migrate it, rebuild/recreate the runtime, or restart the long-lived scheduler until the relevant
runtime gate is explicitly approved and both delivery secrets are ready.

```powershell
jobagent-scheduler start
jobagent-scheduler makeup --date 2026-09-06
jobagent-scheduler show --run-id 1
```

- `start` first marks stale `running` stage attempts as `interrupted`, resumes incomplete runs in
  oldest-first order, and then starts the persistent daily scheduler.
- `makeup` converts the supplied local date to the configured daily slot. It cannot create a
  second run for an existing logical slot.
- `show` emits the run and every ordered stage attempt, including record IDs, versions, counts,
  statuses, and safe error metadata.

Development makeup remains explicit and is already audited by `pipeline_runs.trigger=makeup` plus
append-only numbered `pipeline_stage_runs`; it never erases the failed scheduled run or stage.
Migration `0011` adds the separate operator authorization ledger only for the higher-risk provider
resend boundary, where an ambiguous external identity must be preserved. G1 tests both recovery
ledgers only on `_test`; it does not authorize running `makeup`, restarting the scheduler, or
contacting a real provider.

A-012 G3 later provided one narrow exception: apply `0011` to the business database and run exactly
one 2026-09-27 makeup with one PushPlus submission for its new report. That allowance is consumed.
Run `6` ended `failed` because delivery finality remained `unknown`; the formal scheduler stayed
stopped and no further makeup, resend, provider call, or scheduler restart is authorized.

A-013 G1 changes only source, migration, UI, and offline/`_test` evidence. After `0012`, a run may
complete when every message part is either provider-confirmed `succeeded` or terminal `accepted`
with a durable message identity. Historical run `6` and delivery/attempt `3` remain unchanged;
business migration, runtime image replacement, scheduler restart, provider calls, makeup, and
resend each require a later explicit gate.

Collection stage output records attempted, successful, partial, and failed source IDs. When only a
subset fails transiently, the next bounded stage attempt targets those retryable failed IDs instead
of recollecting healthy sources, while its output retains cumulative source and crawl-run evidence.
The latest persisted attempt restores this retry selection after process restart; older ledger rows
without source identities safely retain full-stage retry behavior.

Exit code `0` means completed/reused inspection success, `2` means a failed/not-found operation,
and `3` means another process holds the pipeline lock.

Delivery has a separate explicit operator boundary:

```powershell
jobagent-delivery show --delivery-id 1
jobagent-delivery send --snapshot-id 2
```

`show` is read-only and credential-free. `send` may contact PushPlus and therefore requires a named
snapshot and live-send approval; see [DELIVERY.md](DELIVERY.md).

## JAI-028 daily full-flow evidence

JAI-028 treats each counted scheduled run as an initial end-to-end quality observation, not merely
as a terminal-status check. The collection stage must prove that the real adapters attempted every
enabled official source and must retain per-source list/detail outcomes, crawl-run identities,
`created`/`updated`/`skipped`/`failed` counts, content-version evidence, and deduplication results. A
successful source check with zero new announcements is a valid fresh observation; missing or failed
collection evidence is not.

The same daily scorecard then follows extraction/validation, matching, report generation, and
delivery. It records source availability, field completeness, parsing success, validation findings,
match/report counts, delivery finality, retries, per-stage and total duration, and announcement or
notification duplicates. After the fifth successful observation, JAI-028 ranks improvement
recommendations by impact and effort. This evidence definition does not itself authorize container
starts, public-source/provider calls, database migration, makeup, resend, or scheduler restart.

## Recovery and traceability

Successful or partial stages are never replayed during recovery. A previously `running` stage is
closed as `interrupted`, then receives the next numbered attempt. Each stage output records its
existing artifact identity: collection `crawl_run_ids`; extraction document/post/position IDs and
version; matching result IDs and score version; reporting snapshot ID/version/content hash.

The delivery stage records delivery ID, report snapshot ID, channel, part count, dispatch status,
and safe final state. Accepted `shortCode` values remain in the delivery-attempt ledger rather than
the pipeline output.

Compose passes optional PushPlus variables only to the scheduler. Empty values leave delivery
unconfigured; after migration, a scheduled delivery stage then fails safely instead of contacting a
provider. JAI-026/JAI-027 database tests use only a guarded database whose name ends in `_test` and
replace public HTTP/provider traffic with synthetic boundaries.

## A-013 G2 runtime activation and replacement observation window

On 2026-09-28 the owner approved and G2 completed the populated-business migration to
`0012_delivery_accepted`, rebuilt the API and scheduler images, activated the updated `/app/`, and
verified the sole scheduler was still stopped before the new window was enabled. The scheduler
startup path replaces the persisted cron job before processing due jobs, so the stale
2026-09-28 08:00 row advanced to 2026-09-29 08:00 `Asia/Shanghai` without a makeup run.

The replacement JAI-028 window is 2026-09-29 through 2026-10-03. The production pipeline remains
scheduled for 08:00 `Asia/Shanghai`; automation `jai-028` performs its evidence audit at 08:15
`Asia/Shanghai`. All five outcomes are visible: success, failure, missing run, or still-running
bounded-wait status. Only the real automatic run for each named date can count. No makeup, manual
send/resend, scheduler expansion, automatic job application, early JAI-051/JAI-029 work, or silent
implementation of scorecard recommendations is authorized.
