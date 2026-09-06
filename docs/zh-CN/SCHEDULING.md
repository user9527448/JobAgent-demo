# 每日调度、恢复与补跑

> English: [Daily scheduling, recovery, and makeup operations](../SCHEDULING.md)

JAI-026 将既有采集、确定性抽取/校验、匹配和日报服务组成一条持久化每日流水线。投递仍属于
JAI-027，附件衔接和线上完整率工作仍属于 JAI-049。

## 运行架构

- 一个专用 `AsyncIOScheduler` 进程与 FastAPI worker 分离运行。
- APScheduler 3 把固定任务 `jobagent.daily-pipeline.v1` 保存到 PostgreSQL 表
  `apscheduler_jobs`，使用 `replace_existing=True`、`coalesce=True`、`max_instances=1`，默认
  misfire 宽限期为六小时。
- 只允许运行一个 scheduler 服务。APScheduler 3 不会通过共享 job store 协调多个调度器。
- PostgreSQL session advisory lock 覆盖完整领域流水线。锁竞争会在写入 `pipeline_runs` 前返回
  `locked`。
- `(job_name, scheduled_for)` 是不可变逻辑运行身份。同一本地时刻的计划运行和手工补跑会恢复或
  复用同一行。

固定顺序为：

```text
采集 → 确定性抽取/校验 → 匹配 → 日报
```

采集使用既有 Adapter 与限速策略，按来源 ID 稳定顺序访问启用来源。抽取处理尚无 `jai-026-v1`
结果的当前文档。匹配在逻辑 `scheduled_for` 时刻强制使用既有当前评分版本，但不修改用户偏好。
日报使用 `Asia/Shanghai` 下的计划日期与既有不可变快照服务。

## 配置

| 变量 | 默认值 | 含义 |
|---|---:|---|
| `JOBAGENT_TIMEZONE` | `Asia/Shanghai` | 计划和报告日期使用的 IANA 时区 |
| `JOBAGENT_SOURCE_CATALOG_PATH` | `config/source_catalog.toml` | 已批准的网站库 |
| `JOBAGENT_SCHEDULER_HOUR` | `8` | 本地每日小时，0～23 |
| `JOBAGENT_SCHEDULER_MINUTE` | `0` | 本地每日分钟，0～59 |
| `JOBAGENT_SCHEDULER_MISFIRE_GRACE_SECONDS` | `21600` | 错过触发后仍允许执行的最大延迟 |
| `JOBAGENT_SCHEDULER_STAGE_MAX_ATTEMPTS` | `3` | 每阶段临时失败最大尝试次数 |
| `JOBAGENT_SCHEDULER_RETRY_DELAY_SECONDS` | `30` | 指数重试的基础延迟 |

只有 `TransientJobAgentError` 会重试，默认等待 30 秒和 60 秒。永久失败和意外异常会停止下游并
保留安全的错误码/类型。采集最后一次尝试若至少一个来源成功，则以 `partial` 继续，同时保留失败。

## 操作命令

任何命令使用数据库前必须先应用迁移 `0009`。已有数据业务库的迁移与长驻调度启用必须先通过
单独的 G4 明确审批。

```powershell
jobagent-scheduler start
jobagent-scheduler makeup --date 2026-09-06
jobagent-scheduler show --run-id 1
```

- `start` 先把遗留的 `running` 阶段尝试标为 `interrupted`，按时间从旧到新恢复未完成运行，再启动
  持久化每日调度器。
- `makeup` 把指定本地日期转换为配置的每日时刻；已有同一逻辑时刻时不会创建第二条运行。
- `show` 输出运行及全部有序阶段尝试，包括记录 ID、版本、计数、状态和安全错误元数据。

退出码 `0` 表示完成/复用或查询成功，`2` 表示运行失败或记录不存在，`3` 表示另一进程持有流水线锁。

## 恢复与追溯

恢复时不重放已经成功或部分成功的阶段。之前仍为 `running` 的阶段会先以 `interrupted` 结束，再创建
下一编号的尝试。各阶段输出保存既有产物身份：采集的 `crawl_run_ids`；抽取的文档/公告/岗位 ID 与
版本；匹配的结果 ID 与评分版本；日报的快照 ID、版本与内容哈希。

Compose 中声明的 scheduler 服务在单独 G4 批准前只作为配置，不实际启用。JAI-026 测试只操作名称以
`_test` 结尾的受保护数据库；端到端测试以合成边界替代公网采集，但真实执行全部下游服务与
PostgreSQL 持久化。
