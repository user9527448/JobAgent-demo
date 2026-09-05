# JAI-025 Top 20 matching-quality review

> Simplified Chinese: [JAI-025 Top 20 匹配质量评审](zh-CN/MATCHING_QUALITY.md)

JAI-025 adds a deterministic offline comparison around the existing matching engine. The evaluator itself does not collect live data, alter report delivery, schedule jobs, call an LLM, or persist a generated evaluation report. The committed fixture and evaluator make every proposed relevance label, false positive, miss, score, and ranking reproducible. A separately approved bounded run validates the existing live-data flow without adding scheduling or delivery behavior.

## Review set

`tests/fixtures/matching_quality/review-set.json` contains 60 entirely synthetic and sanitized positions evaluated at one explicit instant against one explicit preference profile:

- 30 proposed relevant positions: 15 direct direction/major/region matches, 10 direct direction/major matches with a region tradeoff, and 5 direct matches with missing evidence requiring confirmation;
- 20 proposed non-relevant positions: 10 where a preferred term appears only as incidental requirements context and 10 direct direction/major mismatches;
- 10 non-relevant positions blocked by evidenced validation, deadline, education, or exclusion conditions.

Every record has a binary proposed label, a reason category, and a written rationale. URLs use `example.invalid`; organizations are synthetic. The dataset contains no real applicant, personal data, credentials, downloaded announcement, or runtime output. These labels are intentionally marked as proposed until the project owner reviews them; JAI-025 must not claim a completed human-labelled benchmark before that confirmation.

## Version change

`jai-023-v1` remains supported byte-for-byte as the comparison baseline. The current `jai-025-v2` version changes only the new calculation identity:

| Component | v1 maximum | v2 maximum | v2 behavior |
|---|---:|---:|---|
| Region | 25 | 25 | unchanged exact/national behavior |
| Job direction | 30 | 35 | match only position name, announcement title, or department; requirements-only mentions no longer earn direction points |
| Major | 15 | 20 | same evidence rule with higher relevance weight |
| Organization type | 10 | 10 | unchanged exact enum behavior |
| Deadline urgency | 10 | 5 | same boundaries with scores 5/4/2/1, reducing urgency's ability to outrank fit |
| Information completeness | 10 | 5 | one point per evidenced core field, reducing completeness's ability to outrank fit |

Hard filters are unchanged. Requirements remain part of exclusion matching; v2 removes them only from positive job-direction scoring because incidental references produced the observed false positives.

## Reproducible result

Run:

```powershell
.\.venv\Scripts\python.exe scripts\evaluate_matching_quality.py
```

The fixed proposed labels currently produce:

| Metric at 20 | `jai-023-v1` | `jai-025-v2` | Delta |
|---|---:|---:|---:|
| True positives | 15 | 20 | +5 |
| False positives | 5 | 0 | -5 |
| Misses among 30 relevant labels | 15 | 10 | -5 |
| Precision@20 | 0.750000 | 1.000000 | +0.250000 |
| Recall@20 | 0.500000 | 0.666667 | +0.166667 |

The five v1 false positives are fixture IDs 31–35, all classified `requirements_context_false_positive`. The v1 misses are IDs 16–30: direction/major matches with a region tradeoff or missing evidence. V2 moves IDs 16–20 into Top 20; its remaining misses are IDs 21–30 and are explicitly retained in the report rather than hidden.

Ranking is score-descending with position ID as the stable tie breaker. The evaluator rejects invalid Top-K bounds and compares both versions over exactly the same inputs, preferences, labels, and time.

## Controlled live-flow evidence

On 2026-09-05, the project owner approved a flow-first exception while retaining all public-access and evidence rules. Read-only discovery produced a bounded allocation across NCSS, Jiangsu personnel examination, and Shanghai public institutions. Three manual runs persisted nine public documents with no detail failure: two from NCSS, two from Jiangsu, and five from Shanghai.

Deterministic reparse version `jai-025-live-v1` created nine current posts, two positions, 38 field-evidence rows, and 41 explicit validation issues. One position remained recommendation-eligible; one was blocked by evidenced validation. Seven document bodies produced no position because their useful position tables were in attachments and the current manual-crawl command does not automatically discover/store attachments.

Using unchanged unrestricted default preferences and the published `jai-023-v1` baseline, matching processed both positions, passed one, filtered one, and created two results. Report version `jai-024-v1` created snapshot 1 for 2026-09-05 with one priority item, no closing-soon item, one added-today item, and two needs-confirmation items. A repeated match check was a `not_required` no-op and repeated report generation reused snapshot 1 with the same content hash. Live source bodies, URLs, and runtime output are not committed; only these aggregate verification facts are recorded.

## MVP limitations

- The set is synthetic and pattern-based, not a statistically representative sample of all live sources, employers, regions, or job families.
- Labels are binary and use one preference profile; they do not measure graded relevance or preference diversity.
- Proposed labels require project-owner confirmation before they count as human-labelled acceptance evidence.
- The controlled live run contains only nine documents and two extracted positions; it is end-to-end execution evidence, not a 50-position quality benchmark.
- Attachment discovery/storage is not yet connected to the manual crawl command. This materially limits position yield from public-exam announcements whose tables are PDF/XLSX attachments.
- Matching remains deterministic substring/rule scoring. It has no synonym expansion, semantic retrieval, negation understanding, LLM reranking, or learned calibration.
- V2 deliberately ignores requirements-only positive direction terms. A position whose only reliable job-direction evidence is in requirements can therefore be missed.
- Missing evidence is never guessed. Relevant but incomplete positions may remain outside Top 20 and should still appear in JAI-024's needs-confirmation section.
- Precision/recall on 60 fixed samples is regression evidence, not a production quality guarantee. JAI-049 and later live review must continue tracking source quality and drift.

## Closure and deferred review

The project owner prioritized an executable MVP flow over blocking on live review volume. Current closure evidence therefore combines the explicit synthetic comparison with the bounded live end-to-end run, without relabelling either artifact. The following quality work remains deferred to JAI-049:

1. connect bounded attachment discovery/storage to the persisted collection flow;
2. investigate Firstjob's empty discovery and China Mobile connectivity without bypasses;
3. build and confirm at least 50 distinct live human-labelled positions;
4. compare that benchmark with the current versions and create a new score version if rules must change.

JAI-025 still requires the paired documentation, full PostgreSQL gate, and explicit G5 merge approval. The deferred benchmark does not authorize silent edits to `jai-025-v2` or a production-quality claim.
