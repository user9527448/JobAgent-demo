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
| `A-006` | 已过期且未决；2026-09-23 运行环境不可用 | Docker 恢复后先审阅只读台账核验，再决定 scheduler 是否继续启用 | 明确当前运行状态；不倒推结果或补跑 |
| `M-004` | 待处理 | 提供每日更新 Excel 工作簿链接并授权 G1 只读检查；不得发送凭据 | JAI-052 G1 结构/来源审计 |
| `A-007` | 等待 `M-004/G1` | 批准 JAI-052 G2 字段映射、身份、消失、刷新和访问规则 | 使用合成固定样本实现导入器 |

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

2026-09-16 的决定期限已经过去，但没有留下决定记录。2026-09-23 Docker Desktop Linux engine
不可用，因此当前没有 2026-09-16 至 2026-09-23 计划记录的只读证据。旧的“正在运行/下一时刻”
描述已经失效，不得据此推断成功、失败、misfire 或当前 scheduler 状态。Docker 恢复后，Agent 必须
先只读核验 Compose、Alembic、APScheduler、`pipeline_runs` 和 `pipeline_stage_runs`；再由负责人决定
scheduler 状态。A-006 不授权补跑、迁移、投递或来源命令。

## M-004/A-007 — 提供并审批表格数据源

执行 `M-004` 时，只需提供工作簿链接并说明授权 G1 只读检查。如果链接需要登录、Token、Cookie、
密码或私有共享授权，不要把凭据粘贴到对话或提交到仓库；只说明“需要认证”。G1 会登记 provider
边界，并提出环境变量或获批连接器方案，另行审批。

G1 只允许检查工作簿结构与更新语义，不授权数据库迁移、生产导入、周期获取、表格写回、Agent
实现、爬虫改动或绕过访问控制。G1 后，Agent 会提交基于证据的 `A-007/G2` 映射建议，包括行身份、
缺失行语义、刷新频率和凭据边界。批准 G2 只允许使用合成固定样本实现；生产启用仍受 JAI-052
后续闸门保护。

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
