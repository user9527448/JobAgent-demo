# 解析器协议与标准中间格式

> English: [Parser contracts and standard intermediate format](../PARSING.md)

JAI-013 定义已存储来源内容与后续格式专用解析/抽取之间的公共边界。本 Issue 只增加契约和按 MIME 选择能力；PDF 提取、OCR 识别、Excel 启发式、持久化编排和字段抽取仍属于 JAI-014 及后续 Issue。

## 解析输入与选择

`ParseRequest` 包含不可变来源身份和非空字节。`ParseSource` 记录：

- `source_type`：`document` 或 `attachment`；
- 正数持久化 `source_id`；
- `source_name`：可追溯的文件名、对象路径或来源 URL；
- 规范 `media_type`：转为小写并移除可选参数。

`ParserRegistry` 把每个规范 MIME 类型映射到唯一一个显式注册的 `DocumentParser`。解析器名称和 MIME 注册必须唯一；不允许动态导入或执行配置中的任意代码。

对未注册 MIME 类型调用 `ParserRegistry.parse()` 时，会返回状态为 `unsupported`、错误码为 `parser.unsupported_media_type` 的 `ParseResult`，绝不静默丢弃输入。已注册解析器必须返回相同来源身份和其注册名称，否则注册表会抛出永久性契约错误。

## 标准中间格式

每个输出块都携带 `EvidenceLocation`，其中 `source` 必须等于结果的 `ParseSource`：

| Schema | 用途 | 必需定位 |
|---|---|---|
| `TextBlock` | 标题、段落、列表项或其他文本内容 | `PageLocation`、`LineRangeLocation` 或 `CellRangeLocation` |
| `TableBlock` | 按顺序排列的解析单元格行 | 块级页/行/单元格范围 |
| `TableCell` | 表格中的一个值 | 自身的页/行/单元格定位 |
| `PageLocation` | PDF 或分页证据 | 正数、从 1 开始的页码 |
| `LineRangeLocation` | HTML/文本证据 | 包含端点、正数、从 1 开始的行范围 |
| `CellRangeLocation` | 表格证据 | 工作表名称和包含端点、从 1 开始的 A1 单元格范围 |

`TableBlock` 会拒绝引用其他来源的单元格；`ParseResult` 对每个顶层块应用相同约束。因此后续抽取始终可以回到已持久化的文档或附件，而不依赖解析器本地状态。

## PDF 文本解析器

JAI-014 新增 `PdfTextParser`，并通过 `build_parser_registry()` 为 `application/pdf` 显式注册。它复用现有 PyMuPDF 依赖，不访问网络，也不执行 OCR。

- 每个非空页面生成一个规范化 `TextBlock`，携带从 1 开始的 `PageLocation`；保留页面顺序和换行，同时折叠行内重复空白。
- 结果元数据记录页数、非空白字符总数与页均值、页级字符数，以及非空的标准 PDF 元数据字段。
- `PdfTextPolicy.min_average_characters_per_page` 默认是 `40`。低于该确定性平均阈值的文档返回 `ocr_required`；已经提取的部分文本块保留供人工复核，但不会调用 OCR 引擎。
- 密码保护文件返回 `failed` 和 `parser.encrypted_document`；空文件、无效/损坏文件或不可读页树返回 `failed` 和 `parser.corrupt_document`。
- 直接使用非 PDF MIME 调用时返回 `parser.invalid_input`；正常调用方通过注册表选择解析器。

该阈值有意保持保守并允许配置，以便后续固定样本评估。JAI-016 将建立更完整的黄金样本成功率指标；JAI-B01 仍是唯一规划中的 OCR 实现。

## 状态与错误码

`ParseStatus` 与现有附件状态词汇一致：

| 状态 | 含义 |
|---|---|
| `pending` | 已持久化附件尚未完成解析；不能作为已完成 `ParseResult` |
| `parsed` | 已产生至少一个可追溯块 |
| `ocr_required` | 直接解析不足，需要人工/OCR 处理 |
| `unsupported` | 不存在合规解析器或支持的文件变体 |
| `failed` | 已尝试解析，但无法产生有效的完成结果 |

非 `parsed` 结果必须至少包含一个 `ParseIssue`。稳定的 `ParseErrorCode` 值为：

- `parser.unsupported_media_type`
- `parser.invalid_input`
- `parser.invalid_output`
- `parser.corrupt_document`
- `parser.encrypted_document`
- `parser.ocr_required`
- `parser.failed`

Issue 包含安全消息、是否可重试和可选的 JSON 兼容详情，不得包含文件正文、凭据或个人数据。

## 示例

```python
source = ParseSource(
    source_type=ParseSourceType.ATTACHMENT,
    source_id=42,
    source_name="objects/ab/example.pdf",
    media_type="application/pdf",
)
result = registry.parse(ParseRequest(source=source, content=file_bytes))
```

调用方后续可把 `result.status` 和安全诊断映射到附件记录。JAI-013 不新增中间块数据库表，也不启动附件解析 worker。
