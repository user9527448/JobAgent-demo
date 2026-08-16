# 附件发现与存储

> 英文原文：[Attachment discovery and storage](../ATTACHMENTS.md)。修改原文时必须在同一提交中同步更新本镜像。

JAI-010 为不可变原始公告版本链接的 PDF、XLS 和 XLSX 文件提供有界、可追溯的存储。文件解释属于后续流水线阶段；成功存储文件绝不等同于已解析。

## 发现

`discover_attachment_links()` 检查公告中的锚点元素，并按文档顺序返回支持的链接。它会：

- 从 URL 路径或可见链接文本识别 `.pdf`、`.xls` 和 `.xlsx`；
- 解析相对 URL，并应用与原始公告相同的规范化规则；
- 删除片段和已知跟踪参数，同时保留有业务含义的查询参数；
- 在同一公告内按规范 URL 去重；
- 清理显示名称，但不把显示名称用作存储路径。

发现阶段不抓取链接，也不从页面任意文本中推断附件。

## 下载与校验

`AttachmentStorageService` 使用公共来源 HTTP 客户端的流式请求路径，因此来源并发、请求节奏、超时、重试和安全日志规则仍然生效。`Content-Length` 和实际流式字节都会与 `JOBAGENT_ATTACHMENT_MAX_BYTES` 比较；流式分块使用 `JOBAGENT_ATTACHMENT_CHUNK_BYTES`。

仅有扩展名不足以接受文件：

| 声明类型 | 必需内容 | 接受的响应 MIME 类型 |
|---|---|---|
| PDF | 文件开头附近存在 `%PDF-` 签名 | `application/pdf` 或通用二进制类型 |
| XLS | OLE 复合文件签名 | `application/vnd.ms-excel` 或通用二进制类型 |
| XLSX | ZIP 内含 `[Content_Types].xml` 和 `xl/workbook.xml` | XLSX MIME、`application/zip` 或通用二进制类型 |

HTML 错误页、空响应体、签名不匹配和不兼容的非通用 MIME 类型都会被拒绝。校验只用于确认文件身份；公共解析器契约和 JAI-014 PDF 文本解析器见 [`PARSING.md`](PARSING.md)，OCR 仍为延期项，表格解析属于 JAI-015/JAI-016。

## 原子内容寻址存储

服务把响应流写入 `<storage-root>/.tmp`，完整文件刷新并同步到磁盘后进行校验和 SHA-256 计算，最后通过同卷原子替换发布。最终对象路径为：

```text
objects/<sha256-前两位>/<sha256>.<extension>
```

数据库保存相对路径，而不是机器专用的绝对路径。重复处理同一文档 URL 时，如果数据库记录和本地对象有效，就会直接复用而不再请求。不同 URL 的相同内容会汇聚到同一对象路径。中断或被拒绝的下载会删除 `.part` 文件，也不能被标记为 `stored`。

## 数据库状态

附件下载和解析是两个独立状态机：

- `download_status`：`pending`、`stored` 或 `failed`；
- `parse_status`：在后续解析 Issue 运行前保持 `pending`；
- 成功存储要求 MIME 类型、SHA-256、相对路径、字节数和下载时间；
- 失败会清除成功存储元数据，只记录安全错误码/消息。

唯一约束 `(document_id, url)` 和 PostgreSQL advisory lock 防止重复元数据行。即使两个 worker 在创建记录后竞争，内容寻址最终路径也能防止产生重复文件对象。

## 配置

| 环境变量 | 默认值 | 用途 |
|---|---:|---|
| `JOBAGENT_ATTACHMENT_STORAGE_PATH` | `data/attachments` | 本地附件对象存储根目录 |
| `JOBAGENT_ATTACHMENT_MAX_BYTES` | `26214400` | 最大响应大小（25 MiB） |
| `JOBAGENT_ATTACHMENT_CHUNK_BYTES` | `65536` | 流式读写分块大小 |

Compose 把存储根目录映射到 `/app/data/attachments` 的命名卷 `attachment-data`，非 root API 用户具有写权限。运行时附件数据不会进入 Git。
