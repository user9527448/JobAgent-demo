# 来源 HTTP 客户端策略

> 英文原文：[Source HTTP client policy](../HTTP_CLIENT.md)。修改原文时必须在同一提交中同步更新本镜像。

JAI-008 提供来源 Adapter 共用的异步 HTTP 行为。Adapter 仍负责来源专用 URL 和解析，但不自行实现重试、请求节奏或缓存请求头循环。

## 来源级策略

每个来源客户端使用独立的 `HttpSourcePolicy`：

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

- `timeout_seconds` 适用于连接、读取、写入和连接池等待。
- `min_interval_seconds` 控制该来源各次请求开始时间的最小间隔。
- `max_concurrency` 限制该来源的进行中请求数。
- 重试延迟为 `min(base * 2^(attempt-1), maximum)`。
- User-Agent 必须非空且能说明用途。

客户端实例不共享信号量或限速时钟，因此慢来源不会暗中把自己的策略施加给其他来源。

## 重试分类

| 结果 | 行为 |
|---|---|
| HTTP 2xx | 立即返回 |
| HTTP 304 | 返回 `not_modified=true` |
| HTTP 429 | 重试到 `max_attempts` |
| HTTP 5xx | 重试到 `max_attempts` |
| HTTP 传输错误 | 重试到 `max_attempts` |
| 其他 HTTP 4xx/3xx | 立即作为永久失败 |

临时错误重试耗尽后抛出 `crawler.http_retry_exhausted`，包含尝试次数和安全的状态/错误类型。不可重试响应在一次尝试后抛出 `crawler.http_permanent_response`。

日志包含来源 ID、清理后的 URL、尝试次数、状态和重试延迟。查询字符串、片段、URL 凭据和响应正文不会进入日志。

## 条件缓存请求头

成功响应通过 `HttpCacheValidators` 暴露 `ETag` 和 `Last-Modified`。把这些校验值传给下一次 GET，会发送 `If-None-Match` 和 `If-Modified-Since`。304 响应会保留服务器未再次返回的校验值。

```python
async with SourceHttpClient(policy) as client:
    first = await client.get(url)
    later = await client.get(url, validators=first.validators)
    if later.not_modified:
        # 复用之前保留的来源内容。
        ...
```

JAI-009 通过[原始公告仓库](RAW_DOCUMENTS.md)持久化这些校验值，并按规范 URL 为后续条件请求重新加载。

对于有大小上限的下载，`SourceHttpClient.stream()` 会在完整消费上下文期间保留同一信号量、节奏、重试和安全错误行为，同时向调用方暴露成功响应正文。JAI-010 用它完成[附件 MIME/签名校验、大小限制和原子存储](ATTACHMENTS.md)；响应正文中断会记录为可重试的附件失败，不能发布部分对象。
