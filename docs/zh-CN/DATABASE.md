# JOBAGENT 核心数据库模型

> 英文原文：[JOBAGENT core database model](../DATABASE.md)。修改原文时必须在同一提交中同步更新本镜像。

本文描述 JAI-006 建立的 PostgreSQL Schema，以及 JAI-009 的[原始公告版本策略](RAW_DOCUMENTS.md)、JAI-010 的[附件存储策略](ATTACHMENTS.md)、JAI-019 的[版本化抽取/证据策略](MERGING_AND_EVIDENCE.md)、JAI-020 的[校验/重解析策略](VALIDATION_AND_REPARSING.md)、JAI-022 的[单用户偏好策略](PREFERENCES.md)、JAI-023 的[版本化匹配策略](MATCHING.md)和 JAI-024 的[日报快照](REPORTS.md)带来的扩展。JAI-007 增加的采集运行仓库和编排见[采集编排文档](COLLECTION.md)。

## 数据表

| 表 | 用途 | 重要字段与约束 |
|---|---|---|
| `sources` | 公开招聘来源配置 | `name` 唯一；`crawl_interval_minutes` 为正数；通过 `enabled=false` 停用 |
| `crawl_runs` | 一次来源运行 | 状态值受限；`finished_at` 不得早于 `started_at`；JSONB 统计 |
| `raw_documents` | 不可变的来源公告版本 | `(source_id, canonical_url, version)` 唯一；每个来源 URL 只有一个当前版本；SHA-256 内容哈希；可选 ETag/Last-Modified；HTML 或文本至少一个存在 |
| `attachments` | 从公告发现的文件 | `(document_id, url)` 唯一；下载状态和元数据受校验；解析状态独立 |
| `job_posts` | 版本化公告级结构化结果 | 公告/抽取版本唯一；只有一个当前版本；版本/前序/哈希链；时间顺序；复核状态和推荐资格 |
| `job_positions` | 一个公告版本下的可选岗位记录 | 稳定记录 key；没有证据时岗位名称可空；已知人数必须为正 |
| `field_evidence` | 字段级可追溯证据 | 原值/规范值、方法/版本、选中/冲突、且仅一个来源、引文/页/行/工作表/单元格定位，置信度为 0 到 1 |
| `validation_issues` | 逐版本质量问题 | 每个公告下 issue key 稳定唯一；原因、严重度、实体/字段身份；仅允许错误和警告 |
| `user_preferences` | 本地单用户档案 | 固定 `id=1`；结构化筛选项；无限制默认值；审计时间与粘性重算信号 |
| `match_results` | 版本化岗位匹配决定 | 得分/规则版本；输入/偏好/结果哈希；硬过滤决定；JSONB 分项/规则；一个当前结果和追加式历史 |
| `daily_report_snapshots` | 不可变结构化/渲染日报 | 日期/时区/版本/输入身份；JSONB payload；内容哈希；Markdown 与已转义 HTML；相同输入复用一份快照 |

## 关系与删除策略

```text
sources
├── crawl_runs
└── raw_documents
    ├── supersedes → 上一个 raw_documents 版本
    ├── attachments
    │   └── field_evidence（附件来源）
    ├── job_posts
    │   ├── job_positions
    │   │   └── match_results → user_preferences
    │   └── validation_issues
    └── field_evidence（文档来源）

daily_report_snapshots（不可变日报 payload 与渲染）
```

所有历史外键使用 `ON DELETE RESTRICT`，ORM 关系不使用删除级联。有历史记录引用的来源不能被意外删除。正常停用来源只把 `sources.enabled` 改为 false，从而保留运行、文档、附件和抽取数据。

`field_evidence.entity_type/entity_id` 有意采用经过校验的多态引用，可指向 `job_posts` 或 `job_positions`。抽取仓库会校验该实体目标，数据库则保留真实外键，指向提供证据的来源文档或附件。新抽取版本会追加公告/岗位/证据行，旧版本保持抗删除。

`validation_issues.post_id` 是指向实际 `job_posts` 抽取版本的受限外键。新的规则/抽取版本会追加新公告和新问题，不修改历史判断。

`match_results.position_id` 和 `preference_id` 是指向实际岗位与单例偏好档案的受限外键。新偏好快照或评分版本会追加结果并切换唯一当前标记；`supersedes_id` 保留前一项决定。

## 时间处理

- PostgreSQL 列使用 `TIMESTAMP WITH TIME ZONE`。
- `UTCDateTime` 拒绝没有时区信息的 Python 时间值。
- 有时区的值在绑定前和读取后规范化为 UTC。
- 数据库默认值使用 PostgreSQL 当前时刻；PostgreSQL 以绝对时刻保存 `timestamptz`。
- 转换为 `Asia/Shanghai` 用于显示和调度，属于应用边界，不进入存储值。

## 约束与索引

- SHA-256 是 64 位小写十六进制字符串。
- 原始公告版本必须为正数，并形成抗删除的自引用链；部分唯一索引保证每个来源/规范 URL 只有一个 `is_current=true` 记录。
- 已存储附件必须包含 MIME 类型、SHA-256、相对本地路径、非负字节数和下载时间；记录下载失败时，仓库会清除这些成功元数据。
- 附件 `download_status`（`pending`/`stored`/`failed`）与后续 `parse_status` 流程相互独立。
- 状态和证据类型字段使用显式检查约束，而不是不受限制的自由文本。
- 来源/日期、状态、截止日期、地区/学历和证据查询等常见路径均建立索引。
- 不完整的结构化字段保持可空，以便保留原始证据并进入后续复核流程。
- 公告/抽取版本组合通过结果哈希实现幂等；部分唯一索引保证每个公告只有一个当前 post，`supersedes_id` 保留完整 post 版本链。
- 字段证据同时保存原值与规范值，并保留冲突候选而不是覆盖；行范围和工作表/单元格坐标补充既有页码/引文定位。
- `review_status` 仅允许 `approved`、`review_required` 或 `blocked`；`validation_issues.severity` 仅允许 `warning` 或 `error`。任何错误都会在同一抽取事务中设置 `recommendation_eligible=false`。
- 当前/推荐资格索引供后续推荐查询使用，避免把旧数据或阻塞记录当作可推荐。旧数据回填为 `review_required` 和 `legacy-unvalidated`，不会被静默批准。
- `user_preferences` 只允许 `id=1`；JSON 偏好字段必须保持数组，`education` 必须是受支持的确定性枚举或空值。空值表示无限制，绝不表示“一个也不匹配”。
- `match_results` 把得分限制为 0～100，任一硬过滤失败时必须为零，校验全部 SHA-256 身份，并要求分项/规则解释为 JSON 数组；部分唯一索引保证每个岗位只有一个当前结果。
- `daily_report_snapshots` 要求 payload 为 JSON 对象，输入/内容 SHA-256 合法。日期/时区/报告版本/输入哈希身份避免重复快照，同时把同日发生变化的输入保留为独立不可变记录。

## 迁移

Alembic 通过正常 Settings 读取 `JOBAGENT_DATABASE_URL`；`alembic.ini` 不包含凭据。

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

在 Compose 内执行：

```powershell
docker compose exec api alembic upgrade head
```

迁移集成测试具有破坏性，因此拒绝操作名称不以 `_test` 结尾的数据库。
