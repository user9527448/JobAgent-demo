# Source Adapter 与采集编排

> 英文原文：[Source Adapter and collection orchestration](../COLLECTION.md)。修改原文时必须在同一提交中同步更新本镜像。

JAI-007 建立来源插件边界和通用批处理流程。HTTP 行为由 JAI-008 的[来源 HTTP 客户端策略](HTTP_CLIENT.md)单独提供，JAI-009 提供[原始公告规范化持久化](RAW_DOCUMENTS.md)，JAI-010 在下游增加[附件发现与存储](ATTACHMENTS.md)。

JAI-011 增加可手工维护的 `config/source_catalog.toml`。中文的[目标网站库与维护说明](../SOURCE_CATALOG.md)登记校招、江浙沪公职考试、央国企官方来源。只有标记为 `active` 且 `enabled`、并已有显式 Adapter 实现的条目才可运行。

标题过滤属于来源级配置：候选标题命中任一 `exclude_keywords` 时优先排除；存在 `include_keywords` 时，至少命中其中一项才保留。关键词只影响发现阶段，绝不修改所保存的来源 HTML。

## Adapter 契约

每个来源使用 `sources.adapter` 中保存的名称显式注册工厂。工厂接收 `SourceDefinition`，并返回实现以下接口的对象：

```python
class SourceAdapter(Protocol):
    async def discover(self, cursor: dict[str, JsonValue] | None) -> Sequence[DiscoveredItem]: ...

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput: ...
```

- `discover` 只产出来源 URL 和少量来源专用元数据。
- `fetch_detail` 返回未经修改的 HTML 和/或文本，以及基础来源追踪字段。
- Adapter 不创建 `crawl_runs`、不执行公共重试、不持久化原始公告，也不控制批处理循环。
- 注册必须显式完成，不允许动态导入，也不接受配置中的任意 Adapter 名称。

## 批处理流程

```text
加载已启用来源
  -> 解析已注册 Adapter
  -> 创建 running 状态的 crawl_run
  -> 发现候选项
  -> 逐条抓取详情，并隔离单条错误
  -> 在发现完成后及每条处理后持久化进度
  -> 以 succeeded / partial / failed 结束
```

未知 Adapter、来源不存在或来源已停用，会在创建运行记录前失败。发现阶段失败会把运行标记为失败并重新抛出异常。详情失败会转换为安全的结构化失败，写入运行统计，同时不阻止后续条目。

取消不会被吞掉：运行先标记为 `cancelled`，随后重新抛出取消异常。

## 运行统计

`crawl_runs.stats` 包含稳定的计数器和步骤状态：

```json
{
  "discovered": 3,
  "detail_succeeded": 2,
  "detail_failed": 1,
  "steps": {
    "discover": {"status": "succeeded", "count": 3},
    "fetch_detail": {"status": "partial", "succeeded": 2, "failed": 1}
  },
  "failures": [
    {
      "url": "https://example.invalid/jobs/2",
      "code": "crawler.adapter_fetch_detail_failed",
      "message": "Adapter fetch_detail failed with RuntimeError.",
      "retryable": false
    }
  ]
}
```

意外异常的原始消息不会持久化，因为其中可能包含上游响应数据或凭据。领域错误会保留其已明确标记为安全的错误码、消息和可重试性。

## 下游持久化边界

完成的 `CrawlBatchResult` 会把成功的 `RawDocumentInput` 对象交给 `SqlAlchemyRawDocumentRepository`。仓库解析规范 URL、计算规范化内容的 SHA-256，并以原子方式创建、复用或版本化不可变 `raw_documents` 记录，无需改变各来源 Adapter。HTTP 缓存校验值会保留给后续条件请求。

附件发现和文件持久化不发生在 Adapter 或批处理循环内部。确定原始公告版本后，JAI-010 附件服务从该版本 HTML 中发现支持的链接，并以公告文档 ID 为归属原子存储已验证文件。

## JAI-011 首个来源

`SasacRecruitmentAdapter` 通过 `SourceHttpClient` 读取国务院国资委央企公开招聘列表和详情。它按稳定的公开 URL 语义识别详情链接，移除查询串/片段和重复 URL，应用网站库关键词，并保留完整详情 HTML、可读文本和发布时间来源信息。`scripts/run_source_preview.py` 可列出网站库，或执行不写数据库的低频只读预览。

契约测试只使用最小化离线样本。当前 Windows 环境无法完成到 `sasac.gov.cn` 的 TLS 访问，浏览器检查又被安全策略拒绝，因此在进入定时任务前仍必须补做线上冒烟。
