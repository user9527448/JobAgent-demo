# Configuration, logging, and error conventions

> 简体中文：[配置、日志与错误约定](../CONFIGURATION.md)

## Configuration

The application reads runtime configuration only from environment variables prefixed with
`JOBAGENT_`. Copy the example file before the first run:

```powershell
Copy-Item .env.example .env
```

| Environment variable | Required | Default | Meaning |
|---|---:|---|---|
| `JOBAGENT_ENVIRONMENT` | Yes | None | `development`, `test`, or `production` |
| `JOBAGENT_LOG_LEVEL` | No | `INFO` | Standard Python logging level |
| `JOBAGENT_TIMEZONE` | No | `Asia/Shanghai` | Valid IANA zone used at report and schedule boundaries |
| `JOBAGENT_APP_NAME` | No | `jobagent` | Log and service identity |
| `JOBAGENT_DATABASE_URL` | Yes | None | SQLAlchemy PostgreSQL URL |
| `JOBAGENT_FRONTEND_DIST_PATH` | No | `frontend/dist/client` | Frontend build served by FastAPI on the same origin; `/app/frontend-dist` in the image |
| `JOBAGENT_ATTACHMENT_STORAGE_PATH` | No | `data/attachments` | Attachment storage root |
| `JOBAGENT_ATTACHMENT_MAX_BYTES` | No | `26214400` | Maximum bytes per attachment |
| `JOBAGENT_ATTACHMENT_CHUNK_BYTES` | No | `65536` | Streaming attachment write size |
| `JOBAGENT_SOURCE_CATALOG_PATH` | No | `config/source_catalog.toml` | Approved source catalog |
| `JOBAGENT_SCHEDULER_HOUR` | No | `8` | Local hour for the daily schedule |
| `JOBAGENT_SCHEDULER_MINUTE` | No | `0` | Local minute for the daily schedule |
| `JOBAGENT_SCHEDULER_MISFIRE_GRACE_SECONDS` | No | `21600` | Misfire grace in seconds |
| `JOBAGENT_SCHEDULER_STAGE_MAX_ATTEMPTS` | No | `3` | Maximum transient attempts per stage |
| `JOBAGENT_SCHEDULER_RETRY_DELAY_SECONDS` | No | `30` | Base stage backoff in seconds |
| `JOBAGENT_PUSHPLUS_TOKEN` | No; required for delivery | Empty | PushPlus user token, read only from the environment |
| `JOBAGENT_PUSHPLUS_SECRET_KEY` | No; required for delivery | Empty | PushPlus OpenAPI secret key, read only from the environment |

The two PushPlus secrets must be configured together; both empty means delivery is disabled. A
single configured value, or an explicitly constructed empty `SecretStr`, is rejected at startup.
Compose passes both variables to the sole scheduler process without writing their values into the
image, command line, or repository. Real values belong only in the Git-ignored local `.env` and may
be injected only after explicit G5 approval.

Settings are cached in-process. Tests and explicit reloads may call `clear_settings_cache()`:

```python
from jobagent.core import get_settings

settings = get_settings()
```

Missing or invalid settings become non-retryable `ConfigurationError` instances; validation
details exclude the original input values.

## Secret boundary

- Tokens, secret keys, and short-lived access keys never enter Git, the database, logs, fixtures,
  or command arguments.
- The access key is cached only in provider process memory.
- URLs, request/response bodies, headers, and third-party exception text that may contain a secret
  never enter generic logging or error paths.
- `.env.example` contains empty values only; the real `.env` is never committed.
- `jobagent-delivery show` needs no PushPlus secret; `send` fails safely without a complete pair.

## Structured logging

Application entry points configure the root logger once:

```python
from jobagent.core import bind_log_context, configure_logging, get_logger, get_settings

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)

with bind_log_context(request_id="request-123", run_id="run-456", source_id=7):
    logger.info("crawler.started", extra={"discovered": 12})
```

Each line is a JSON object containing a UTC timestamp, level, logger, and event plus active async
context. Common sensitive field names are recursively redacted, including `password`, `secret`,
`token`, `api_key`, `authorization`, `cookie`, and `credential`. Never concatenate a secret into a
free-text event: arbitrary strings cannot be reliably redacted.

## Unified exceptions

| Exception | Retryable | Example use |
|---|---:|---|
| `ConfigurationError` | No | Missing variables, invalid timezone, incomplete delivery secrets |
| `TransientJobAgentError` | Yes | Connection failure, temporary source throttling, unavailable result query |
| `PermanentJobAgentError` | No | Unsupported file, stable 4xx, persisted identity conflict |

Every domain exception has a stable `code`, safe `message`, `category`, `retryable`, and structured
`details`, and can be converted to a log/API payload with `to_dict()`. Raw provider messages must
first be mapped to an allowlisted code and fixed safe explanation.

## Related documentation

- [Manual owner actions and approval queue](../MANUAL_ACTIONS.md)
- [PushPlus report delivery](../DELIVERY.md)
- [Daily scheduling, recovery, and makeup](../SCHEDULING.md)
- [Database models and migrations](../DATABASE.md)
