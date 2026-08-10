# JOBAGENT 简体中文文档

本目录从 JAI-036 开始维护纯英文技术文档的简体中文镜像。英文原文与中文镜像具有同等技术含义；代码标识符、环境变量、错误码、URL 和命令保持原样。

## 已有中文文档

以下文档原本就是中文，只维护单一版本：

- [项目 README](../../README.md)
- [详细开发计划](../DEVELOPMENT_PLAN.md)
- [GitHub Issues Backlog](../GITHUB_ISSUES.md)
- [配置、日志与错误约定](../CONFIGURATION.md)
- [持续开发工作日志](../WORKLOG.md)（JAI-036 之前的历史记录保留原语言，后续新增记录使用中文）

## 英文文档的中文镜像

| 主题 | 简体中文 | 英文原文 |
|---|---|---|
| 仓库协作规范 | [中文](AGENTS.md) | [English](../../AGENTS.md) |
| Source Adapter 与采集编排 | [中文](COLLECTION.md) | [English](../COLLECTION.md) |
| 数据库模型与迁移 | [中文](DATABASE.md) | [English](../DATABASE.md) |
| 来源 HTTP 客户端策略 | [中文](HTTP_CLIENT.md) | [English](../HTTP_CLIENT.md) |
| 原始公告规范化与版本化 | [中文](RAW_DOCUMENTS.md) | [English](../RAW_DOCUMENTS.md) |
| 附件发现与存储 | [中文](ATTACHMENTS.md) | [English](../ATTACHMENTS.md) |
| JAI-005 济宁来源技术验证 | [中文](spikes/JAI-005-JINING-SOURCE.md) | [English](../spikes/JAI-005-JINING-SOURCE.md) |
| 数据库迁移说明 | [中文](MIGRATIONS.md) | [English](../../migrations/README.md) |
| JAI-005 固定样本说明 | [中文](fixtures/JINING.md) | [English](../../tests/fixtures/jining/README.md) |

## 同步规则

1. 修改上表中的英文原文时，必须在同一提交中更新对应中文镜像。
2. 新增纯英文技术文档时，同时创建 `docs/zh-CN/` 镜像并加入本表。
3. 中文镜像保持相同的章节、约束和示例语义，不翻译代码/API 标识符。
4. 若两种语言出现歧义，以实际代码和测试为准，并在同一修复中同步纠正两份文档。
5. 已经是中文的文档不再复制，以避免无意义的双份维护。
