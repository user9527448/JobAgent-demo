# Source Adapter and collection orchestration

JAI-007 establishes the source plug-in boundary and the common batch flow. HTTP behavior is supplied separately by the JAI-008 [source HTTP client policy](HTTP_CLIENT.md), and JAI-009 supplies [canonical raw-document persistence](RAW_DOCUMENTS.md). Attachment storage remains JAI-010.

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
  "steps": {
    "discover": {"status": "succeeded", "count": 3},
    "fetch_detail": {"status": "partial", "succeeded": 2, "failed": 1}
  },
  "failures": [
    {
      "url": "https://example.invalid/jobs/2",
      "code": "crawler.adapter_fetch_detail_failed",
      "message": "Adapter fetch_detail failed with RuntimeError.",
      "retryable": false
    }
  ]
}
```

Unexpected exception messages are not persisted because they may contain upstream response data or credentials. Domain errors retain their explicitly safe code, message and retryability.

## Downstream persistence boundary

A completed `CrawlBatchResult` carries successful `RawDocumentInput` objects to `SqlAlchemyRawDocumentRepository`. The repository resolves canonical URLs, computes normalized-content SHA-256 values and atomically creates/reuses/versions immutable `raw_documents` rows without changing individual Adapters. HTTP cache validators are retained for later conditional requests.

Attachment discovery and file persistence do not occur at this boundary; JAI-010 adds those operations after a raw-document version is known.
