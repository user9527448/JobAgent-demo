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
A successful prior delivery is reused. Permanent, retry-exhausted, or ambiguous terminal delivery
prevents a successful pipeline result while preserving the report and safe delivery evidence.

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
Delivery submission retries have their own persistent three-attempt ledger; an ambiguous external
outcome becomes `unknown` and is not retried automatically.

## Operator commands

Apply migration `0010` before running the five-stage scheduler. Do not migrate or restart the
long-lived scheduler against a populated business database until the G5 runtime gate has been
explicitly approved and both delivery secrets are ready.

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

Exit code `0` means completed/reused inspection success, `2` means a failed/not-found operation,
and `3` means another process holds the pipeline lock.

Delivery has a separate explicit operator boundary:

```powershell
jobagent-delivery show --delivery-id 1
jobagent-delivery send --snapshot-id 2
```

`show` is read-only and credential-free. `send` may contact PushPlus and therefore requires a named
snapshot and live-send approval; see [DELIVERY.md](DELIVERY.md).

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
