# Source Adapter and collection orchestration

> 简体中文：[Source Adapter 与采集编排](zh-CN/COLLECTION.md)

JAI-007 establishes the source plug-in boundary and the common batch flow. HTTP behavior is supplied separately by the JAI-008 [source HTTP client policy](HTTP_CLIENT.md), JAI-009 supplies [canonical raw-document persistence](RAW_DOCUMENTS.md), and JAI-010 adds downstream [attachment discovery and storage](ATTACHMENTS.md). JAI-012 connects manual runs to raw-document persistence, persisted summaries, and failed-item retries.

JAI-011 adds the manually maintained `config/source_catalog.toml`. The Chinese [target-source catalog and maintenance guide](SOURCE_CATALOG.md) records official campus, Jiangsu/Zhejiang/Shanghai public-exam, and central/state-owned enterprise sources. Only entries marked `active` and `enabled`, with an implemented explicit Adapter, are runnable.

Title filtering is source-level configuration: an item matching any `exclude_keywords` value is rejected first; otherwise it must match at least one `include_keywords` value when that list is present. Keywords affect discovery only and never alter retained source HTML.

## Adapter contract

Each source registers an explicit factory under the name stored in `sources.adapter`. A factory receives a `SourceDefinition` and returns an object implementing:

```python
class SourceAdapter(Protocol):
    async def discover(self, cursor: dict[str, JsonValue] | None) -> Sequence[DiscoveredItem]: ...

    async def fetch_detail(self, item: DiscoveredItem) -> RawDocumentInput: ...
```

- `discover` emits source URLs and small source-specific metadata only.
- `fetch_detail` returns the untouched HTML and/or text plus basic provenance fields.
- Adapters do not create `crawl_runs`, perform shared retries, persist raw documents or control the batch loop.
- Registration is explicit. There are no dynamic imports or arbitrary adapter names from configuration.

## Batch flow

```text
load enabled source
  -> resolve registered adapter
  -> create running crawl_run
  -> discover candidates
  -> fetch each detail with item-level error isolation
  -> persist progress after discovery and every item
  -> finish as succeeded / partial / failed
```

An unknown adapter, missing source or disabled source fails before a run is created. A discovery failure marks the run failed and is re-raised. A detail failure is converted into a safe structured failure, recorded in run statistics and does not stop later items.

Cancellation is not swallowed: the run is marked `cancelled`, then the cancellation is re-raised.

## Run statistics

`crawl_runs.stats` contains stable counters and step status:

```json
{
  "discovered": 3,
  "detail_succeeded": 2,
  "detail_failed": 1,
  "created": 1,
  "updated": 0,
  "skipped": 1,
  "failed": 1,
  "steps": {
    "discover": {"status": "succeeded", "count": 3, "total": 3},
    "fetch_detail": {"status": "partial", "succeeded": 2, "failed": 1},
    "persist": {"status": "succeeded", "created": 1, "updated": 0, "skipped": 1, "failed": 0}
  },
  "failures": [
    {
      "url": "https://example.invalid/jobs/2",
      "step": "fetch_detail",
      "code": "crawler.adapter_fetch_detail_failed",
      "message": "Adapter fetch_detail failed with RuntimeError.",
      "retryable": false
    }
  ]
}
```

Unexpected exception messages are not persisted because they may contain upstream response data or credentials. Domain errors retain their explicitly safe code, message and retryability.

`created`, `updated` and `skipped` are the idempotent outcomes returned by `SqlAlchemyRawDocumentRepository`; `failed` counts all failed retry filters, detail fetches and persistence attempts. `detail_failed` remains a detail-fetch-only counter so operators can distinguish upstream parsing failures from database failures.

## JAI-012 manual runs and failed-item retries

The JAI-012 command is synchronous: it returns after the run reaches a terminal state and prints a JSON summary containing the run ID, source ID, status, timestamps, counters and structured failures. It uses the normal configured database and the manually maintained catalog:

```powershell
.\.venv\Scripts\python.exe scripts/manage_crawl.py run --source-id 7
.\.venv\Scripts\python.exe scripts/manage_crawl.py run --source-id 7 --limit 10
.\.venv\Scripts\python.exe scripts/manage_crawl.py show --run-id 101
.\.venv\Scripts\python.exe scripts/manage_crawl.py retry --run-id 101
```

- `run` accepts only an enabled database source that exactly matches one runnable catalog entry and an explicitly wired Adapter. It discovers public items, fetches details, and saves each successful detail through the idempotent raw-document repository.
- `run --limit N` keeps discovery unchanged but fetches and persists only the first `N` items in stable source order. The run records both selected `discovered` and source `discovered_total`; the optional cap must be positive and never truncates failed-item retries.
- `show` performs no source-site request. It reads one persisted `crawl_runs` summary and exposes the structured `failures` list separately from the complete `stats` payload.
- `retry` requires a terminal run with failed item URLs. It repeats public list discovery to reconstruct source metadata, then filters the result to the prior failed URLs before detail fetches. Successful URLs from the prior run are never fetched again.
- Retry never accepts an arbitrary URL from the command line. A prior failed URL that is no longer rediscovered is recorded as `crawler.retry_item_not_discovered`; it is not fetched directly.
- Every retry creates a new run with `retry_of_run_id`, `retry_requested`, selected `discovered`, and pre-filter `discovered_total` statistics. An ambiguous prior database commit is safe because a repeated raw-document save becomes `skipped` instead of a duplicate.
- Discovery failures have no failed detail URL and therefore use a new manual `run`, not `retry`. Nonterminal or successful runs return explicit `crawler.run_not_terminal` or `crawler.run_has_no_failed_items` errors.

