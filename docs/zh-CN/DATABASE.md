# JOBAGENT 核心数据库模型

> 英文原文：[JOBAGENT core database model](../DATABASE.md)。修改原文时必须在同一提交中同步更新本镜像。

本文描述 JAI-006 建立的 PostgreSQL Schema，以及 JAI-009 的[原始公告版本策略](RAW_DOCUMENTS.md)和 JAI-010 的[附件存储策略](ATTACHMENTS.md)带来的扩展。JAI-007 增加的采集运行仓库和编排见[采集编排文档](COLLECTION.md)。

## 数据表

| 表 | 用途 | 重要字段与约束 |
|---|---|---|
| `sources` | 公开招聘来源配置 | `name` 唯一；`crawl_interval_minutes` 为正数；通过 `enabled=false` 停用 |
| `crawl_runs` | 一次来源运行 | 状态值受限；`finished_at` 不得早于 `started_at`；JSONB 统计 |
| `raw_documents` | 不可变的来源公告版本 | `(source_id, canonical_url, version)` 唯一；每个来源 URL 只有一个当前版本；SHA-256 内容哈希；可选 ETag/Last-Modified；HTML 或文本至少一个存在 |
| `attachments` | 从公告发现的文件 | `(document_id, url)` 唯一；下载状态和元数据受校验；解析状态独立 |
| `job_posts` | 公告级结构化结果 | 每个文档至多一个当前公告；截止时间不得早于开始时间 |
| `job_positions` | 公告下可选的岗位行 | 已知人数必须为正；公告可以没有岗位行 |
| `field_evidence` | 字段级可追溯证据 | 必须且只能指向一个文档或附件；必须有引文/页码/单元格定位；置信度为 0 到 1 |

## 关系与删除策略

```text
sources
├── crawl_runs
└── raw_documents
    ├── supersedes → 上一个 raw_documents 版本
    ├── attachments
    │   └── field_evidence（附件来源）
    ├── job_posts
    │   └── job_positions
    └── field_evidence（文档来源）
```

所有历史外键使用 `ON DELETE RESTRICT`，ORM 关系不使用删除级联。有历史记录引用的来源不能被意外删除。正常停用来源只把 `sources.enabled` 改为 false，从而保留运行、文档、附件和抽取数据。

`field_evidence.entity_type/entity_id` 有意采用经过校验的多态引用，可指向 `job_posts` 或 `job_positions`。数据库同时保留真实外键，指向提供证据的来源文档或附件。

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
