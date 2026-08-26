# JOBAGENT 简体中文文档索引

> English index: [`../en-US/README.md`](../en-US/README.md)。

仓库文档使用独立的英文和简体中文文件。修改任一语言版本时，必须在同一提交同步对应版本；代码标识符、环境变量、错误码、URL 和命令保持原样。存量单语文档按 JAI-047/JAI-048 分批迁移，不允许用一种语言覆盖另一种语言。

## 当前双语文档

| 主题 | 简体中文 | English |
|---|---|---|
| 仓库协作规范 | [中文](AGENTS.md) | [English](../../AGENTS.md) |
| 详细开发计划 | [中文](../DEVELOPMENT_PLAN.md) | [English](../en-US/DEVELOPMENT_PLAN.md) |
| GitHub Issues Backlog | [中文](../GITHUB_ISSUES.md) | [English](../en-US/GITHUB_ISSUES.md) |
| 持续开发工作日志 | [中文](WORKLOG.md) | [English](../WORKLOG.md) |
| Source Adapter 与采集编排 | [中文](COLLECTION.md) | [English](../COLLECTION.md) |
| 数据库模型与迁移 | [中文](DATABASE.md) | [English](../DATABASE.md) |
| 来源 HTTP 客户端策略 | [中文](HTTP_CLIENT.md) | [English](../HTTP_CLIENT.md) |
| 原始公告规范化与版本化 | [中文](RAW_DOCUMENTS.md) | [English](../RAW_DOCUMENTS.md) |
| 附件发现与存储 | [中文](ATTACHMENTS.md) | [English](../ATTACHMENTS.md) |
| 解析器协议与标准中间格式 | [中文](PARSING.md) | [English](../PARSING.md) |
| 确定性字段抽取与规范化 | [中文](EXTRACTION.md) | [English](../EXTRACTION.md) |
| 可替换 LLM 抽取服务 | [中文](LLM_EXTRACTION.md) | [English](../LLM_EXTRACTION.md) |
| 抽取结果合并与字段证据 | [中文](MERGING_AND_EVIDENCE.md) | [English](../MERGING_AND_EVIDENCE.md) |
| 数据校验、待复核与重解析 | [中文](VALIDATION_AND_REPARSING.md) | [English](../VALIDATION_AND_REPARSING.md) |
| 来源 4、5 与稳定性验证 | [中文](SOURCE_STABILITY.md) | [English](../SOURCE_STABILITY.md) |
| 招聘信息目标网站库 | [中文](../SOURCE_CATALOG.md) | [English](../en-US/SOURCE_CATALOG.md) |
| JAI-005 济宁来源技术验证 | [中文](spikes/JAI-005-JINING-SOURCE.md) | [English](../spikes/JAI-005-JINING-SOURCE.md) |
| 数据库迁移说明 | [中文](MIGRATIONS.md) | [English](../../migrations/README.md) |
| JAI-005 固定样本说明 | [中文](fixtures/JINING.md) | [English](../../tests/fixtures/jining/README.md) |
| JAI-016 附件黄金样本 | [中文](fixtures/ATTACHMENTS.md) | [English](../../tests/fixtures/attachments/README.md) |
| JAI-021 NCSS 固定样本 | [中文](fixtures/NCSS.md) | [English](../../tests/fixtures/ncss/README.md) |
| JAI-021 上海人社固定样本 | [中文](fixtures/SHANGHAI_RSJ.md) | [English](../../tests/fixtures/shanghai_rsj/README.md) |

## 历史归档

- [JAI-046 之前的原混合语言 WORKLOG](../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)逐字节保留，SHA-256 为 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`。
- 历史归档不再追加记录，也不要求翻译；当前工作只写入上表中的独立中英文活动日志。

## JAI-048 存量迁移清单

以下仓库自有文档仍缺少独立语言版本。JAI-048 将逐份保留原文件语言并新增缺失镜像；如果其他 Issue 先实质修改其中任何文件，必须在同一提交提前补齐对应版本。

| 文档 | 当前语言 | 缺失版本 |
|---|---|---|
| [项目 README](../../README.md) | 简体中文 | English |
| [配置、日志与错误约定](../CONFIGURATION.md) | 简体中文 | English |
| [非官方招聘信息参考源](../REFERENCE_SOURCES.md) | 简体中文 | English |
| [Firstjob 固定样本说明](../../tests/fixtures/firstjob/README.md) | English | 简体中文 |
| [江苏人事考试固定样本说明](../../tests/fixtures/jiangsu/README.md) | 简体中文 | English |
| [国资委固定样本说明](../../tests/fixtures/sasac/README.md) | 简体中文 | English |

## 同步规则

1. 修改已配对文档时，在同一提交更新两种语言版本。
2. 新增仓库文档时，同时创建英文和简体中文文件并加入两份索引。
3. 两种语言保持相同的章节、约束和示例语义；不翻译代码/API 标识符。
4. 若两种语言出现歧义，以实际代码和测试为准，并在同一修复中同步纠正。
5. 历史归档与第三方原始材料必须明确标注不翻译理由，不得伪装成已配对文档。
