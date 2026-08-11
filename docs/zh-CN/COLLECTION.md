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

## JAI-011 来源

### 来源 1：国务院国资委招聘

`SasacRecruitmentAdapter` 通过 `SourceHttpClient` 读取国务院国资委央企公开招聘列表和详情。它按稳定的公开 URL 语义识别详情链接，移除查询串/片段和重复 URL，应用网站库关键词，并保留完整详情 HTML、可读文本和发布时间来源信息。`scripts/run_source_preview.py` 可列出网站库，或执行不写数据库的低频只读预览。

契约测试只使用最小化离线样本。当前 Windows 环境无法完成到 `sasac.gov.cn` 的 TLS 访问，浏览器检查又被安全策略拒绝，因此在进入定时任务前仍必须补做线上冒烟。

### 来源 2：江苏省人事考试

`JiangsuPersonnelExamAdapter` 读取江苏省人力资源和社会保障厅人事考试首页、年度专题页与公开文章页。发现阶段只接受同域 HTTPS 且匹配 `/art/YYYY/M/D/art_<column>_<article>.html` 或 `/col/col<id>/index.html` 的路径（排除配置的首页自身），再应用网站库关键词和发布日期游标。详情保留完整 HTML、可读文本、发布日期、地区和官方主体。

该来源覆盖公务员、事业单位和高校毕业生服务项目的公开公告与时间安排。报名、缴费、登录和成绩查询系统不属于 Adapter 边界；公告正文中的相关链接仍作为来源证据保存，但 Adapter 不跟随。四组最小化离线详情样本覆盖年度专题、不同标题/日期结构和带附件公告。

### 来源 3：上海学生就业招聘会

`ShanghaiFirstjobAdapter` 查询上海市学生事务中心公开的高校毕业生招聘会列表。官网单页应用通过表单 POST 暴露该只读列表；Adapter 因此使用范围受限的公共 `post_form_query()` 策略，且绝不调用账号、简历、求职投递或报名功能。发现阶段应用网站库关键词和开始日期游标，再以每场招聘会的 UUID 生成稳定的公开证据 URL。

列表记录已经包含完整公开时间表，因此详情物化不再发出第二次请求。原始 JSON 文本与来源元数据保留 UUID、标题、开始/结束日期和公开海报 URL。三组最小化离线契约样本覆盖不同的 2026 届毕业生招聘会时间表；海报图片格式超出当前附件存储边界，因此 URL 作为来源证据保留。

### 三来源持久化验收

JAI-011 的 PostgreSQL 验收把每个已启用来源的 3 份固定公告连续写入原始公告仓库两次。首轮创建 9 条不可变版本 1 记录；第二轮以 `unchanged` 返回完全相同的 9 个 ID，不新增记录或版本。随后国资委 PDF 和江苏 XLSX 分别执行两次附件发现与原子存储，结果为先 `stored`、后 `reused`，每个 URL 只产生一条数据库记录、一个对象和一次下载。

Firstjob 公开记录提供海报图片，而不是 JAI-010 当前支持的 PDF/XLS/XLSX。Adapter 将经过官方域名约束的图片 URL 保留为来源证据，但不提前扩大附件类型边界；这是明确记录的不支持格式，不会伪造或丢失为不存在的附件。
