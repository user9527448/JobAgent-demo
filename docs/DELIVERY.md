# PushPlus report delivery

> Simplified Chinese: [PushPlus 日报投递](zh-CN/DELIVERY.md)

JAI-027 delivers one immutable daily-report snapshot to the personal WeChat channel through
PushPlus. Delivery is an explicit fifth pipeline stage; it is not part of report generation and
does not change the report snapshot.

## Architecture and identity

```text
report stage output: report_snapshot_id
                │
                ▼
deterministic renderer → notification_deliveries
                │             │
                │             └─ UNIQUE(report_snapshot_id, channel)
                ▼
ordered message parts → notification_delivery_attempts → PushPlus → final-result query
```

The immutable snapshot ID and fixed `pushplus_wechat` channel form the logical idempotency key.
`delivery_version`, message hash, part count, and every part hash are deterministic. If an existing
identity has different rendered content, execution stops with `notification.delivery_identity_conflict`
instead of silently changing what was sent.

The fifth pipeline stage reads the exact `report_snapshot_id` from the successful report-stage
output of the same `pipeline_run`; it never selects the latest report by date. Historical terminal
JAI-026 runs are not delivered retroactively.

## Ledger and state machines

`notification_deliveries` stores the parent status, immutable identity, timestamps, and safe error
metadata. `notification_delivery_attempts` stores each numbered part submission, optional PushPlus
`shortCode`, timestamps, hashes, and safe error metadata. Restricted foreign keys preserve both
report and attempt history.

```text
delivery: pending → sending → succeeded | failed | unknown
attempt:  submitting → accepted → succeeded
                     └──────────→ failed | unknown | interrupted
```

The parent becomes `succeeded` only after every part reaches provider-confirmed final success.
`failed` means a permanent rejection or exhausted bounded attempts. `unknown` means the provider
may have accepted a submission but the system cannot prove its final identity or result; automatic
resubmission is forbidden.

## Rendering, limits, and order

- The renderer version is `jai-027-v1` and uses the persisted Markdown snapshot.
- Each body is capped at 18,000 Unicode characters and each title at 90 characters, leaving margin
  below the provider's documented verified-user limits.
- Splitting prefers complete report sections/items, then line boundaries, then Unicode-safe slices.
- Titles include the report date and `[i/n]`; parts are submitted and confirmed sequentially.
- Provider submissions are separated by at least 13 seconds. Empty reports still produce one part.

PushPlus documents that synchronous `code=200` means accepted, not delivered, and returns a
`shortCode` for final-result lookup. The OpenAPI result endpoint reports status 0/1/2/3 for pending,
sending, sent, or failed. Current provider limits are documented as 100 title characters, 20,000
content characters, five requests per minute, and three identical messages per hour for verified
users. See the official [send API](https://www.pushplus.plus/doc/guide/api.html),
[OpenAPI](https://pushplus.plus/doc/guide/openApi.html), and
[limit guide](https://pushplus.plus/doc/help/limit.html).

## Retry and recovery

- Only a failure known to occur before submission, or an explicit temporary provider rejection,
  may create another submission attempt.
- A part receives at most three submissions with 30- and 60-second delays.
- A durable accepted `shortCode` is queried in a bounded window without resubmission. A later
  pipeline retry resumes that query.
- After a `shortCode` is durable, any error that prevents final-result lookup is recorded as
  `unknown`, even when that lookup error itself is permanent. Only an explicit provider final
  status of failed may terminate the accepted attempt as `failed`.
- A write/read timeout, malformed accepted submission response, cancellation during submission,
  or stale `submitting` attempt becomes `unknown` because external acceptance may already exist.
- A PostgreSQL session advisory lock serializes scheduler and operator work for one report/channel.
  Contention returns `locked` without a duplicate ledger row.

Raw provider URLs, bodies, headers, error messages, and transport exception strings are discarded.
Only allowlisted codes and fixed safe explanations enter the ledger or application errors.

## Configuration and secret safety

Configure both variables in the Git-ignored `.env` only after live activation is approved:

```dotenv
JOBAGENT_PUSHPLUS_TOKEN=
JOBAGENT_PUSHPLUS_SECRET_KEY=
```

Both empty means delivery is disabled; exactly one configured value is invalid. The user token and
secret key are `SecretStr` settings. The OpenAPI access key is obtained and cached in memory only.
No credential may enter Git, database rows, logs, test fixtures, command arguments, or URLs.

Before using OpenAPI result lookup, the PushPlus account must have developer access enabled, a
secret key configured, and the sending host allowed by the provider's security-IP settings.

## Operator commands

Migration `0010_notification_delivery` must be applied before either command uses the database:

```powershell
jobagent-delivery show --delivery-id 1
jobagent-delivery send --snapshot-id 2
```

- `show` needs no provider credential and returns the safe parent plus ordered attempts.
- `send` creates or resumes eligible work for one explicit immutable snapshot. A successful prior
  delivery returns `reused`; `succeeded` and `unknown` are never resubmitted automatically.
- Exit code `0` means successful/reused delivery or inspection, `2` means configuration/not-found/
  terminal failure, and `3` means lock contention.

Do not use `send` merely to test configuration: it can create real external messages. The approved
live test must name one snapshot in advance.

## Activation gates

- G4 covers paired documentation, Compose environment wiring, and the complete repository gate.
- G4 does not authorize applying `0010` to the populated business database, injecting credentials,
  starting/restarting the scheduler, running makeup, or contacting PushPlus.
- G5 separately requires a pre-migration business-ledger snapshot, explicit migration approval,
  credential injection, one named report snapshot, and exactly one controlled live test.
- JAI-028's five unattended executions begin only after JAI-027 is accepted and separately enabled.

Related references: [manual owner actions](MANUAL_ACTIONS.md),
[configuration](en-US/CONFIGURATION.md), [database](DATABASE.md), and [scheduling](SCHEDULING.md).
