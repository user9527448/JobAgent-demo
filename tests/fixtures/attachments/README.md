# JAI-016 attachment golden fixtures

> 简体中文：[JAI-016 附件黄金样本](../../../docs/zh-CN/fixtures/ATTACHMENTS.md)

This directory contains ten synthetic, sanitized fixtures for offline parser regression: five PDF files and five XLSX workbooks. They cover multiple pages, sparse/blank PDF text, Chinese and English headers, multiple worksheets, merged cells, blank rows, and an unrecognized-header review result. They contain no applicant records, credentials, downloaded source material, or real personal data.

`manifest.json` stores the reviewed expected intermediate results, including statuses, stable issue codes, complete text/table blocks, and page or A1 cell evidence. Run:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_attachment_fixtures.py
```

The command performs no network access. It prints total, matched, success rate, and case-level expected/actual differences, and exits non-zero when any case differs.

`scripts/generate_attachment_fixtures.py` documents how the synthetic binaries and snapshots were created. Regenerate only as an intentional reviewed fixture update; never use it to hide an unintended parser regression.
