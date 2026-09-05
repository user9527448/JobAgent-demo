# 单用户偏好

> English: [Single-user preferences](../PREFERENCES.md)

JAI-022 新增一个本地用户的结构化偏好档案，以及读取/全量替换 API。它只保存后续匹配所需输入，不执行岗位过滤、评分或重算；这些行为属于 JAI-023。

## 契约

| 字段 | 类型 | 空值语义 |
|---|---|---|
| `regions` | 保序、去重的地区代码数组 | 任意地区 |
| `education` | 学历枚举或 `null` | 不限制学历 |
| `majors` | 保序、去重的文本数组 | 任意专业 |
| `job_keywords` | 保序、去重的文本数组 | 不要求岗位关键词 |
| `organization_types` | 保序、去重的单位类型数组 | 任意单位类型 |
| `exclusions` | 保序、去重的文本数组 | 无排除词 |

空集合和 `education=null` 是有意设计的无限制默认值。JAI-022 绝不会把它们解释为“一个岗位也不匹配”。文本项会进行 Unicode NFKC 规范化、删除首尾和重复空白，并对大小写不敏感的重复项保留第一次出现的值。

地区和学历代码复用确定性抽取字典。单位类型使用独立的偏好词表，因为 `public_exam` 等来源分类描述的是采集来源，而不是用人单位：

- `government`
- `public_institution`
- `state_owned`
- `private`
- `foreign_enterprise`

## API

`GET /preferences` 返回单例偏好档案及其审计、重算状态。

`PUT /preferences` 全量替换所有偏好字段。因此，未提供的偏好字段会采用无限制默认值。输入在进入持久化前受 Pydantic Schema 的长度和枚举约束。

```json
{
  "regions": ["shanghai", "jiangsu"],
  "education": "bachelor_or_above",
  "majors": ["计算机科学"],
  "job_keywords": ["Python"],
  "organization_types": ["state_owned"],
  "exclusions": ["销售"],
  "trigger_recompute": true
}
```

响应会返回规范化字段，并增加 `created_at`、`updated_at`、`recompute_required` 和 `recompute_requested_at`。基础设施故障使用稳定的 `preferences.*` 错误码；无效输入直接返回 FastAPI 标准 `422`，不会调用持久化层。

## 持久化与重算边界

迁移 `0006_single_user_preferences` 创建 `user_preferences`，并插入唯一一行 `id=1`。检查约束会拒绝任何第二个用户 ID。JSON 字段必须是数组，学历值受数据库约束，所有审计时间都是带时区的 UTC 时刻。

更新会锁定单例行，在一个事务中替换全部值并设置 `updated_at`。`trigger_recompute` 默认为 `true`；启用时设置粘性的 `recompute_required` 标志，并记录 `recompute_requested_at`。`trigger_recompute=false` 的更新绝不会清除已经待处理的信号。JAI-023 的 [`SqlAlchemyMatchingService`](MATCHING.md) 只会在完整版本化重算的同一事务中消费并确认该信号；成功确认会保留 `updated_at`，以标识本批次使用的偏好值，任何失败都会回滚且不丢失粘性信号。JAI-022 有意不提供评分逻辑或公开确认端点。

## 范围边界

JAI-022 不新增硬过滤、匹配得分、评分版本、解释、日报生成、多用户认证或来源特定行为，也不会从已采集招聘数据中猜测用户偏好。
