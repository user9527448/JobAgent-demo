# 需要项目负责人手动执行的事项

> English: [Manual owner actions](../MANUAL_ACTIONS.md)

本文档集中维护必须由项目负责人亲自完成或明确批准的事项。文档不保存任何凭据值，也不能替代各
Issue 自己的审批闸门。新增、完成、延期或取代事项时，必须同步更新中英文文件。

## 当前队列

| ID | 状态 | 负责人操作 | 解锁事项 |
|---|---|---|---|
| `M-001` | 负责人已延期 | 准备 PushPlus 账户与 OpenAPI 设置 | JAI-027 G5 凭据校验 |
| `M-002` | 负责人已延期 | 创建本地 `.env` 并填写两项 PushPlus 密钥 | JAI-027 G5 受控真实测试 |
| `A-001` | 等待 `M-001`/`M-002` | 明确批准 JAI-027 G5 | 业务迁移 `0010` 与一次指定真实测试 |
| `A-002` | 已批准：2026-09-14 | 批准 D-038/U1-R、堆叠分支顺序及追加式持久反馈方向 | 双语计划更新与独立 JAI-050 设计/实现 |
| `A-003` | 已完成：方案 1 | 已从三个 U2 视觉方向中选择“晨间简报” | 待 A-002/U1-R 后作为 JAI-050 的视觉基线 |
| `A-004` | 未来事项 | 在 U3 审批 JAI-051 反馈 Schema/API/保留边界 | 反馈迁移与写入 |
| `M-003` | 待处理 | 恢复 Docker Hub 访问或预拉取 `node:24-alpine` | JAI-050 容器构建验证 |
| `A-005` | 已被时刻经过取代 | 恢复的 scheduler 在决定登记前已执行 2026-09-15 时刻 | 仅作事实记录，不倒推已获批准 |
| `A-006` | 已完成：只停止 scheduler | 负责人已批准只停止 scheduler；`db`/`api` 保持运行 | 停止期间不会执行 2026-09-26 线上来源时刻 |

当前队列中的任何事项都不授权补跑、线上招聘来源请求、第二次真实通知、JAI-028 五次无人值守运行或
JAI-029 发布工作。

## M-003 — 恢复 Docker 构建前置条件

JAI-050 Dockerfile 现在通过 `node:24-alpine` 阶段按 lockfile 构建前端。首次
`docker compose build api` 已访问 Docker Hub，但通过 IPv6 获取匿名 token 时超时；Compose 语法有效，
本地也没有该镜像。不得为绕过此问题修改仓库远程、Git 代理或已提交的 Docker 配置。

Docker Hub 可访问后，可在任意目录执行：

```powershell
docker pull node:24-alpine
```

完成后只回复“`M-003 已完成`”。随后由 Agent 重跑 `docker compose build api`；本项不得附带重建或
重启当前 Compose 服务。

## A-005/A-006 — 决定已恢复 scheduler 的状态

2026-09-15 启动 Docker Desktop 后，Compose 已有的 `restart: unless-stopped` 策略自动恢复了唯一
scheduler。只读证据表明下一时刻为 `Asia/Shanghai` 2026-09-15 08:00。保持运行会允许现有四阶段
生产流水线届时访问已批准线上来源并写入业务数据；这不是 JAI-028 试运行，也不会应用迁移 `0010`。

2026-09-15 时刻在决定登记前已经经过。当前只读证据显示该日期新增一条计划运行，既有四阶段均一次
成功；固定作业下一时刻为 2026-09-16 08:00。该事实不表示倒推批准，也不属于 JAI-028 试运行。

2026-09-16 的决定截止时刻已过，但没有登记负责人决定。Docker 在 2026-09-25 较早时不可用，随后由
负责人手动启动。已完成的只读核验显示一个健康数据库、一个健康 API、一个 scheduler，业务 Alembic
仍为 `0009_pipeline_scheduling`，并且恰有一个固定作业，下次为 `Asia/Shanghai` 2026-09-26 08:00。
台账仍只有 2026-09-06 成功补跑和 2026-09-15 成功计划运行，两条各有四个成功阶段；2026-09-16 至
2026-09-25 没有运行行，启动日志也没有显式 misfire 事件。

负责人已明确批准只停止 scheduler。`docker compose stop scheduler` 已完成；scheduler 以退出码 143
停止，`db` 与 `api` 继续保持健康。只读 SQL 确认 Alembic 仍为 `0009_pipeline_scheduling`，一个固定
作业行保留，两条运行与八条阶段记录均为成功。存储的 2026-09-26 08:00 时刻只是持久作业状态，
scheduler 容器停止时不会主动执行。后续任何 scheduler 重启都需要重新明确批准。本操作没有补跑、
迁移、投递或访问来源。

## M-001 — 准备 PushPlus

以下步骤由负责人在 PushPlus 网站完成；不得通过对话发送得到的值：

