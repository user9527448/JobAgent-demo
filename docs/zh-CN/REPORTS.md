# 日报查询、渲染与快照

> English: [Daily report queries, rendering, and snapshots](../REPORTS.md)

## 报告输入与输出

JAI-024 只读取属于当前 `job_posts` 的当前 `match_results`。报告日期和配置的 IANA 时区都是显式输入，构建器不会读取进程时钟。每个 JSON 条目都包含 `organization`、`title`、`region`、`deadline`、`reason`、`risks` 和不可变原文 `source_url`。没有证据的字段保持 null，并渲染为 `未提供 (需确认)`，不得猜测填充。

四个分组始终全部存在。同一岗位可以出现在多个分组，因为“优先投递”“即将截止”和“今日新增”是相互独立的行动维度。

## 四个确定性分组

| 分组 | 纳入规则 |
|---|---|
| `priority_applications` | 当前硬过滤通过，且 JAI-023 得分不低于 70 |
| `closing_soon` | 当前硬过滤通过，且有证据截止时间位于本地报告日起点至七个自然日后起点的左闭右开区间 |
| `added_today` | 当前硬过滤通过，且来源文档首次 `fetched_at` 落在本地报告日期内 |
| `needs_confirmation` | 抽取复核状态不是 `approved`，或单位/标题/地区/截止时间/来源 URL 任一项没有证据 |

没有任何来源岗位时，仍生成四个标题及明确的 `本组暂无岗位。`。硬过滤未通过的岗位不会作为可行动岗位展示，除非其校验状态或证据缺口本身要求人工确认。

## 稳定排序与风险

`jai-024-v1` 对标准 JSON 计算哈希，输入包括报告日期、时区、报告版本，以及会影响分组、排序、理由或风险的全部候选字段。构建前先按岗位 ID 规范化候选输入顺序。

- 优先投递按得分降序，再按截止时间、规范化单位/标题和岗位 ID 排序。
- 即将截止按截止时间，再按得分降序和稳定文本/ID 并列规则排序。
- 今日新增按首次采集时间降序，再按得分和稳定文本/ID 并列规则排序。
- 需要确认按风险数量降序，再按得分、截止时间和岗位 ID 排序。

风险只来自已持久化的校验原因、非 `approved` 复核状态、有证据的缺失字段、适用时失败的硬过滤解释，以及不足 72 小时的明确截止时间。没有这些情况时，条目明确说明未记录校验或字段证据风险。

## Markdown 与 HTML 渲染

`render_markdown()` 和 `render_html()` 只消费不可变日报契约。Markdown 会转义来源控制的格式字符，并以自动链接输出原文 URL。HTML 会转义全部来源文本和 URL 属性，并添加 `rel="noopener noreferrer"`。两种渲染均保留全部字段、理由、风险和明确空分组。

模板不执行来源 HTML 或 JavaScript；日报不复制来源正文、附件路径、凭据或 provider payload。

## 持久化与 API

迁移 `0008_daily_report_snapshots` 新增 `daily_report_snapshots`。唯一身份为 `(report_date, timezone, report_version, input_hash)`；相同输入重复生成时，在核对内容哈希及两份渲染完全一致后复用现有记录。JSON payload、SHA-256 内容哈希、Markdown、HTML 和审计时间构成不可变快照证据。

```http
POST /reports/daily
Content-Type: application/json

{"report_date":"2026-09-03"}
```

响应返回 `snapshot_id`、`content_hash`、结构化 `report`、`markdown`、`html` 和 `created_at`。已存在快照可在不重新计算当前数据的前提下读取：

```http
GET /reports/daily/{snapshot_id}
GET /reports/daily/{snapshot_id}/markdown
GET /reports/daily/{snapshot_id}/html
```

不存在的正整数 ID 返回 `reports.snapshot_not_found`；持久化不可用返回 `reports.database_unavailable`。同版本/输入产生不同内容时返回 `reports.version_not_deterministic`，绝不覆盖历史。

## 范围边界

JAI-024 不调整推荐质量，不调度日报，不发送通知，不管理通道/Token，也不实现 LLM/向量排序。JAI-025 负责人工 Top 20 评审，JAI-026 负责调度与恢复，JAI-027 负责一个具备幂等语义的通知通道。
