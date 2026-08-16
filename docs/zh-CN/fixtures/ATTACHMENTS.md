# JAI-016 附件黄金样本

> English: [JAI-016 attachment golden fixtures](../../../tests/fixtures/attachments/README.md)

此目录包含 10 份用于离线解析回归的纯合成脱敏样本：5 份 PDF 和 5 份 XLSX。它们覆盖多页、稀疏/空白 PDF 文本、中英文表头、多工作表、合并单元格、空行和无法识别表头的复核结果。样本不包含应聘者记录、凭据、下载的来源材料或真实个人数据。

`manifest.json` 保存已审查的期望中间结果，包括状态、稳定错误码、完整文本/表格块，以及页码或 A1 单元格证据。运行：

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_attachment_fixtures.py
```

该命令不访问网络。它输出总数、匹配数、成功率和逐样本 expected/actual 差异；任何样本不一致时返回非零退出码。

`scripts/generate_attachment_fixtures.py` 记录纯合成二进制文件与快照的生成方式。只有在有意且经过审查地更新样本时才重新生成；不得用它掩盖非预期解析回归。
