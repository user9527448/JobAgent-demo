# 抽取结果合并与字段证据

> English mirror: [`../MERGING_AND_EVIDENCE.md`](../MERGING_AND_EVIDENCE.md)。

JAI-019 把相互独立的确定性候选与已校验 LLM 候选转换为版本化 `job_posts`、可选的部分 `job_positions` 和持久 `field_evidence`。合并过程确定、保留矛盾，且绝不修改旧抽取版本。

## 输入与实体边界

`ExtractionMergeInput` 标识一个不可变 `raw_documents` 行和一个显式合并 `extraction_version`。它接收任意数量的 `ExtractionResult`，以及把已校验 `LlmExtractionPayload` 重新绑定到实际送给 provider 的解析器片段的 `LlmMergeContribution`。

正文解析来源必须使用与 `document_id` 相同的数据库 ID。持久化仓库会校验附件来源 ID，确保每个附件都属于该公告。来源身份混合或缺失时，在业务写入之前直接拒绝。

公告字段包括 `start_at`、`deadline`、`region`、`organization`、`apply_url` 和 `category`。包含 `headcount` 或 `education` 的解析器记录可以生成一个部分岗位，携带 `region`、`headcount` 与 `education`。由于 JAI-017 没有产出有证据的岗位名称字段，岗位 `name` 允许为空；JAI-019 不会虚构占位名称。没有证据可以证明正文与附件岗位行描述同一个岗位时，两者保持独立。

## 优先级与冲突

优先级稳定且按目标字段区分：

1. 确定性候选始终优先于 LLM 候选；
2. 公告字段优先使用文档/正文证据，再使用附件证据；
3. 岗位字段优先使用附件证据，再使用文档/正文证据；
4. 其余并列项按来源 ID、精确位置、原值和规范值排序。

完全重复的候选会折叠，但不同证据不会丢失。按上述顺序的首个候选成为业务选中值；每个不同规范值都保留为 `MergedEvidence`，落选的矛盾候选设置 `conflict=true`，`MergedField.has_conflict` 则暴露字段级冲突。因此冲突可查询，不会被静默覆盖。

确定性证据置信度为 `1.0000`。已校验 LLM 证据使用策略置信度 `0.6000`；该值描述抽取方法，不是模型自评。LLM 值在合并前还会接受字段语义检查：日期必须是带时区 ISO 值，招聘人数必须是正整数，地区必须是非空文本/列表，文本字段必须是非空字符串。不支持的 LLM 语义会被省略，而不是强制转换。

## 版本化持久化与幂等性

`SqlAlchemyExtractionRepository.save()` 按公告取得 PostgreSQL advisory lock，并原子写入一个抽取版本。`job_posts` 现在包含：

- 唯一 `(document_id, extraction_version)`；
- 按公告递增的正 `version`；
- 每个公告只允许一个 `is_current=true` 行的部分唯一约束；
- 指向上一公告版本的 `supersedes_id`；
- 覆盖稳定字段、岗位、证据、冲突和坐标的 SHA-256 `result_hash`。

使用同一 `extraction_version` 和相同结果哈希重复执行时返回 `unchanged`，并复用原公告/岗位 ID。同一版本产生不同哈希时，持久化以 `extraction.version_not_deterministic` 拒绝；调用方必须修复不确定性或使用新的显式版本。新版本会把旧公告标记为非当前，并追加新公告、岗位和证据。历史行通过 `ON DELETE RESTRICT` 关系保留。

迁移 `0004_versioned_field_evidence` 将 JAI-019 之前的结构化行回填为 `legacy-v1`、版本 1、当前状态，并添加稳定的旧岗位 key 和证据元数据。PostgreSQL 测试同时覆盖空 Schema 升级/检查/降级，以及包含旧数据的升级。

## 证据 Schema

每条持久证据都保存：

- 目标 `entity_type`、`entity_id` 和 `field_name`；
- 且仅有一个来源文档或附件 ID，以及匹配的 `source_type`；
- 同时保存 `raw_value` 与 JSONB `normalized_value`；
- `extraction_method`、产出方 `extraction_version`、置信度、是否选中和冲突标记；
- 精确引文，以及页码、闭区间行范围或工作表/单元格范围坐标。

由于每个业务实体版本都有独立 ID 和证据行，选中及冲突证据在重新抽取后仍会保留。仓库也会拒绝属于其他原始公告的附件证据。地区元组在证据中保存为有序 JSON 数组，在当前业务列中保存为逗号分隔的稳定代码；UTC 日期时间在证据中使用 ISO `Z` 字符串，在 `job_posts` 中使用带时区列。

## Issue 边界

- JAI-019 负责实体化并暴露冲突，但不分配复核严重度、不控制推荐资格，也不实现修正流程；这些属于 JAI-020。
- 本 Issue 不新增重解析命令/API。幂等版本持久化是 JAI-020 后续可以调用的底层能力。
- 没有有证据的岗位身份时，不猜测跨来源岗位合并。新增岗位名称抽取器需要独立范围的抽取改动。
- LLM provider 调用、预算和 Prompt 行为仍属于 JAI-018；OCR 仍属于 JAI-B01。
