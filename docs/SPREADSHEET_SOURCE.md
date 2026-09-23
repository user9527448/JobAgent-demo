# Spreadsheet source contract

> Simplified Chinese: [表格数据源契约](zh-CN/SPREADSHEET_SOURCE.md)

## 1. Purpose and status

This document defines the design gate for JAI-052. The owner has approved an incremental acceleration track in which a daily updated Excel workbook becomes the first information source for a read-only Agent. The existing crawler, scheduling, delivery, and frontend work is preserved and is not replaced or declared complete.

No workbook has been supplied or inspected yet. Column names, sheet names, row identity, update semantics, access method, and refresh frequency therefore remain unknown and must not be guessed.

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
