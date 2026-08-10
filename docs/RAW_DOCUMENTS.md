# Raw-document canonicalization and versioning

JAI-009 turns Adapter output into canonical, immutable source-document versions. Adapters still return untouched HTML/text through `RawDocumentInput`; shared code owns URL normalization, fingerprints and PostgreSQL idempotency.

## URL canonicalization

`canonicalize_url()` applies deterministic HTTP(S) rules:

- resolve relative links against `sources.base_url`;
- lowercase the scheme and IDNA-normalized host;
- remove default ports and fragments;
- normalize dot segments and percent escapes;
- remove explicit tracking keys (`utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`, `spm`, `yclid`);
- retain, sort and re-encode all other query pairs, including repeated and blank values.

URLs without a host, unsupported schemes, embedded credentials and invalid ports fail with `crawler.document_url_invalid`. The implementation intentionally retains unknown query parameters because they may select a real announcement rather than track a visitor.

## Content fingerprint

The SHA-256 input is stable visible body text, not mutable HTML formatting:

1. Prefer non-empty `raw_text` supplied by the Adapter.
2. Otherwise extract visible HTML body text while excluding script, style, template and noscript content.
3. Normalize Unicode with NFKC and collapse whitespace.
4. Hash the UTF-8 bytes with SHA-256.

Untouched `raw_html` and `raw_text` are stored as evidence. An input with no visible text fails with `crawler.document_content_empty` instead of producing a misleading fingerprint for an empty string.

## Idempotent version policy

Each `raw_documents` row is one immutable content version:

```text
source + canonical URL
  version 1 (is_current=false)
       <- version 2 (is_current=false, supersedes=1)
            <- version 3 (is_current=true, supersedes=2)
```

`SqlAlchemyRawDocumentRepository.save()` returns one of:

| Status | Behavior |
|---|---|
| `created` | No current row exists; insert version 1 |
| `unchanged` | Current fingerprint matches; reuse its ID and version |
| `updated` | Fingerprint changed; retain the old row and insert the next version |

PostgreSQL enforces unique `(source_id, canonical_url, version)` values and a partial unique index allowing exactly one current version per source URL. A transaction-scoped advisory lock serializes concurrent first writes for the same source URL, so racing duplicate runs resolve to one `created` result and one `unchanged` result.

The HTTP `ETag` and `Last-Modified` values associated with the current version are stored for the next conditional GET. A same-content response may refresh supplied validators without replacing raw source evidence; an omitted validator retains its previous value.

## Boundaries

- The repository prepares and persists individual successful Adapter outputs; collection-run orchestration remains responsible for item-level failure isolation.
- Attachment URL discovery, MIME checks, downloads, hashes and atomic file storage begin in JAI-010.
- Structured extraction and field evidence continue to reference the exact immutable raw-document version that supplied them.

The `0002_raw_document_versions` migration upgrades existing rows to version 1/current. Downgrading to the original one-row-per-URL schema is safe only when no URL has accumulated multiple versions; otherwise PostgreSQL rejects the old uniqueness constraint rather than discard evidence.
