# PushPlus 日报投递

> English: [PushPlus report delivery](../DELIVERY.md)

JAI-027 通过 PushPlus 把一份不可变日报快照投递到个人微信通道。投递是显式的第五流水线阶段，
不属于日报生成，也不会修改日报快照。

## 架构与身份

```text
日报阶段输出：report_snapshot_id
                │
                ▼
确定性渲染器 → notification_deliveries
                │             │
                │             └─ UNIQUE(report_snapshot_id, channel)
                ▼
有序消息分段 → notification_delivery_attempts → PushPlus → 最终结果查询
```

不可变快照 ID 与固定 `pushplus_wechat` 通道共同构成逻辑幂等键。`delivery_version`、消息哈希、
分段数和每段哈希均为确定值。若已有身份对应不同渲染内容，系统以
`notification.delivery_identity_conflict` 停止，不会静默改变发送内容。

第五阶段只从同一 `pipeline_run` 的成功日报阶段输出读取准确的 `report_snapshot_id`，绝不按日期选择
最新日报。已经终结的 JAI-026 历史运行不会被追溯投递。

## 台账与状态机

`notification_deliveries` 保存父状态、不可变身份、时间戳和安全错误元数据；
`notification_delivery_attempts` 保存每次编号分段提交、可选 PushPlus `shortCode`、时间戳、哈希和
安全错误元数据。受限外键会保留日报与尝试历史。

迁移 `0011_delivery_operator_audit` 新增 `notification_delivery_operator_events`。同一个 UUID
操作身份下，以 `authorized`、`started`、`completed` 三类事件记录一次显式开发重发。授权事件会在
创建新尝试前保存有界操作原因与重复风险确认；完成事件只保存安全终态与白名单错误元数据。数据库
触发器拒绝 `UPDATE` 和 `DELETE`，因此既有不明确尝试与操作证据都不能被改写。

```text
投递：pending → sending → succeeded | failed | unknown
尝试：submitting → accepted → succeeded
                    └────────→ failed | unknown | interrupted
```

只有每个分段都得到 provider 最终成功确认后，父记录才成为 `succeeded`。`failed` 表示永久拒绝或
有界尝试已经耗尽；`unknown` 表示 provider 可能已受理，但系统无法证明最终身份或结果，因此禁止
自动重新提交。

## 渲染、限制与顺序

- 渲染版本为 `jai-027-v1`，内容来自已持久化的 Markdown 快照。
- 每段正文上限 18,000 个 Unicode 字符，标题上限 90 字符，为 provider 已实名用户限制保留余量。
- 分段优先保持完整报告章节/条目，其次使用换行边界，最后才按 Unicode 安全切片。
- 标题包含日报日期和 `[i/n]`；各分段按序逐段提交并确认。
- provider 提交间隔至少 13 秒；空日报仍生成一段。

PushPlus 文档明确：同步 `code=200` 只表示受理，并非送达；返回的 `shortCode` 用于查询最终结果。
OpenAPI 结果状态 0/1/2/3 分别表示待投递、发送中、已发送和发送失败。当前文档中，已实名用户限制
为标题 100 字、正文 20,000 字、每分钟五次请求、同一内容每小时三条。参见官方
[发送 API](https://www.pushplus.plus/doc/guide/api.html)、
[OpenAPI](https://pushplus.plus/doc/guide/openApi.html)和
[限制说明](https://pushplus.plus/doc/help/limit.html)。

## 重试与恢复

- 只有明确发生在提交前的失败，或 provider 显式临时拒绝，才允许创建下一次提交尝试。
- 每段最多提交三次，退避 30 秒和 60 秒。
- 已持久化受理 `shortCode` 时，只在有界窗口查询，不重新提交；后续流水线重试继续查询。
- `shortCode` 已持久化后，只要错误导致无法查询最终结果，即使该查询错误本身属于永久错误，也应记为
  `unknown`；只有 provider 明确返回最终投递失败，才能把已受理尝试终结为 `failed`。
- 写入/读取超时、已受理提交响应畸形、提交期间取消，或遗留 `submitting` 尝试都会转为 `unknown`，
  因为外部系统可能已经受理。
- PostgreSQL session advisory lock 会串行化同一日报/通道的 scheduler 与人工操作；锁竞争返回
  `locked`，不创建重复台账。

原始 provider URL、正文、请求头、错误消息和 transport 异常字符串都会被丢弃；只有白名单错误码和
固定安全说明可以进入台账或应用异常。

## 配置与密钥安全

只有真实启用获得批准后，才可在被 Git 忽略的 `.env` 中同时配置：

```dotenv
JOBAGENT_PUSHPLUS_TOKEN=
JOBAGENT_PUSHPLUS_SECRET_KEY=
```

两项均为空表示未启用；只配置一项属于非法配置。用户 token 和 secret key 使用 `SecretStr`；OpenAPI
access key 只在内存中获取和缓存。凭据不得进入 Git、数据库、日志、测试固定样本、命令参数或 URL。

使用 OpenAPI 查询最终结果前，PushPlus 账户还需启用开发者访问、配置 secret key，并按 provider
要求把发送主机加入安全 IP 设置。

## 操作命令

普通命令只要求迁移 `0010_notification_delivery`；受审计重发命令还要求
`0011_delivery_operator_audit`：

```powershell
jobagent-delivery show --delivery-id 1
jobagent-delivery send --snapshot-id 2
jobagent-delivery resend --delivery-id 2 --part-number 1 --reason "负责人已批准本次开发恢复重发" --confirm-duplicate-risk
```

- `show` 不需要 provider 凭据，返回安全父记录、有序尝试和有序操作事件。
- `send` 只为一份明确的不可变快照创建或恢复合资格工作。既有成功投递返回 `reused`；
  `succeeded` 和 `unknown` 都不会自动重新提交。
- `resend` 仅在 `JOBAGENT_ENVIRONMENT=development` 时可用。它只接受已有终态尝试的 `failed` 或
  `unknown` 投递分段，必须给出 10～500 字符原因及显式重复风险确认，只新增一次尝试并且只调用
  provider 提交一次；既有尝试永不修改，也不隐式重试提交。
- 退出码 `0` 表示成功/复用投递或查询，`2` 表示配置/不存在/终态失败，`3` 表示锁竞争。

不得仅为了测试配置而运行 `send`，它可能创建真实外部消息。获批的真实测试必须提前指定唯一快照。
G1 只在 `_test` 数据库和合成 provider 上验证 `resend`；业务库迁移、凭据检查、真实重发、补跑或
scheduler 重启仍分别需要下一次明确审批。

## 启用闸门

- G4 只覆盖双语文档、Compose 环境变量接线和完整仓库门禁。
- G4 不授权把 `0010` 应用于已有数据的业务库、注入凭据、启动/重启 scheduler、执行补跑或访问
  PushPlus。
- G5 必须另行完成业务台账迁移前快照、明确迁移审批、凭据注入、指定一份日报快照，并且只执行一次
  受控真实测试。
- JAI-028 的五次无人值守运行只能在 JAI-027 验收并另行启用后开始。

相关文档：[负责人手动操作](MANUAL_ACTIONS.md)、[配置](../CONFIGURATION.md)、
[数据库](DATABASE.md)和[调度](SCHEDULING.md)。
