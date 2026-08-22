# Replaceable LLM Extraction Service

> Simplified Chinese mirror: [`zh-CN/LLM_EXTRACTION.md`](zh-CN/LLM_EXTRACTION.md).

JAI-018 adds an optional in-memory LLM extraction boundary for irregular announcements. It consumes bounded parser fragments and emits only validated candidates for later reconciliation. It never writes `job_posts`, `job_positions`, or `field_evidence` rows.

## Provider and configuration boundary

`LlmProvider` is the provider-neutral async protocol. `LlmProviderConfig` selects a registered implementation, while `build_llm_provider()` accepts deployment-specific factories so a provider can be replaced without changing extraction orchestration. The built-in `OpenAIResponsesProvider` uses the existing `httpx` dependency and an HTTPS Responses API endpoint; the API key is held as `SecretStr` and never appears in errors or call records.

`LlmServicePolicy` configures the model, Prompt version, maximum attempts, retry delay, input/output token ceilings, deployment-supplied token prices, daily USD budget, and budget timezone. Model names and prices are not hard-coded because they are deployment decisions that change independently from this repository.

Tests use scripted providers and `httpx.MockTransport`; no live provider request or credential is required by the quality gate.

## Strict output and evidence validation

Every request carries the JSON Schema generated from `LlmExtractionPayload`. The schema forbids extra properties at both payload and candidate levels. Each candidate contains only:

- a supported `FieldName`;
- non-empty `raw_value` and `normalized_value`;
- a non-empty `evidence_quote`.

After provider response parsing, Pydantic performs strict JSON validation. The service then requires `raw_value` to occur inside `evidence_quote` and the entire quote to occur verbatim in one supplied parser fragment. Invalid JSON, unknown properties, wrong types, invented quotes, and unsupported raw values produce `invalid_output` with no payload. An empty candidate list is valid and preferable to guessing.

The Prompt treats announcement content as untrusted data, forbids following source instructions, and requires omission when direct evidence is unavailable. Prompt text and `DEFAULT_PROMPT_VERSION` are explicit and every call record retains the configured version.

## Responses adapter and retry policy

The built-in adapter sends `model`, `instructions`, `input`, `max_output_tokens`, and a strict `text.format` JSON Schema to `POST /responses`. It accepts either a direct `output_text` field or text nested in the response output items, and requires non-negative `input_tokens`, `output_tokens`, and `total_tokens` usage.

Timeouts, transport failures, HTTP 408/409/429, and server errors are retryable. Other HTTP failures and malformed successful responses are permanent. `LlmExtractionService` applies bounded exponential backoff and records the final logical status without exposing provider response bodies.

## Call records, cost, and budget queue

Every logical request produces one `LlmCallRecord` containing task ID, provider, model, Prompt version, result status, attempt count, token use, deployment-priced estimated cost, timestamps, and a safe error code. The statuses are `completed`, `invalid_output`, `provider_error`, and `queued_budget`. `invalid_output` retains usage and cost but never exposes candidates.

`DailyLlmBudget` makes a concurrency-safe pessimistic reservation using configured maximum input/output tokens before a provider call. A zero budget disables new calls. If spent plus reserved maximum cost would cross the daily threshold, the provider is not invoked, the request is sent to `LlmPendingQueue`, and a zero-token `queued_budget` record is emitted. Successful HTTP responses charge provider-reported usage even when their structured output is invalid; failed attempts without reported usage release the reservation.

`InMemoryLlmCallRecorder` and `InMemoryLlmPendingQueue` provide the JAI-018 process-local defaults. Their protocols allow later worker infrastructure to supply durable implementations without changing this service.

## Issue boundaries

- JAI-018 returns isolated candidate payloads; it does not merge deterministic, body, or attachment results, choose precedence, resolve conflicts, or produce business entities.
- No database migration or `field_evidence` persistence is added. Those responsibilities remain JAI-019.
- The in-memory recorder and queue are not presented as durable delivery. Later orchestration may implement their protocols after the corresponding persistence/worker Issue authorizes it.
- OCR remains deferred to JAI-B01, and provider extraction never bypasses source login, CAPTCHA, access control, anti-bot, or platform restrictions.
