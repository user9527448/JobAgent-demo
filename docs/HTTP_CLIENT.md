# Source HTTP client policy

> 简体中文：[来源 HTTP 客户端策略](zh-CN/HTTP_CLIENT.md)

JAI-008 provides the shared asynchronous HTTP behavior used by source Adapters. Adapters remain responsible for source-specific URLs and parsing; they do not implement their own retry, pacing or cache-header loops.

`post_form_query()` extends the same controls to a verified public read-only endpoint whose HTTP contract happens to use form-encoded POST. It is intentionally not a general POST client: adapters must never use it for login, registration, application or other state changes. Read-only form queries receive the same pacing, retry classification and safe logging as GET requests, but do not use conditional cache validators.

## Per-source policy

Each source client is created with an independent `HttpSourcePolicy`:

```python
policy = HttpSourcePolicy(
    source_id=7,
    user_agent="JOBAGENT/0.1 (+https://example.invalid/contact)",
    timeout_seconds=20,
    min_interval_seconds=1,
    max_concurrency=1,
    max_attempts=3,
    backoff_base_seconds=0.5,
    backoff_max_seconds=8,
)
```

- `timeout_seconds` applies to connect, read, write and pool waits.
- `min_interval_seconds` spaces request start times for that source.
- `max_concurrency` caps in-flight requests for that source.
- Retry delay is `min(base * 2^(attempt-1), maximum)`.
- A descriptive, non-empty User-Agent is mandatory.

Client instances do not share semaphores or rate clocks, so a slow source cannot silently impose its policy on another source.

## Retry classification

| Result | Behavior |
|---|---|
| HTTP 2xx | Return immediately |
| HTTP 304 | Return `not_modified=true` |
| HTTP 429 | Retry to `max_attempts` |
| HTTP 5xx | Retry to `max_attempts` |
| HTTP transport error | Retry to `max_attempts` |
| Other HTTP 4xx/3xx | Fail immediately as permanent |

Exhausted temporary failures raise `crawler.http_retry_exhausted` with the attempt count and safe status/error type. Non-retryable responses raise `crawler.http_permanent_response` after one attempt.

Logs include source ID, sanitized URL, attempt, status and retry delay. Query strings, fragments, URL credentials and response bodies are not logged.

## Conditional cache headers

Successful responses expose `HttpCacheValidators` from `ETag` and `Last-Modified`. Passing those validators to the next GET sends `If-None-Match` and `If-Modified-Since`. A 304 response retains validators that the server omits.

```python
async with SourceHttpClient(policy) as client:
    first = await client.get(url)
    later = await client.get(url, validators=first.validators)
    if later.not_modified:
        # Reuse the previously retained source content.
        ...
```

JAI-009 persists these validators through the [raw-document repository](RAW_DOCUMENTS.md) and reloads them by canonical URL for later conditional requests.

For bounded downloads, `SourceHttpClient.stream()` exposes the successful response body while retaining the same semaphore, pacing, retry and safe-error behavior for the full consumer context. JAI-010 uses it for [attachment MIME/signature validation, size limits and atomic storage](ATTACHMENTS.md); an interrupted response body is recorded as a retryable attachment failure and cannot publish a partial object.
