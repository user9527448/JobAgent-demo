# 配置、日志与错误约定

> English: [Configuration, logging, and error conventions](en-US/CONFIGURATION.md)

## 配置

应用只通过带 `JOBAGENT_` 前缀的环境变量读取运行配置。首次运行前复制示例文件：

```powershell
Copy-Item .env.example .env
```

| 环境变量 | 必填 | 默认值 | 说明 |
|---|---:|---|---|
| `JOBAGENT_ENVIRONMENT` | 是 | 无 | `development`、`test` 或 `production` |
| `JOBAGENT_LOG_LEVEL` | 否 | `INFO` | Python 标准日志级别 |
| `JOBAGENT_TIMEZONE` | 否 | `Asia/Shanghai` | 有效 IANA 时区；用于日报和调度边界 |
| `JOBAGENT_APP_NAME` | 否 | `jobagent` | 日志和服务标识 |
| `JOBAGENT_DATABASE_URL` | 是 | 无 | SQLAlchemy PostgreSQL URL |
| `JOBAGENT_ATTACHMENT_STORAGE_PATH` | 否 | `data/attachments` | 附件根目录 |
| `JOBAGENT_ATTACHMENT_MAX_BYTES` | 否 | `26214400` | 单个附件最大字节数 |
| `JOBAGENT_ATTACHMENT_CHUNK_BYTES` | 否 | `65536` | 附件流式写入块大小 |
| `JOBAGENT_SOURCE_CATALOG_PATH` | 否 | `config/source_catalog.toml` | 已审批来源清单 |
| `JOBAGENT_SCHEDULER_HOUR` | 否 | `8` | 每日计划的本地小时 |
| `JOBAGENT_SCHEDULER_MINUTE` | 否 | `0` | 每日计划的本地分钟 |
| `JOBAGENT_SCHEDULER_MISFIRE_GRACE_SECONDS` | 否 | `21600` | misfire 宽限秒数 |
| `JOBAGENT_SCHEDULER_STAGE_MAX_ATTEMPTS` | 否 | `3` | 每阶段瞬时失败最大尝试数 |
| `JOBAGENT_SCHEDULER_RETRY_DELAY_SECONDS` | 否 | `30` | 阶段指数退避基准秒数 |
| `JOBAGENT_PUSHPLUS_TOKEN` | 否；启用投递时必填 | 空 | PushPlus 用户 token，仅从环境读取 |
| `JOBAGENT_PUSHPLUS_SECRET_KEY` | 否；启用投递时必填 | 空 | PushPlus OpenAPI secret key，仅从环境读取 |

PushPlus 两项密钥必须同时配置；两项均为空表示未启用投递。只配置一项、或直接构造空的
`SecretStr`，启动时都会被拒绝。Compose 把两项变量传给唯一 scheduler 进程，但不把值写入镜像、
命令行或仓库。真实密钥只能写入被 Git 忽略的本地 `.env`，并且只有 G5 明确批准后才可注入。

配置在进程内缓存。测试或明确需要重新载入时调用 `clear_settings_cache()`：

```python
from jobagent.core import get_settings

settings = get_settings()
```

缺失或非法配置会转换为不可重试的 `ConfigurationError`；校验详情不会包含原始配置值。

## 密钥边界

- Token、secret key 和短期 access key 不得进入 Git、数据库、日志、测试固定样本或命令参数。
- access key 只在 provider 进程内缓存，不持久化。
- 不得把包含凭据的 URL、请求/响应正文、请求头或第三方异常文本传入通用日志和错误链路。
- `.env.example` 只保留空值；真实 `.env` 不得提交。
- `jobagent-delivery show` 不需要 PushPlus 密钥；`send` 在缺少完整密钥对时安全失败。

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

每行日志是一个 JSON 对象，固定包含 UTC 时间、级别、logger 和事件，并自动附加当前异步上下文。
常见敏感字段名会递归遮蔽，包括 `password`、`secret`、`token`、`api_key`、`authorization`、
`cookie` 和 `credential`。不得把密钥拼接到自由文本事件名；任意字符串无法可靠自动脱敏。

## 统一异常

| 异常 | 是否可重试 | 用途示例 |
|---|---:|---|
| `ConfigurationError` | 否 | 缺失环境变量、非法时区、投递密钥不完整 |
| `TransientJobAgentError` | 是 | 网络连接失败、来源临时限流、结果查询暂不可用 |
| `PermanentJobAgentError` | 否 | 不支持的文件、稳定 4xx、持久身份冲突 |

所有业务异常都包含稳定的 `code`、安全的 `message`、`category`、`retryable` 和结构化
`details`，可通过 `to_dict()` 转换为日志或 API 响应。Provider 的原始错误消息必须先映射到白名单
错误码和固定安全说明。

## 相关文档

- [PushPlus 日报投递](DELIVERY.md)
- [每日调度、恢复与补跑](SCHEDULING.md)
- [数据库模型与迁移](DATABASE.md)
