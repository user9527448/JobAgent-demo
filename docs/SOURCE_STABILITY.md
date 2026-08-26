# Source 4-5 integration and stability verification

> Language: English. Simplified Chinese mirror: [`zh-CN/SOURCE_STABILITY.md`](zh-CN/SOURCE_STABILITY.md).

## 1. Enabled sources

JAI-021 adds two public, read-only official sources to the three JAI-011 Adapters:

- `ncss-jobs` uses the GET job-list endpoint invoked by the official NCSS public job page and reads public detail pages. It never uses login, favorite, resume, or application actions.
- `shanghai-public-institution` uses the Shanghai Human Resources and Social Security public-institution column and accepts only `/tzpgg_17408/` recruitment-announcement paths. Proposed-hire notices and application systems are excluded.

All five catalog sources are `active` and `enabled`, have explicit runtime wiring, and have offline Adapter contract tests. New fixtures are synthetic and sanitized; live pages are never committed.

## 2. Evidence rules

NCSS list fields retain the official job ID, title, organization, region, education, headcount, and publication time before the public detail is materialized. Shanghai organization names are derived only from the exact recruitment title before a fixed recruitment-announcement suffix, with that title retained as evidence.

Date extraction accepts colon or `为` connectors and a value on the next line. For `即日起` or `自公告发布之日起` ranges with one explicit end date, only the evidenced deadline is emitted; no start date is invented. Missing NCSS deadlines and broad Jiangsu topic organization/deadline values remain missing.

## 3. Offline acceptance

Each new source has one synthetic list and three synthetic detail samples. Contract tests cover filtering, same-origin URL restrictions, cursors, public request methods, metadata, visible failures, and explicit runtime registration. PostgreSQL acceptance writes all six documents twice: the first writes are `created`, the second writes are `unchanged`, and only six version-1 rows remain.

## 4. Daily observation command and metrics

Run one bounded observation without database or file writes:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_source_stability.py --limit 3
```

The command limits each source to 1-10 details, uses concurrency 1 and the shared retry/pacing policy, isolates detail failures, and prints JSON only. It reports:

- source success rate: fully successful source runs divided by selected sources;
- detail success rate: successfully fetched details divided by attempted details;
- duplicate rate: repeated canonical URLs or normalized-content SHA-256 fingerprints among successful details;
- core-field completeness: evidenced organization, title, region, deadline, and source link divided by the five possible fields per successful detail.

An observation with a failed source is not a qualified stability day. Empty successful lists are retained as zero-item source runs and never fabricate completeness.

## 5. Observation ledger

| Date | Status | Source success | Detail success | Duplicate rate | Completeness | Evidence |
|---|---|---:|---:|---:|---:|---|
| 2026-08-26 | Pre-observation; not a qualified day | 80% (4/5) | 100% (8/8) | 0% | 55% before rule correction | SASAC exhausted three retries with retryable `PoolTimeout`; no data or history changed |
| 2026-08-26 | Diagnostic reruns; not a qualified day | 100% for four reachable sources | 100% (8/8) | 0% | 67.5% before the Shanghai evidence correction | NCSS 80%, Jiangsu 60%, Shanghai 60%; Firstjob returned zero matching fairs |
| 2026-08-26 | Shanghai correction verification | 100% (1/1) | 100% (3/3) | 0% | 100% (15/15) | Direct title organization and explicit deadline formats only |
| 2026-08-26 | Same-day bounded re-observation; not a qualified day | 80% (4/5) | 100% (7/7) | 0% | 82.86% (29/35) | SASAC again exhausted three retries with `PoolTimeout`; a no-body IPv4 `curl` diagnostic also failed to connect to official port 443 and returned HTTP `000` |

The comparable post-correction diagnostic composite is 82.5% across NCSS (12/15), Jiangsu (6/10), and Shanghai (15/15). It is not a single all-source run and is not counted as day 1. Three consecutive qualified calendar-day observations remain outstanding.

## 6. Known gap and corrective Issue

JAI-049 tracks the remaining evidence-backed completeness gap before the MVP release gate. It must improve or replace low-value broad announcement inputs without inventing organization/deadline values. JAI-021 may satisfy its documented alternative by retaining this explicit corrective Issue, but it still cannot close until three consecutive daily records exist.
