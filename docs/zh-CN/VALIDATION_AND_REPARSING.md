# 数据校验、待复核与重解析

> English: [Validation, review, and reparsing](../VALIDATION_AND_REPARSING.md)

JAI-020 在 JAI-019 合并之后新增确定性质量控制边界。每个抽取版本都持久化校验问题；严重错误会阻止自动推荐资格；抽取或校验规则修正后，可以显式重解析一份已存储文档。

## 校验规则

`ExtractionValidator` 输出稳定错误码、严重度、实体 key、可选字段名、安全原因和确定性 issue key，绝不猜测缺失值。

- 缺少 `organization`、`deadline`、`apply_url`、全部岗位，或岗位 `education` 时记录 `error`。
- 缺少公告 `region`/`category` 或岗位 `headcount`/`region` 时记录 `warning`。
- 日期范围倒置、报名链接不是合法的绝对 HTTP(S) URL，或规范化地区/类别/学历不在支持字典中时记录 `error`。
- `organization`、`deadline`、`apply_url` 或岗位 `education` 的冲突属于错误；其他有证据冲突属于警告。

原因文本不包含凭据、附件路径、provider 响应正文或原始个人数据。原始字段值与位置继续保存在 `field_evidence`，不重复写入校验消息。

## 复核与推荐资格

每个 `job_posts` 版本保存 `review_status`、`recommendation_eligible`、`validation_version` 和 `validated_at`。

| 校验结果 | `review_status` | `recommendation_eligible` |
|---|---|---|
| 无问题 | `approved` | `true` |
| 只有警告 | `review_required` | `true` |
| 至少一个错误 | `blocked` | `false` |

每个问题都以原因和严重度追加到 `validation_issues`；历史公告版本及其问题保持可查询。JAI-020 之前的记录回填为 `review_required`、不可推荐和 `legacy-unvalidated`，迁移不会伪装旧数据已经通过当前规则。

## 已存储文档重解析流水线

`StoredDocumentReparsePipeline` 重新加载一行不可变 `raw_documents`。存在 `raw_text` 时优先使用，否则把已存 HTML 转为文本；随后从配置的内容寻址存储根目录重新解析全部关联附件。附件路径必须位于该根目录内，且解析前必须匹配已持久化的字节数和 SHA-256。

附件未存储、完整性校验失败、不支持或无法产生 `parsed` 中间结果时，重解析会显式失败。默认流水线只执行确定性抽取和 JAI-019 合并；不发起线上来源请求，也不调用 LLM。

## 命令与 API

手动命令要求正整数文档 ID 和显式抽取/规则版本：

```powershell
.\.venv\Scripts\python.exe scripts/manage_extraction.py reparse --document-id 19 --extraction-version rules-2026.08.25
```

API 复用同一服务：

```http
POST /extraction/documents/19/reparse
Content-Type: application/json

{"extraction_version":"rules-2026.08.25"}
```

两种响应都包含写入结果、公告/岗位 ID、实体版本、结果哈希、复核状态、推荐资格、校验版本及错误/警告计数。安全的永久错误返回 `404` 或 `422`，临时数据库/存储错误返回 `503`。

## 幂等与版本变更

抽取版本必须由 1～100 个字母、数字、点、下划线、冒号或连字符组成。同一文档/版本产生相同结果哈希时返回 `unchanged`，复用既有实体与问题；同一版本产生不同输出时以 `extraction.version_not_deterministic` 拒绝。

规则修正后必须使用新的显式抽取版本。仓库会追加新的当前公告/岗位/证据/校验版本，把旧公告标记为非当前，并保留 `supersedes_id` 链。

## Issue 边界

- JAI-020 不接入来源 4/5，也不执行连续多日稳定性运行；这些属于 JAI-021。
- 不新增偏好、匹配、评分、报告、调度、OCR 或宽泛维护 API。
- 不新增手工改值或审批接口。阻塞记录只有在修正证据/规则产生合法新版本后才能恢复推荐资格。
- 不绕过登录、验证码、访问控制、反爬措施或平台限制。