JAI-012 deliberately provides a command boundary only. Source/run maintenance APIs remain JAI-030 scope; scheduling and concurrency locks remain JAI-026.

## Downstream persistence boundary

A completed `CrawlBatchResult` carries successful `RawDocumentInput` objects. In JAI-012 manual execution, the orchestrator saves each successful detail through `SqlAlchemyRawDocumentRepository` before marking that item successful. The repository resolves canonical URLs, computes normalized-content SHA-256 values and atomically creates/reuses/versions immutable `raw_documents` rows without changing individual Adapters. HTTP cache validators are retained for later conditional requests.

Attachment discovery and file persistence do not occur inside the Adapter or batch loop. After a raw-document version is known, the JAI-010 attachment service discovers supported links from that version's HTML and atomically stores validated files against its document ID.

## JAI-011 sources

### Current source 1 replacement: China Mobile recruitment announcements

`ChinaMobileRecruitmentAdapter` reads the official login-free announcement page and the same-origin static list/detail JSON declared by that page through `SourceHttpClient`. Discovery accepts only strict official HTTPS URLs and numeric announcement IDs, applies catalog include/exclude terms, and materializes each selected detail through GET-only requests. The raw document preserves the displayed organization, title, publication time, visible body and attachment links together with their provenance.

The detail JSON also exposes an internal takedown field (`text5`/`downTime`). The public detail script does not render it, so the Adapter retains it only as source metadata and never labels it as an application deadline. A deadline is eligible only when visible announcement text supplies direct evidence. For an image-only body, the Adapter preserves the strictly validated same-origin image URL as evidence but does not download it or perform OCR. Contract tests use purely synthetic, minimized offline fixtures; `scripts/run_source_preview.py` provides a bounded, read-only live preview without database writes.

The historical `SasacRecruitmentAdapter` and synthetic fixtures remain for traceability, but the catalog marks the source `blocked` and disabled. The public URL was unreachable from both the project environment and the user's browser on 2026-08-26 and 2026-08-27; the alternate official mobile hostname presented an expired certificate. No TLS bypass, login, browser automation, or access-control workaround is used.

### Source 2: Jiangsu personnel exams

`JiangsuPersonnelExamAdapter` reads the Jiangsu Department of Human Resources and Social Security personnel-exam index, annual topic pages and public articles. Discovery accepts only same-origin HTTPS paths matching `/art/YYYY/M/D/art_<column>_<article>.html` or `/col/col<id>/index.html` (excluding the configured index itself), then applies catalog keywords and a publication-date cursor. Detail pages retain their complete HTML, readable text, publication date, region and official owner.

The source covers public civil-service, public-institution and graduate service-program notices and schedules. Registration, payment, login and result-query systems are outside the Adapter boundary; links mentioned in an announcement remain source evidence but are not followed by the Adapter. Four minimized offline detail fixtures cover annual topics, distinct title/date structures and attachment-bearing notices.

### Source 3: Shanghai Firstjob graduate fairs

`ShanghaiFirstjobAdapter` queries the Shanghai Student Affairs Center's public graduate job-fair list. The official single-page application exposes the list through a form-encoded POST whose semantics are read-only; the Adapter therefore uses the narrowly scoped shared `post_form_query()` policy and never calls account, resume, application or registration functions. Discovery applies catalog keywords and a start-date cursor, then creates a stable public evidence URL from each fair UUID.

The list record is already the complete public schedule record, so detail materialization does not issue a second request. It preserves the UUID, title, start/end dates and public poster URL as raw JSON text and provenance metadata. Three minimized offline contract fixtures cover distinct 2026 graduate-fair schedules; poster URLs remain provenance because their image format is outside the current attachment-storage boundary.

### Three-source persistence acceptance

The JAI-011 PostgreSQL acceptance runs three fixed documents from each active source through the raw-document repository twice. The first pass creates nine immutable version-1 rows; the second pass returns the same nine IDs as `unchanged`, without new rows or versions. A SASAC PDF and Jiangsu XLSX then pass through attachment discovery and atomic storage twice, producing `stored` followed by `reused` with one database row, object and download per URL.

Firstjob's public record exposes a poster image rather than a JAI-010-supported PDF/XLS/XLSX attachment. The adapter retains its validated official-domain URL as provenance but does not expand the current attachment-type boundary. This is treated as an explicit unsupported format, not as a missing or fabricated source attachment.

JAI-021 separately exercises three synthetic China Mobile announcements together with the six source-4/5 fixtures through two PostgreSQL persistence runs. The first run creates nine immutable version-1 rows; the second returns the same nine rows as `unchanged`, proving the replacement does not introduce duplicate versions.