1. 注册/登录，绑定接收消息的微信账户，并完成 provider 要求的实名认证。
2. 打开“个人中心 → 一对一推送”，复制**用户 token**。不得使用消息 token：PushPlus 的基础发送
   接口可以使用两类 token，但 OpenAPI 只接受用户 token；JOBAGENT 需要 OpenAPI 核对最终发送结果。
3. 打开“个人中心 → 开发设置”，启用 OpenAPI，并创建至少 32 位、混合数字和英文字母的随机
   `secretKey`；应使用密码管理器生成并保存。
4. 把运行 Docker 的机器当前公网出口 IP 加入 PushPlus 安全 IP 列表。条目缺失或过期会使 AccessKey
   获取返回 403。

官方参考：[token 类型](https://pushplus.plus/doc/help/token.html)和
[OpenAPI 设置](https://pushplus.plus/doc/guide/openApi.html)。

## M-002 — 配置被忽略的本地文件

仓库本地需要 `.env`，但 Git 中绝不能出现它。如果 `.env` 尚不存在，只在仓库根目录执行一次：

```powershell
Test-Path .env
Copy-Item .env.example .env
```

如果 `Test-Path` 返回 `True`，不得复制或覆盖已有文件。用本地文本编辑器打开 `.env`，只填写其中
已有的两行空值：

```dotenv
JOBAGENT_PUSHPLUS_TOKEN=<PushPlus 用户 token>
JOBAGENT_PUSHPLUS_SECRET_KEY=<PushPlus secretKey>
```

不得把任一值写入 `.env.example`、命令参数、Shell 历史、截图、测试固定样本、日志、数据库、Git 或
对话。无需手工创建 AccessKey；JOBAGENT 会在内存中换取且绝不持久化。

完成 `M-001` 和 `M-002` 后，只回复“`M-001/M-002 已完成`”，不要附带具体值。随后可由 Agent 在不
打印密钥的前提下校验是否存在且成对配置。

## A-001 — JAI-027 G5 审批

凭据存在性通过安全校验后，审批文本为：

```text
批准 JAI-027 G5：业务迁移 0010，并且只对日报快照 2 执行一次真实 PushPlus 测试。
```

由 Agent 执行的顺序为：取得业务台账只读快照、停止唯一 scheduler、应用只新增结构的迁移、核验
Alembic/漂移/计数、构建已审批运行时、只发送一次快照 ID `2`、核对 provider 最终结果并审计投递
台账。测试后 scheduler 保持停止，直到 JAI-028 启用另行获批，避免本次真实测试静默开始五次验收。

## A-002 — 正式 UI 基底审批

建议审批文本为：

```text
批准 D-038/U1-R：React、TypeScript、Vite、pnpm、Tailwind CSS v4、基于 Radix 的 shadcn/ui、
frontend/、FastAPI 同源生产发布、JAI-050 位于 JAI-028 前、JAI-051 位于 JAI-028 后，并采用受 U3
约束的追加式持久化推荐反馈。
```

该批准允许在 JAI-027 集成后正式更新两份开发计划与两份 Backlog，但不等于安装依赖或选择视觉
方向。JAI-050 必须先形成成对 DESIGN.md 草案和三个 U2 视觉方案。

2026-09-14，项目负责人批准上述技术路线、Issue 插入和追加式持久反馈方向，并补充批准：由于
JAI-027 G5 已延期，可从当前 JAI-027 末端创建独立堆叠分支
`feature/jai-050-production-ui-foundation` 继续 JAI-050；该分支不得先于 JAI-027 合入 `develop`，
不得把 JAI-027 G5、JAI-028 或 JAI-051 的运行/迁移验收混入 UI Issue。JAI-051 的具体 Schema、API
和保留边界仍受 `A-004/U3` 单独审批。

## A-003 — JAI-050 视觉方向选择

2026-09-10，项目负责人从三个独立 U2 方案中选择方案 1“晨间简报”。该方向以最新日报和行动型岗位
推荐为主阅读流，以调度、流水线和投递证据为辅助信息；采用克制的浅色编辑式布局，并作为后续
Tailwind CSS + shadcn/ui 正式页面的视觉基线。

本选择只完成视觉方向决策，不替代 `A-002/U1-R` 的技术路线、Issue 插入和执行顺序审批，也不授权
创建 JAI-050 分支、安装前端依赖或实现 UI。JAI-050 启动后必须把该方向转写为成对、可版本控制的
`docs/DESIGN.md` 与 `docs/zh-CN/DESIGN.md` 规范；预览图本身不作为运行时资产或实现验收的唯一依据。

## 可复用 Docker 恢复步骤

Docker engine 不可用时，由负责人手动启动 Docker Desktop，然后只告知 Agent“Docker 已就绪”。
不要自行执行迁移、补跑、线上来源采集、scheduler 扩容或通知命令。Agent 会先进行只读 Compose 与
台账核验，并在任何写入前请求准确审批。
