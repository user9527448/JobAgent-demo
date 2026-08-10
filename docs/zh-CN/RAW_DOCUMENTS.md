# 原始公告 URL 规范化与版本化

> 英文原文：[Raw-document canonicalization and versioning](../RAW_DOCUMENTS.md)。修改原文时必须在同一提交中同步更新本镜像。

JAI-009 把 Adapter 输出转换为规范、不可变的来源公告版本。Adapter 仍通过 `RawDocumentInput` 返回未经修改的 HTML/文本；公共代码负责 URL 规范化、内容指纹和 PostgreSQL 幂等写入。

## URL 规范化

`canonicalize_url()` 应用确定性的 HTTP(S) 规则：

- 以 `sources.base_url` 为基准解析相对链接；
- 将协议和经 IDNA 规范化的主机名转为小写；
- 删除默认端口和片段；
- 规范化点路径段和百分号转义；
- 删除明确的跟踪参数（`utm_*`、`fbclid`、`gclid`、`mc_cid`、`mc_eid`、`spm`、`yclid`）；
- 保留、排序并重新编码其他全部查询参数，包括重复键和空值。

缺少主机、协议不受支持、包含嵌入凭据或端口非法的 URL 会以 `crawler.document_url_invalid` 失败。实现会有意保留未知查询参数，因为它们可能选择真实公告，而不是用于访客跟踪。

## 内容指纹

SHA-256 的输入是稳定可见的正文文本，而不是易变的 HTML 格式：

1. 优先使用 Adapter 提供的非空 `raw_text`。
2. 否则提取 HTML 正文中的可见文本，排除 script、style、template 和 noscript 内容。
3. 使用 NFKC 规范化 Unicode，并折叠空白。
4. 对 UTF-8 字节计算 SHA-256。

未经修改的 `raw_html` 和 `raw_text` 会作为证据存储。没有可见文本的输入以 `crawler.document_content_empty` 失败，而不是为空字符串生成误导性指纹。

## 幂等版本策略

每条 `raw_documents` 记录代表一个不可变内容版本：

```text
source + canonical URL
  version 1 (is_current=false)
       <- version 2 (is_current=false, supersedes=1)
            <- version 3 (is_current=true, supersedes=2)
```

`SqlAlchemyRawDocumentRepository.save()` 返回以下状态之一：

| 状态 | 行为 |
|---|---|
| `created` | 不存在当前记录；插入版本 1 |
| `unchanged` | 当前指纹相同；复用其 ID 和版本 |
| `updated` | 指纹发生变化；保留旧记录并插入下一版本 |

PostgreSQL 强制 `(source_id, canonical_url, version)` 唯一，并通过部分唯一索引让每个来源 URL 恰好只有一个当前版本。事务级 advisory lock 串行化同一来源 URL 的并发首次写入，因此竞争的重复运行会得到一个 `created` 和一个 `unchanged` 结果。

当前版本对应的 HTTP `ETag` 和 `Last-Modified` 会保存给下一次条件 GET。同内容响应可以刷新已提供的校验值，但不会替换原始来源证据；未提供的校验值继续保留之前值。

## 边界

- 仓库准备并持久化单条成功 Adapter 输出；采集运行编排仍负责隔离单条失败。
- 确定原始公告版本后，JAI-010 执行[附件 URL 发现、MIME/签名校验、哈希和原子文件存储](ATTACHMENTS.md)。
- 结构化抽取和字段证据继续引用提供它们的准确、不可变原始公告版本。

迁移 `0002_raw_document_versions` 会把现有记录升级为版本 1/当前版本。只有在没有 URL 已累积多个版本时，才能安全降级回每个 URL 一行的原始 Schema；否则 PostgreSQL 会拒绝旧唯一约束，而不是丢弃证据。
