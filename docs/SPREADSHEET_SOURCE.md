# Spreadsheet source contract

> Simplified Chinese: [表格数据源契约](zh-CN/SPREADSHEET_SOURCE.md)

## 1. Purpose and status

This document preserves the withdrawn JAI-052 design audit. The owner withdrew the spreadsheet-Agent acceleration proposal on 2026-09-23 and restored the original project plan. This document is historical evidence, not an active implementation contract.

The owner supplied the shared Feishu Bitable link and authorized G1 read-only inspection on 2026-09-23. G1 completed without writing, exporting, downloading, or persisting source data. `A-007/G2` was then cancelled; no implementation may begin and the source must not be accessed again.

## 2. Source boundary

The implementation must keep three explicit layers:

1. **Raw observation**: capture source URL/workbook identity, sheet identity, retrieval time, provider-visible update metadata when available, content hash, and an immutable raw snapshot reference. Raw business files and downloaded snapshots are runtime data and must not be committed to Git.
2. **Prepared records**: apply deterministic header normalization, whitespace/date/value normalization, classification, validation, and duplicate detection. Preserve rejected rows with bounded safe reason codes and source coordinates; never invent missing values.
3. **Canonical jobs**: map accepted rows into the existing stable job-query boundary with source provenance. Agent and UI consumers read this layer instead of reading arbitrary workbook cells directly.

The crawler remains another producer of canonical jobs. JAI-052 must not delete crawler tables, adapters, scheduling history, or source evidence.

## 3. Identity, refresh, and idempotency

The exact identity rule is an approval item after the workbook audit. The design must distinguish:

- workbook and sheet identity;
- source row identity or a documented deterministic fallback;
- row content hash and normalized content hash;
- first/last observed timestamps and source-provided update time, when present;
- unchanged, changed, new, missing-from-current-snapshot, and rejected observations.

Refreshing the same workbook version must not duplicate canonical records. A row disappearing from a later snapshot must not be hard-deleted automatically; the approved policy must define whether it becomes inactive, expired, or merely unobserved. Source snapshots and import runs require auditable counts for discovered, accepted, changed, unchanged, rejected, and missing rows.

## 4. Cleaning and classification

JAI-052 may implement only rules confirmed by observed workbook evidence and approved mapping. Candidate categories include organization, organization type, region, role family, education, experience, application deadline, source URL, and free-text notes, but none is a committed source column until the audit proves it.

Rules must be deterministic and testable. Ambiguous values stay explicit, original cell text remains traceable, and a classification rule change receives a version. Synthetic fixtures may model the approved shape; real workbook rows, personal data, credentials, and downloaded files must not enter tests or Git.

## 5. Access and security

- JAI-052 begins with read-only access only.
- The shared source is permanently read-only from JOBAGENT's perspective. No implementation, operator command, test, or recovery path may edit cells, views, filters, sorting, comments, sharing, permissions, or other source state. There is no write-back mode.
- Public links may be recorded as source configuration only after the owner supplies and approves them. Private links, access tokens, cookies, passwords, and signed URLs must not be committed or pasted into logs, fixtures, database error text, or documentation.
- If authentication is required, the access mechanism and environment-variable boundary require a separate approval after the read-only audit. Do not bypass login, CAPTCHA, access control, sharing restrictions, or provider terms.
- Provider errors are mapped to safe internal reason codes; raw response bodies and secrets are not persisted.

## 6. Agent and UI boundary

The accelerated path is read-only:

1. JAI-052 creates the spreadsheet acquisition/normalization contract and canonical source adapter.
2. JAI-032 exposes stable search, detail, filtering, and explanation services over canonical jobs.
3. JAI-033 exposes only read-only Agent tools for the first slice.
4. JAI-034 implements single-Agent orchestration and evaluation.
5. JAI-053 adds the Agent conversation and filter experience to the existing JAI-050 production shell.

`run_crawl`, report generation, source toggles, reruns, delivery, workbook writes, and other mutations remain outside this slice. They return only when their original dependencies and approval gates resume.

## 7. Approval gates

| Gate | Evidence | Permission after approval |
|---|---|---|
| G0 | Remote JAI-027/JAI-050 branches and checkpoint tag verified | Preserve the pre-pivot baseline; no product behavior change |
| G1 | Owner supplies the workbook link and authorizes read-only inspection; sheet/header/update evidence is recorded | Read and profile the named workbook only |
| G2 | Owner approves exact field mapping, identity, disappearance, refresh, and access rules | Implement the importer against synthetic fixtures |
| G3 | Offline tests and PostgreSQL tests use only a database ending in `_test`; no real source write occurs | Implement bounded persisted import and canonical mapping |
| G4 | Owner approves daily refresh activation after a read-only production review | Enable scheduled refresh separately from crawler scheduling |

G1 does not authorize database migration, background refresh, production import, external write, or Agent implementation. Any new migration, authenticated connector, or real recurring fetch must be presented with impact evidence before its gate opens.

## 8. G1 intake checklist

When the owner supplies the link, record without exposing secrets:

- provider and link type; public or authenticated access;
- workbook identity, sheet list, header rows, merged cells, formulas, and hidden rows/columns;
- sample-free structural types, approximate row count, and update indicators;
- whether rows are appended, edited in place, deleted, reordered, or split across sheets;
- candidate stable keys and duplicate cases;
- date/time zone, blank/error/formula semantics, and category vocabularies;
- provider rate/export limits and terms relevant to automated read-only access.

The G1 report must separate observed facts, unresolved questions, and proposed mappings. Implementation begins only after G2 approval.

## 9. G1 evidence — 2026-09-23

### 9.1 Observed facts

