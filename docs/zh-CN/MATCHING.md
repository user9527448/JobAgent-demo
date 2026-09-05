# 确定性匹配与版本化评分

> English: [Deterministic matching and versioned scoring](../MATCHING.md)

JAI-023 把一份显式岗位快照与 JAI-022 偏好快照转换为确定、可解释的结果。评分引擎是纯函数边界：不访问数据库、网络或 LLM，不生成日报或通知，评估时刻也必须显式传入。

## 硬过滤

任一硬过滤失败时，总分为零：

| 规则 | 通过行为 |
|---|---|
| `validation_eligibility` | 当前抽取版本已经由 JAI-020 标记为 `recommendation_eligible=true` |
| `education` | 没有带证据的学历不匹配，或候选人的显式学历等级满足岗位的显式学历要求 |
| `deadline` | 没有截止时间证据，或 UTC 截止时间严格晚于 `evaluated_at` |
| `exclusion` | 对单位、公告/岗位标题、部门、专业和要求执行 NFKC/case-fold 后，没有排除词作为子串命中 |

学历或截止时间缺少证据时不得猜测，也不会仅因缺失而硬过滤；缺失会反映到完整度分项，并可由 JAI-024 放入“需要确认”分组。到达截止时间的精确瞬间即视为关闭。

学历等级固定为：`no_requirement` < `high_school`/`secondary_vocational` < `associate`/`associate_or_above` < `bachelor`/`bachelor_or_above` < `master`/`master_or_above` < `doctorate`。

## 分项评分

全部硬过滤通过后，`jai-023-v1` 使用计划中的 100 分公式：

| 分项 | 上限 | 规则 |
|---|---:|---|
| `region` | 25 | 偏好为空时中性满分；`national` 或地区精确匹配时满分 |
| `job_direction` | 30 | 偏好为空时中性满分；任一显式岗位关键词命中时满分 |
| `major` | 15 | 偏好为空时中性满分；任一显式专业偏好命中时满分 |
| `organization_type` | 10 | 偏好为空时中性满分；否则按枚举精确匹配 |
| `deadline_urgency` | 10 | 开放截止：≤72 小时为 10、≤7 天为 8、≤14 天为 5、更晚为 2；缺失/关闭为 0 |
| `information_completeness` | 10 | 单位、岗位/公告标题、地区、截止时间、来源 URL 各 2 分 |

对已持久化的抽取数据，只从语义能直接确定单位类型的类别做映射：`civil_service → government`、`public_institution → public_institution`、`state_owned → state_owned`。`campus` 和 `social` 不能证明单位类型，因此保持未知，不进行猜测。

每个硬过滤都会保存规则、输入、通过/失败决定和解释；每个评分分项都会保存分项名称、规则版本、输入、得分、上限和解释。日报与面向用户的推荐文案仍属于 JAI-024。

## 确定性与版本

`DeterministicMatchingEngine.evaluate()` 必须接收岗位数据、规范化偏好、带时区的 `evaluated_at` 和评分版本。UTC 规范化后的标准 JSON 分别生成岗位/时间输入、偏好和完整结果的 SHA-256。同样输入与 `jai-023-v1` 因此会产生完全相同的决定、得分、分项、解释和哈希。

未知评分版本会显式失败。规则或权重变化必须使用新版本，不得静默改变 `jai-023-v1` 的含义。数据库 `generated_at` 仅为审计元数据，不进入确定性结果哈希。

## 持久化与全量重算

迁移 `0007_versioned_match_results` 新增 `match_results`：

- 通过受限外键关联 `job_positions` 和单例 `user_preferences`；
- 保存评分/输入/偏好/结果哈希、显式 `score_version`、`evaluated_at` 和偏好更新时间；
- 使用 JSONB `matched_rules` 与 `components` 保存解释载荷；
- 通过 `supersedes_id` 追加保留历史，并保证每个岗位只有一个当前结果；
- 由数据库约束校验哈希、分数范围、JSON 数组，以及硬过滤失败后的零分。

`SqlAlchemyMatchingService.recompute_if_requested()` 锁定单例偏好行；粘性信号存在时，按岗位 ID 稳定顺序评估所有属于当前 `job_posts` 版本的岗位。结果创建、当前/历史切换和信号确认处于同一事务；任何失败都会同时回滚结果与确认，因此不会丢失待处理请求。成功确认不会改变偏好 `updated_at`，因为该时间用于标识本批次实际使用的偏好值。

没有待处理信号时重复消费为空操作。相同岗位/输入/偏好更新时间会复用完全一致的结果；若同一计算身份产生不同结果，会抛出 `matching.version_not_deterministic`。

## 范围边界

JAI-023 不实现日报查询/分组、Markdown/HTML 渲染、快照、投递、通知、调度、LLM 排序、向量召回或面向用户的匹配 API。JAI-024 负责日报；后续流水线/API Issue 可以调用这里的可复用匹配服务。
