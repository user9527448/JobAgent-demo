# 配置、日志与错误约定

## 配置

应用使用 `JOBAGENT_` 前缀的环境变量。首次运行前复制示例文件：

```powershell
Copy-Item .env.example .env
```

当前配置：

| 环境变量 | 必填 | 默认值 | 说明 |
|---|---|---|---|
| `JOBAGENT_ENVIRONMENT` | 是 | 无 | `development`、`test` 或 `production` |
| `JOBAGENT_LOG_LEVEL` | 否 | `INFO` | Python 标准日志级别 |
| `JOBAGENT_TIMEZONE` | 否 | `Asia/Shanghai` | 有效的 IANA 时区 |
| `JOBAGENT_APP_NAME` | 否 | `jobagent` | 日志和服务标识 |
| `JOBAGENT_DATABASE_URL` | 是 | 无 | SQLAlchemy PostgreSQL URL，推荐 `postgresql+psycopg://...` |

配置在进程内缓存。测试或明确需要重新载入时，调用 `clear_settings_cache()`。

```python
from jobagent.core import get_settings

settings = get_settings()
```

缺失或非法配置会转换为不可重试的 `ConfigurationError`，并且错误详情不会包含原始配置值。

## 结构化日志

应用入口负责配置一次根日志器：

```python
from jobagent.core import bind_log_context, configure_logging, get_logger, get_settings

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)

with bind_log_context(request_id="request-123", run_id="run-456", source_id=7):
    logger.info("crawler.started", extra={"discovered": 12})
```

每行日志是一个 JSON 对象，固定包含 UTC 时间、级别、logger 和事件，并自动附加当前异步上下文中的关联字段。

常见敏感字段名会递归遮蔽，包括 `password`、`secret`、`token`、`api_key`、`authorization`、`cookie` 和 `credential`。不要把密钥拼接到自由文本事件名中，因为任何日志系统都无法可靠识别任意字符串中的秘密。

## 统一异常

| 异常 | 是否可重试 | 用途示例 |
|---|---:|---|
| `ConfigurationError` | 否 | 缺失环境变量、非法时区 |
| `TransientJobAgentError` | 是 | 网络超时、来源临时限流 |
| `PermanentJobAgentError` | 否 | 不支持的文件、永久 4xx |

所有业务异常都包含稳定的 `code`、用户可理解的 `message`、`category`、`retryable` 和结构化 `details`，可通过 `to_dict()` 转换为日志或 API 响应负载。
