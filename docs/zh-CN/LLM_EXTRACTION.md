# 可替换 LLM 抽取服务

> English mirror: [`../LLM_EXTRACTION.md`](../LLM_EXTRACTION.md)。

JAI-018 为不规则公告新增可选的纯内存 LLM 抽取边界。它接收有界解析器片段，只输出供后续协调的已校验候选结果，绝不写入 `job_posts`、`job_positions` 或 `field_evidence` 行。

## Provider 与配置边界

`LlmProvider` 是与供应商无关的异步协议。`LlmProviderConfig` 选择已注册实现，`build_llm_provider()` 接受部署侧工厂，因此替换 provider 不需要修改抽取编排。内置 `OpenAIResponsesProvider` 复用现有 `httpx` 依赖和 HTTPS Responses API 端点；API key 使用 `SecretStr` 保存，不会出现在错误或调用记录中。

`LlmServicePolicy` 配置模型、Prompt 版本、最大尝试次数、重试延迟、输入/输出 token 上限、部署侧提供的 token 单价、单日美元预算和预算时区。模型名称与价格不硬编码，因为它们属于独立于仓库变化的部署决策。

测试使用脚本化 provider 与 `httpx.MockTransport`；质量门禁不需要真实 provider 请求或凭据。

## 严格输出与证据校验

每个请求都携带由 `LlmExtractionPayload` 生成的 JSON Schema。Schema 在 payload 与 candidate 两层都禁止额外属性。每个候选仅包含：

- 一个受支持的 `FieldName`；
- 非空 `raw_value` 与 `normalized_value`；
- 非空 `evidence_quote`。

provider 响应解析后，Pydantic 先执行严格 JSON 校验。服务随后要求 `raw_value` 出现在 `evidence_quote` 内，并要求完整引文逐字出现在某个已提供的解析器片段中。非法 JSON、未知属性、错误类型、虚构引文和没有原文支持的值都会产生不带 payload 的 `invalid_output`。空候选列表是合法结果，优先于猜测填充。

Prompt 把公告内容视为不可信数据，禁止执行来源中的指令，并要求没有直接证据时省略字段。Prompt 文本与 `DEFAULT_PROMPT_VERSION` 均显式定义，每条调用记录都会保留配置版本。

## Responses 适配器与重试策略

内置适配器向 `POST /responses` 发送 `model`、`instructions`、`input`、`max_output_tokens` 和严格的 `text.format` JSON Schema。它既能接收直接的 `output_text`，也能读取 response output item 中嵌套的文本，并要求 `input_tokens`、`output_tokens` 与 `total_tokens` 均为非负值。

超时、传输错误、HTTP 408/409/429 和服务端错误可重试；其他 HTTP 失败及格式错误的成功响应属于永久失败。`LlmExtractionService` 执行有界指数退避，记录最终逻辑状态，但不暴露 provider 响应正文。

## 调用记录、成本与预算排队

每个逻辑请求都会生成一条 `LlmCallRecord`，包含 task ID、provider、模型、Prompt 版本、结果状态、尝试次数、token 用量、按部署价格计算的预估成本、时间戳和安全错误码。状态包括 `completed`、`invalid_output`、`provider_error` 和 `queued_budget`。`invalid_output` 保留用量与成本，但不会暴露候选结果。

`DailyLlmBudget` 在 provider 调用前使用配置的最大输入/输出 token 成本进行并发安全的保守预留。预算为零时禁用新调用。如果已消费成本加预留最大成本将跨过单日阈值，则不调用 provider，把请求交给 `LlmPendingQueue`，并生成零 token 的 `queued_budget` 记录。成功 HTTP 响应即使结构化输出非法，也按 provider 报告用量计费；没有报告用量的失败尝试会释放预留。

`InMemoryLlmCallRecorder` 与 `InMemoryLlmPendingQueue` 是 JAI-018 的进程内默认实现。它们的协议允许后续 worker 基础设施提供持久实现，而不需要修改本服务。

## Issue 边界

- JAI-018 只返回相互独立的候选 payload，不合并确定性/正文/附件结果，不选择优先级、不解决冲突，也不生成业务实体。
- 本 Issue 不新增数据库迁移或 `field_evidence` 持久化；这些职责仍属于 JAI-019。
- 进程内 recorder 与 queue 不被宣称为持久交付机制；只有对应持久化/worker Issue 授权后，后续编排才能实现其协议。
- OCR 继续延期至 JAI-B01；provider 抽取也绝不绕过来源登录、验证码、访问控制、反爬或平台限制。