- The supplied resource is a public shared Feishu Bitable named `☛秋招+春招汇总表（全年直投）`. The exact shared URL and its query parameters remain runtime-only and are not recorded in Git.
- The anonymous share grants view and preview only. Edit, comment, export, print, collaboration management, metadata management, duplication, and operation-history access are unavailable. The inspecting identity is not the owner.
- The main table `❤秋招+春招汇总表` reports 10,082 records and ten views: the combined autumn/spring list, internship list, previous-graduate list, no-written-test list, state-owned/public-sector, foreign-enterprise, finance/banking, internet, arts, and college-applicable views.
- Three additional tables are visible: `央国企&事业单位` with 200 records, `内推码` with 321 records, and `笔试题库` with 12 records. Their record contents and complete field schemas were not inspected. They are outside the proposed first source scope.
- The main table exposes 18 fields: `投递链接`, `行业分类`, `工作地点`, `父记录 2`, `届次`, `批次`, `更新时间`, `学历要求`, `公司名称`, `公告链接`, `企业性质`, `文本 10`, `招聘岗位`, `是否笔试`, `公告来源`, `专业要求`, `截止时间`, and `父记录`.
- Feishu marks `更新时间` as the schema primary key, but timestamps are not stable row identities. Provider table identity plus provider record ID is available and is the safer source identity.
- The bootstrap response exposed values for only a 2,000-record window, although metadata covered all 10,082 records. In that window, company, position, application link, source, and location were populated for all 2,000 records. Rich text and multi-select fields used mixed object/scalar/array representations and require deterministic normalization.
- In that 2,000-record window, application links had 35 duplicate groups covering 94 rows, announcement links had 9 groups covering 18 rows, while `(公司名称, 招聘岗位, 投递链接)` had no exact duplicate group. URL alone is therefore not a valid source-row identity.
- Record modification metadata across all 10,082 records shows 151 changes on 2026-09-18, 237 on 09-19, 89 on 09-20, 91 on 09-21, 217 on 09-22, and 158 on 09-23 in `Asia/Shanghai`. This confirms continuing daily changes but does not prove append-only behavior or guarantee a future refresh time.
- Inspection used bounded read-only public responses and decoded structural metadata in memory only. No login, credential, write endpoint, export, local workbook, raw row dump, database write, or scheduler action was used.

### 9.2 Unresolved questions

- The public-share browser endpoints are not a committed official automation contract and may change. Recurring production access requires a separate G4 review of stability, provider terms, rate limits, and failure behavior.
- The source owner's willingness to grant a read-only Feishu OpenAPI application is unknown. Official OpenAPI is preferred for a durable connector if such authorization becomes available; no credential request is part of G2.
- Row deletion, archival, reordering, formula behavior, hidden fields, and auxiliary-table relationships were not proven by G1. Missing rows must therefore remain non-destructive observations rather than deletions.
- `截止时间` contains multiple source text forms. Only unambiguous dates may populate the canonical deadline; ambiguous/raw values must remain traceable and raise a bounded validation result.

## 10. A-007/G2 recommendation

Approval is requested for the following bounded implementation contract:

1. Limit the first source to `❤秋招+春招汇总表`; exclude `央国企&事业单位`, `内推码`, and `笔试题库`.
2. Use `(provider, workbook/base identity, table_id, record_id)` as source identity. Use normalized content hashes only for change detection, never as identity.
3. Reuse existing `sources`, `crawl_runs`, `raw_documents`, `job_posts`, and `job_positions`. Do not create a second job domain or delete crawler evidence.
4. Introduce a provider-neutral read-only `SpreadsheetSnapshotReader` boundary. The first implementation uses synthetic fixtures and `_test` databases only; it performs no live recurring retrieval.
5. Fetch one bounded snapshot per future import attempt and normalize it in memory; never issue one provider request per row. Production acquisition remains behind G4. Prefer official Feishu OpenAPI if the owner can authorize a read-only app; otherwise any provisional public-share adapter needs a separate G4 stability/terms approval.
6. Normalize rich text to visible text; normalize scalar/array multi-selects to ordered unique values; validate only `http`/`https` URLs and strip tracking parameters; normalize times to `Asia/Shanghai`; never invent missing or ambiguous values. Version the mapping as `feishu-rollup-v1`.
7. Map company to `JobPost.organization`, normalized industry/company nature to category evidence, location to `JobPost.region` and position location, application link to `JobPost.apply_url`, unambiguous deadline to `JobPost.deadline`, position to `JobPosition.name`, education to `JobPosition.education`, and major to `JobPosition.major`. Preserve cohort, batch, written-test flag, announcement link/source, original deadline, and other unmapped values as traceable raw evidence until a later schema decision.
8. Re-importing unchanged records must reuse existing versions. Changed records create a new immutable raw-document version and deterministic canonical projection. A record absent from a later snapshot becomes `not_observed` evidence only; it is never hard-deleted or automatically expired in G2.
9. Canonicalize record provenance as an `https` source URL containing only stable table/record identity; strip share/user/tracking parameters. Keep the exact shared URL outside Git as runtime configuration.
10. All tests use synthetic response shapes and, where PostgreSQL is needed, a database ending in `_test`. No real Feishu row, share URL, token, cookie, personal data, or response body enters Git, fixtures, logs, or error storage.

The recommendation above was never approved and is retained only to explain the archived branch. The route is withdrawn: there will be no reader/parser, migration, business import, recurring request, scheduler change, Agent/UI implementation, or source write-back. The project continues on its original critical path.

## 11. Withdrawal record

The owner withdrew JAI-052 after confirming that the shared resource disallows download, export, and copy. JAI-052 is not complete and will not merge into the product line. JAI-053 never started and is also withdrawn. The remote audit commits remain immutable evidence; no source link or source data is stored in Git.
