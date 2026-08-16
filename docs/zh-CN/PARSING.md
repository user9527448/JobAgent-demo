# 解析器协议与标准中间格式

> English: [Parser contracts and standard intermediate format](../PARSING.md)

JAI-013 定义已存储来源内容与后续格式专用解析/抽取之间的公共边界。JAI-014 和 JAI-015 在该边界上增加显式注册的 PDF 与 XLSX 实现。持久化编排和字段抽取仍属于后续 Issue；OCR 继续延期到 JAI-B01。

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

## XLSX 岗位表解析器

JAI-015 新增面向规范 XLSX MIME 类型的 `ExcelPositionTableParser`，并通过 `build_parser_registry()` 注册。它只在本地使用 `openpyxl`，不会执行工作簿宏、外部链接或网络请求。

- 每个工作表最多扫描前 20 行。表头必须包含已识别的岗位名称标签和至少一个其他招聘标签；识别时合并表头的从属单元格继承锚点值，多个候选存在时确定性选择识别项最多且最靠前的一行。
- 表头非空单元格的列范围定义表格列。全空数据行会跳过，但 `source_rows`、表头行、数据边界和跳过行数仍保存在块元数据中。
- 每个输出单元格均携带工作表和 A1 格式的 `CellRangeLocation`。继承合并单元格值的位置指向完整原合并范围，不会把空白从属坐标伪造为证据来源。
- 每个已识别且含数据的工作表生成一个 `TableBlock`；多个工作表按原顺序输出。无法识别的工作表生成 `parser.header_not_recognized` 和 `review_required=true`；若其他工作表成功，结果仍可为 `parsed` 并保留这些待复核警告。
- 若没有任何工作表生成表格，结果为带复核诊断的 `failed`。这里刻意复用既有附件状态词汇，不提前新增计划外复核状态；后续复核流程属于 JAI-020。
- 损坏、加密或无效 XLSX 字节返回 `parser.corrupt_document`；直接使用非 XLSX MIME 调用时返回 `parser.invalid_input`。

旧版 XLS（`application/vnd.ms-excel`）有意不注册。既有环境没有可行的 XLS 读取器；在缺少代表性样本时新增 `xlrd` 或第二套 dataframe 依赖会无证据地扩大 Issue。注册表因此对 XLS 返回标准的显式 `unsupported` 结果；JAI-016 可用固定样本支撑后续依赖决策。

## 离线黄金样本回归

JAI-016 提交 10 份纯合成脱敏 PDF/XLSX 样本和已审查的 `manifest.json`。`serialize_parse_result()` 规范化状态、解析器名称、稳定错误码、完整中间块及页码/单元格位置，同时排除不稳定的来源 ID 和第三方库元数据。

`evaluate_golden_fixtures()` 通过生产注册表解析全部本地样本，返回总数、匹配数、成功率和完整逐样本 expected/actual 差异。`scripts/evaluate_attachment_fixtures.py` 以稳定 JSON 输出报告，任何差异都会返回非零退出码；整个过程不访问网络。重新生成样本属于显式审查操作，不是常规测试步骤。

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
- `parser.header_not_recognized`
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
