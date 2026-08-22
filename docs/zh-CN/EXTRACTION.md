# 确定性字段抽取与规范化

> English mirror: [`../EXTRACTION.md`](../EXTRACTION.md)。

JAI-017 在可追溯解析器中间格式之上新增纯内存的确定性抽取层，不写入业务表或证据表。只有解析器块或表格单元格直接支持某个值时，抽取器才会输出该字段。

## 契约

`DeterministicFieldExtractor.extract()` 接收一个 `ParseResult` 并返回 `ExtractionResult`。记录保持解析器顺序，每条记录对应一个文本块或一行表格数据。

每个 `ExtractedField` 都包含：

- 稳定的 `FieldName`；
- 证据直接支持的原始 `raw_value`；
- 确定性的 `normalized_value`；
- 带解析器页/行/单元格位置和原文引文的 `ExtractionEvidence`；
- 稳定的 `rule_id` 和结果级 `extractor_version`。

契约会拒绝空证据、无时区日期时间、非正数招聘人数、空地区集合和混合解析来源。已有证据但不支持或相互矛盾的值会生成保留原值与证据的 `ExtractionIssue`，绝不会静默转换成猜测字段。

## 支持字段

| 字段 | 确定性输入 | 规范输出 |
|---|---|---|
| `start_at` / `deadline` | 带标签的正文日期/范围或已识别表头 | UTC 感知的 `datetime` |
| `region` | 带标签的正文或地点/地区列 | 按来源顺序排列的省级稳定代码元组 |
| `organization` | 明确的单位/用人单位标签或列 | NFKC 与空白规范化文本 |
| `apply_url` | 明确的报名/申请标签或列 | 规范 HTTP(S) URL |
| `headcount` | 一个精确正整数，可带“人/名/个” | 正 `int` |
| `education` | 有界字典中的精确值 | 稳定学历枚举字符串 |
| `category` | 有界字典中的精确招聘类型 | 稳定招聘类别字符串 |

自由正文中没有标签的日期、地区、单位、URL、学历词和数字一律忽略，避免把公告来源链接、发布日期或偶然出现的单位名称错误标记为报名字段。

## 日期与时区规则

已支持黄金样本中的 `YYYY-MM-DD`、`YYYY/MM/DD` 和 `YYYY年M月D日`；证据中还可以带时间与受支持时区。日期范围必须包含两个有证据的值。默认配置时区为 `Asia/Shanghai`，并显式识别 `Z`、`UTC`、`GMT`、`Asia/Shanghai`、北京时间标签和 UTC/GMT 数字偏移。

所有输出统一转换为 UTC。只有日期的开始时间使用当地 `00:00:00`，只有日期的截止时间使用当地当日末尾。无效日历日期生成 `extraction.invalid_date`。开始时间晚于截止时间时，该记录中的两个日期字段都会被移除，并由 `extraction.date_range_inverted` 保留两个原值及证据。

## 字典与 URL 边界

地区字典覆盖全国范围，以及中国大陆省级行政区、香港、澳门和台湾的有界中英文别名；同时出现具体地区和全国别名时以具体地区为准。学历规范化区分 `bachelor`、`bachelor_or_above`、`master`、`master_or_above`、`doctorate` 等精确要求；不支持的描述保留为诊断。

报名 URL 必须有直接标签且使用 HTTP(S)。相对路径必须显式提供来源 `base_url`；抽取器不会猜测主机。规范化会删除片段和跟踪参数，同时保留业务查询参数；带凭据 URL 和不支持的协议会被拒绝。

## Issue 边界

- JAI-017 不调用 LLM，也不定义 provider、Prompt、token 预算、重试或成本行为；这些属于 JAI-018。
- JAI-017 按解析器块/表格行保持记录分离，不合并正文与附件结果，也不解决跨来源冲突。
- JAI-017 不持久化 `job_posts`、`job_positions` 或数据库 `field_evidence`；这些操作属于 JAI-019。
- OCR 继续延期至 JAI-B01。抽取器可以检查 `ocr_required` 已经返回的部分文本，但不会推断缺失字段。
