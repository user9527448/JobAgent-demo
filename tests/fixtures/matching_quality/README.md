# JAI-025 matching-quality review fixture

> Simplified Chinese guide: [`../../../docs/zh-CN/fixtures/MATCHING_QUALITY.md`](../../../docs/zh-CN/fixtures/MATCHING_QUALITY.md).

`review-set.json` contains 60 entirely synthetic and sanitized job records. It stores proposed binary relevance labels, reason categories, and rationales against one explicit preference snapshot and evaluation instant. No downloaded announcement, applicant record, credential, personal data, or runtime output is included.

The fixture is designed for deterministic offline review. Its proposed labels remain easy to inspect and must be explicitly confirmed by the project owner before JAI-025 is marked complete as a human-labelled benchmark.

Run the comparison with:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_matching_quality.py
```
