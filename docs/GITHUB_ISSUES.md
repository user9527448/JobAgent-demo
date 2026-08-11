# JOBAGENT V1.0 — GitHub Issues Backlog

本文件把 10 周计划拆成可执行 Issues。编号是规划编号，不等同于 GitHub 自动生成的 Issue 编号。

## 1. 建议先创建的 Labels

### 类型

`type:feature`、`type:chore`、`type:test`、`type:docs`、`type:spike`、`type:bug`

### 模块

`area:infra`、`area:database`、`area:crawler`、`area:parser`、`area:extraction`、`area:matching`、`area:report`、`area:notification`、`area:api`、`area:ui`、`area:agent`

### 优先级与规模

`priority:P0`、`priority:P1`、`priority:P2`；`size:S`（≤0.5 天）、`size:M`（1–2 天）、`size:L`（3–4 天）。超过 L 的 Issue 必须继续拆分。

## 2. Milestones 与周映射

| Milestone | 周 | Issues |
|---|---|---|
| M1 Foundation | W1 | JAI-001 ～ JAI-005 |
| M2 Collection | W2–W3 | JAI-006 ～ JAI-012 |
| M3 Extraction | W4–W6 | JAI-013 ～ JAI-021 |
| M4 Intelligence | W7 | JAI-022 ～ JAI-025 |
| M5 MVP Release | W8 | JAI-026 ～ JAI-029 |
| M6 Agent | W9–W10 | JAI-030 ～ JAI-035 |

---

## M1 Foundation（第 1 周）

### JAI-001 初始化 Python 工程与开发规范

- **Labels**：`type:chore` `area:infra` `priority:P0` `size:M`
- **依赖**：无
- **目标**：建立可安装、可测试、可持续扩展的单体工程。
- **范围**：创建 `pyproject.toml`、应用目录、测试目录、格式化/静态检查配置、`.gitignore`、`.env.example` 和基础 README。
- **不包含**：业务模型、前端、Agent。
- **验收标准**：
  - [ ] 新环境可按 README 安装依赖并启动空应用。
  - [ ] 格式化、静态检查和测试命令可执行。
  - [ ] 仓库不包含密钥、缓存、数据库文件或下载附件。

### JAI-002 建立配置、结构化日志与统一异常

- **Labels**：`type:feature` `area:infra` `priority:P0` `size:M`
- **依赖**：JAI-001
- **目标**：所有模块使用一致配置、日志字段和错误分类。
- **范围**：环境配置、时区、日志级别、request/run/source 上下文、可重试/不可重试异常。
- **验收标准**：
  - [ ] 缺失必需配置时启动失败且提示明确。
  - [ ] 日志至少包含时间、级别、事件名和关联 ID。
  - [ ] 日志自动遮蔽常见密钥字段。

### JAI-003 搭建 FastAPI、PostgreSQL 与健康检查

- **Labels**：`type:feature` `area:infra` `area:api` `priority:P0` `size:M`
- **依赖**：JAI-001、JAI-002
- **目标**：使用 Docker Compose 一键启动 API 和数据库。
- **范围**：Compose、数据库连接池、`/health/live`、`/health/ready`。
- **验收标准**：
  - [ ] 一条命令可启动服务。
  - [ ] live 检查不依赖数据库；ready 检查验证数据库连接。
  - [ ] 数据库不可用时 ready 返回非成功状态并有日志。

### JAI-004 建立测试与 CI 基线

- **Labels**：`type:test` `area:infra` `priority:P0` `size:M`
- **依赖**：JAI-001、JAI-003
- **目标**：每次变更自动执行质量检查。
- **范围**：pytest、测试数据库策略、lint/type-check/test 工作流。
- **验收标准**：
  - [ ] 本地与 CI 使用相同检查命令。
  - [ ] 测试相互隔离且可重复运行。
  - [ ] 示例失败测试会阻止检查通过。

### JAI-005 完成首个真实来源纵向 Spike

- **Labels**：`type:spike` `area:crawler` `area:parser` `priority:P0` `size:L`
- **依赖**：JAI-003
- **目标**：验证真实公告网页、附件下载和 PDF 文本提取链路。
- **范围**：选一个公开静态来源；记录入口、页面结构、频率限制；保存一个列表页、详情页和 PDF 样本。
- **交付**：技术验证记录、固定样本、已知限制与来源接入建议。
- **验收标准**：
  - [ ] 能从列表发现详情链接并提取标题、发布时间、正文。
  - [ ] 能发现、下载并提取一个 PDF 的页级文本。
  - [ ] 记录访问策略和合规检查结果。

---

## M2 Collection（第 2–3 周）

### JAI-006 实现核心数据库模型与首版迁移

- **Labels**：`type:feature` `area:database` `priority:P0` `size:L`
- **依赖**：JAI-003
- **目标**：持久化来源、运行、原文、附件和结构化岗位。
- **范围**：`sources`、`crawl_runs`、`raw_documents`、`attachments`、`job_posts`、`job_positions`、`field_evidence` 及索引/约束。
- **验收标准**：
  - [ ] 空数据库可升级到最新版本。
  - [ ] 唯一约束阻止同来源同 canonical URL 重复。
  - [ ] 时间以 UTC 保存；历史数据不因停用来源而删除。
  - [ ] 模型关系和字段说明写入文档。

### JAI-007 实现 Source Adapter 协议与采集编排器

- **Labels**：`type:feature` `area:crawler` `priority:P0` `size:L`
- **依赖**：JAI-002、JAI-006
- **目标**：新增来源只实现发现和详情解析，不复制公共流程。
- **范围**：Adapter 注册表、discover/fetch 协议、批处理、步骤状态与单条错误隔离。
- **验收标准**：
  - [ ] 假 Adapter 可完整运行并生成运行统计。
  - [ ] 单条详情失败不会中止其他条目。
  - [ ] 未注册 Adapter 在运行前给出明确错误。

### JAI-008 实现 HTTP 客户端、限速、重试与缓存头

- **Labels**：`type:feature` `area:crawler` `priority:P0` `size:M`
- **依赖**：JAI-002
- **目标**：以可控、礼貌且可观测的方式访问来源。
- **范围**：超时、来源级并发/频率、指数退避、User-Agent、ETag/Last-Modified 支持。
- **验收标准**：
  - [ ] 429/5xx 按策略重试并记录次数。
  - [ ] 4xx 非临时错误不无限重试。
  - [ ] 每个来源可独立配置限速和超时。

### JAI-009 实现 URL 规范化、内容指纹和幂等写入

- **Labels**：`type:feature` `area:crawler` `area:database` `priority:P0` `size:M`
- **依赖**：JAI-006、JAI-007
- **目标**：重复运行不产生重复公告，同时能识别内容更新。
- **范围**：去跟踪参数、相对链接解析、canonical URL、正文规范化、SHA-256、更新策略。
- **验收标准**：
  - [ ] 同样输入运行两次只保留一条当前公告记录。
  - [ ] 页面内容变化可生成新版本或更新事件，不丢失原证据。
  - [ ] 对关键边界情况有单元测试。

### JAI-010 实现附件发现、下载与文件存储

- **Labels**：`type:feature` `area:crawler` `priority:P0` `size:M`
- **依赖**：JAI-006、JAI-008、JAI-009
- **目标**：可靠保存公告附件并避免重复下载。
- **范围**：PDF/XLS/XLSX 链接发现、MIME/扩展名校验、大小限制、SHA-256、原子写入。
- **验收标准**：
  - [ ] 同一附件重复发现不会重复存储。
  - [ ] HTML 错误页伪装成附件时被拒绝并记录。
  - [ ] 下载中断不留下被标记为成功的半文件。

### JAI-011 接入来源 1、2、3 并建立契约样本

- **Labels**：`type:feature` `area:crawler` `priority:P0` `size:L`
- **依赖**：JAI-005、JAI-007～JAI-010
- **目标**：以可人工维护的官方目标网站库覆盖至少三种有代表性的公开页面结构。
- **范围**：先维护校招、江浙沪公职考试和央国企招聘官方来源清单、接入状态与来源级包含/排除关键词；每个来源单独子任务/提交；保存脱敏 HTML/JSON 样本与期望输出。首个 Adapter 选择国务院国资委公开招聘栏目，报名系统和未验证动态门户保持停用。
- **验收标准**：
  - [x] `config/source_catalog.toml` 可手工增删、启停来源和维护关键词，非法/重复配置会明确失败。
  - [x] 网站库覆盖校招、江苏/浙江/上海公职考试和央国企招聘，候选来源均记录官方入口与接入状态。
  - [x] 每个来源可发现并保存新增公告；存在 JAI-010 支持格式附件时可持久化并复用，Firstjob 海报图片仅保留来源 URL。
  - [x] 每个来源至少 3 组固定样本通过契约测试。
  - [x] 连续运行两次无重复数据。

### JAI-012 实现运行统计、手动触发与失败重跑

- **Labels**：`type:feature` `area:crawler` `area:api` `priority:P1` `size:M`
- **依赖**：JAI-007、JAI-011
- **目标**：开发者能看懂一次任务发生了什么，并只重跑失败部分。
- **范围**：命令/API、运行状态、发现/新增/更新/跳过/失败计数、错误分类。
- **验收标准**：
  - [ ] 可按 source 手动运行并获取 run ID。
  - [ ] 可查看运行摘要和失败条目。
  - [ ] 重跑不会重复成功数据。

---

## M3 Extraction（第 4–6 周）

### JAI-013 定义解析器协议与标准中间格式

- **Labels**：`type:feature` `area:parser` `priority:P0` `size:M`
- **依赖**：JAI-006、JAI-010
- **目标**：HTML、PDF、Excel 使用统一、可追溯的解析输出。
- **范围**：parser registry、文档块/表格/证据位置 Schema、状态和错误码。
- **验收标准**：
  - [ ] 可按 MIME 类型选择解析器。
  - [ ] 每个输出块保留来源文件和页/行/单元格位置。
  - [ ] 不支持的文件进入明确状态而非静默跳过。

### JAI-014 实现 PDF 文本解析与扫描件识别

- **Labels**：`type:feature` `area:parser` `priority:P0` `size:M`
- **依赖**：JAI-013
- **目标**：提取文本型 PDF，并识别无法直接解析的文件。
- **范围**：页级文本、元数据、加密/损坏错误、文本密度判断；V1 不含 OCR 实现。
- **验收标准**：
  - [ ] 正常 PDF 输出页级文本和页码。
  - [ ] 扫描件标记 `ocr_required`。
  - [ ] 加密/损坏文件有可诊断错误。

### JAI-015 实现 Excel 岗位表解析

- **Labels**：`type:feature` `area:parser` `priority:P0` `size:L`
- **依赖**：JAI-013
- **目标**：将常见岗位表转换为保留证据位置的标准表格。
- **范围**：多 Sheet、标题行识别、空行、合并单元格、XLSX；XLS 支持视依赖可行性确定。
- **验收标准**：
  - [ ] 黄金样本中表头和数据区识别正确率达到约定目标。
  - [ ] 每个字段可定位到工作表和单元格/行。
  - [ ] 无法识别表头时进入待复核状态。

### JAI-016 建立附件黄金样本与回归测试

- **Labels**：`type:test` `area:parser` `priority:P0` `size:M`
- **依赖**：JAI-014、JAI-015
- **目标**：防止解析器修改破坏既有格式。
- **范围**：至少 10 份脱敏 PDF/Excel 样本、期望中间结果、批量评估脚本。
- **验收标准**：
  - [ ] 样本覆盖多页、合并单元格、空行和多种日期格式。
  - [ ] CI 可离线运行完整回归。
  - [ ] 输出解析成功率和差异明细。

### JAI-017 实现确定性字段抽取与规范化

- **Labels**：`type:feature` `area:extraction` `priority:P0` `size:L`
- **依赖**：JAI-013
- **目标**：用规则可靠抽取日期、地区、单位、报名链接等字段。
- **范围**：日期范围/时区、地区字典、URL、人数、学历和枚举规范化。
- **验收标准**：
  - [ ] 日期解析覆盖黄金样本格式，开始时间不得晚于截止时间。
  - [ ] 原值与规范化值同时保留。
  - [ ] 无证据的关键字段不填充猜测值。

### JAI-018 实现可替换 LLM 抽取服务

- **Labels**：`type:feature` `area:extraction` `priority:P0` `size:L`
- **依赖**：JAI-002、JAI-017
- **目标**：对不规则公告补充结构化抽取，同时控制成本和幻觉。
- **范围**：provider 接口、严格 JSON Schema、Prompt 版本、超时/重试、token/成本统计、mock。
- **验收标准**：
  - [ ] provider 可通过配置替换。
  - [ ] 非法输出不会直接入业务表。
  - [ ] 每次调用记录模型、Prompt 版本、token 和结果状态。
  - [ ] 单日预算达到阈值后停止新调用并进入待处理队列。

### JAI-019 合并正文与附件结果并保存字段证据

- **Labels**：`type:feature` `area:extraction` `area:database` `priority:P0` `size:L`
- **依赖**：JAI-014、JAI-015、JAI-017、JAI-018
- **目标**：生成公告和岗位实体，并解释每个关键字段来自哪里。
- **范围**：优先级规则、冲突标记、置信度、抽取版本、`field_evidence`。
- **验收标准**：
  - [ ] 每个关键字段带来源类型和证据位置。
  - [ ] 正文与附件冲突不会被静默覆盖。
  - [ ] 重新抽取可保留历史版本并生成一致结果。

### JAI-020 实现数据校验、待复核与重新解析

- **Labels**：`type:feature` `area:extraction` `priority:P0` `size:M`
- **依赖**：JAI-019
- **目标**：坏数据不会无提示进入推荐流程。
- **范围**：必填、时间逻辑、链接、枚举、冲突校验；复核状态与重解析命令/API。
- **验收标准**：
  - [ ] 校验失败记录原因和严重度。
  - [ ] 严重错误不参与自动推荐。
  - [ ] 修正规则后可对指定文档重解析且保持幂等。

### JAI-021 接入来源 4、5 并完成三日稳定性验证

- **Labels**：`type:feature` `area:crawler` `area:extraction` `priority:P0` `size:L`
- **依赖**：JAI-011、JAI-020
- **目标**：达到 MVP 来源覆盖和质量指标。
- **验收标准**：
  - [ ] 5 个来源均有 Adapter 契约测试。
  - [ ] 连续 3 天运行并记录成功率、重复率、字段完整率。
  - [ ] 核心字段完整率 ≥ 85%，或对差距形成明确整改 Issue。

---

## M4 Intelligence（第 7 周）

### JAI-022 实现单用户偏好模型与配置 API

- **Labels**：`type:feature` `area:matching` `area:api` `priority:P0` `size:M`
- **依赖**：JAI-006
- **目标**：以结构化方式保存个人筛选与偏好。
- **范围**：地区、学历、专业、岗位关键词、单位类型、排除词；读取/更新 API。
- **验收标准**：
  - [ ] 输入经过 Schema 和枚举校验。
  - [ ] 配置变更有更新时间并可触发重算。
  - [ ] 默认配置不会意外过滤全部岗位。

### JAI-023 实现硬过滤和版本化规则评分

- **Labels**：`type:feature` `area:matching` `priority:P0` `size:L`
- **依赖**：JAI-020、JAI-022
- **目标**：得到稳定、可解释、可复算的推荐排序。
- **范围**：学历/截止/排除词硬过滤，地区/方向/专业/单位/紧迫度/完整度分项评分。
- **验收标准**：
  - [ ] 同样输入和评分版本得到同样结果。
  - [ ] 每个分项保存规则、输入、得分和解释。
  - [ ] 修改偏好后可全量重算。
  - [ ] 边界规则有单元测试。

### JAI-024 实现日报查询与 Markdown/HTML 渲染

- **Labels**：`type:feature` `area:report` `priority:P0` `size:L`
- **依赖**：JAI-023
- **目标**：生成可直接阅读和推送的行动型日报。
- **范围**：优先投递、即将截止、今日新增、需要确认四组；模板、快照、原文链接。
- **验收标准**：
  - [ ] 每条包含单位、标题、地区、截止、理由、风险和链接。
  - [ ] 同一天相同输入可得到稳定排序。
  - [ ] 无岗位时仍生成明确的空日报。

### JAI-025 使用历史样本评审 Top 20 推荐质量

- **Labels**：`type:test` `area:matching` `priority:P1` `size:M`
- **依赖**：JAI-023、JAI-024
- **目标**：用人工判断校正权重，而不是凭感觉上线。
- **范围**：建立至少 50 条带人工相关性标注的岗位集，评审 Top 20 和漏召回。
- **验收标准**：
  - [ ] 记录明显误推荐、漏推荐和原因分类。
  - [ ] 权重调整有前后对比且更新评分版本。
  - [ ] 形成 MVP 推荐局限说明。

---

## M5 MVP Release（第 8 周）

### JAI-026 实现每日调度、并发锁和任务恢复

- **Labels**：`type:feature` `area:infra` `priority:P0` `size:L`
- **依赖**：JAI-012、JAI-024
- **目标**：系统每天无人值守执行完整流水线。
- **范围**：APScheduler、Asia/Shanghai 调度、单实例锁、misfire、阶段重试和手动补跑。
- **验收标准**：
  - [ ] 同一计划时刻不会并发执行两个相同任务。
  - [ ] 进程重启后可识别未完成运行并安全恢复/终止。
  - [ ] 每次计划运行可追踪到采集、解析、评分和日报记录。

### JAI-027 接入微信推送并实现幂等与重试

- **Labels**：`type:feature` `area:notification` `priority:P0` `size:M`
- **依赖**：JAI-024
- **目标**：通过一个选定通道可靠推送日报。
- **范围**：PushPlus 或企业微信机器人（二选一）、消息长度处理、重试、发送记录和密钥配置。
- **验收标准**：
  - [ ] 同一日报同一通道成功发送后不会重复发送。
  - [ ] 临时失败按上限重试，永久失败可查看原因。
  - [ ] 日志和数据库不泄露 Token。

### JAI-028 完成端到端测试与五次无人值守试运行

- **Labels**：`type:test` `area:infra` `priority:P0` `size:L`
- **依赖**：JAI-026、JAI-027
- **目标**：证明 MVP 闭环在真实调度下稳定工作。
- **范围**：离线 E2E、线上受控试运行、指标统计和问题清单。
- **验收标准**：
  - [ ] 离线样本完成采集到日报全链路。
  - [ ] 连续 5 次自动运行成功，无重复公告和重复推送。
  - [ ] 记录来源可用率、字段完整率、解析成功率和总耗时。

### JAI-029 编写运行手册并发布 v0.1.0-mvp

- **Labels**：`type:docs` `area:infra` `priority:P0` `size:M`
- **依赖**：JAI-028
- **目标**：开发者一个月后仍能安装、运行、排错和恢复系统。
- **范围**：安装、配置、添加来源、手动补跑、常见故障、备份恢复、升级与回滚说明；发布清单。
- **验收标准**：
  - [ ] 在干净环境按文档可启动并生成示例日报。
  - [ ] PostgreSQL 备份和恢复演练成功。
  - [ ] 创建 `v0.1.0-mvp` 标签/Release，并列出已知限制。

---

## M6 Agent（第 9–10 周）

### JAI-030 实现来源、偏好、运行历史与失败详情 API

- **Labels**：`type:feature` `area:api` `priority:P1` `size:L`
- **依赖**：JAI-012、JAI-022、JAI-029
- **目标**：日常维护无需直接操作数据库。
- **范围**：来源启停、偏好编辑、运行列表/详情、失败项、重跑；本地单用户访问边界。
- **验收标准**：
  - [ ] 所有写操作有输入校验和审计记录。
  - [ ] 停用来源不会删除历史数据。
  - [ ] 重跑接口具备幂等保护。

### JAI-031 实现最小配置与状态页面

- **Labels**：`type:feature` `area:ui` `priority:P1` `size:L`
- **依赖**：JAI-030
- **目标**：在一个简单页面完成高频维护动作。
- **范围**：来源状态/启停、用户偏好、最近运行、失败详情、今日日报链接。
- **不包含**：登录、多用户、通用 CRUD 管理后台和复杂设计系统。
- **验收标准**：
  - [ ] 常用桌面浏览器下可完成全部范围内操作。
  - [ ] 危险或重复操作有确认/禁用状态。
  - [ ] API 错误对用户显示可理解反馈。

### JAI-032 实现稳定的岗位查询与解释服务层

- **Labels**：`type:feature` `area:api` `area:matching` `priority:P0` `size:L`
- **依赖**：JAI-023、JAI-030
- **目标**：Agent 和 UI 复用相同业务服务，不让 Agent 直接查写数据库。
- **范围**：搜索岗位、岗位详情、评分解释、生成/读取日报、受控触发来源采集。
- **验收标准**：
  - [ ] 服务输入输出使用明确 Schema。
  - [ ] 查询支持地区、单位类型、关键词、截止状态和最低分。
  - [ ] 解释与已保存的评分分项一致。

### JAI-033 封装 Agent Tools 与安全边界

- **Labels**：`type:feature` `area:agent` `priority:P0` `size:L`
- **依赖**：JAI-032
- **目标**：提供最小、受控、可审计的工具集合。
- **范围**：`search_jobs`、`get_job_detail`、`explain_match`、`generate_report`、`run_crawl`；参数 Schema、超时、最大结果数、审计。
- **验收标准**：
  - [ ] Agent 无法执行任意 SQL、代码或未注册工具。
  - [ ] 写/运行类工具有确认策略和幂等键。
  - [ ] 每次工具调用记录名称、参数摘要、结果和耗时。

### JAI-034 实现单 Agent 编排与任务评测集

- **Labels**：`type:feature` `type:test` `area:agent` `priority:P1` `size:L`
- **依赖**：JAI-033
- **目标**：自然语言稳定完成查询、解释和受控操作。
- **范围**：系统指令、工具选择、最大步数、失败降级；至少 30 条任务评测集。
- **验收标准**：
  - [ ] 查询/解释类任务不会触发写操作。
  - [ ] 模糊的运行类请求在执行前要求确认。
  - [ ] 评测集任务成功率 ≥ 90%，失败有分类。

### JAI-035 稳定性收尾并发布 v0.2.0-agent

- **Labels**：`type:chore` `area:agent` `priority:P1` `size:M`
- **依赖**：JAI-031、JAI-034
- **目标**：完成 Agent 版本发布和文档收尾。
- **范围**：回归、性能与成本检查、已知限制、升级说明、演示脚本。
- **验收标准**：
  - [ ] MVP 全链路回归不因 Agent 接入而退化。
  - [ ] 关键 Agent 任务有可复现演示。
  - [ ] 发布 `v0.2.0-agent` 并记录升级和回滚步骤。

---

## 横向文档维护

### JAI-036 建立简体中文文档镜像与同步规范

- **Labels**：`type:docs` `area:infra` `priority:P1` `size:M`
- **依赖**：JAI-010（以当前已完成版本作为中文文档基线）
- **目标**：为纯英文技术文档提供可导航的简体中文版本，并使后续中英文更新保持同步。
- **范围**：`docs/zh-CN/` 中文索引与镜像、仓库文档同步约定、README 导航、当前英文技术文档翻译；现有中文文档继续作为单一版本维护。
- **不包含**：逐字回译历史 WORKLOG、翻译代码标识符或第三方原始材料、引入自动机器翻译服务。
- **验收标准**：
  - [ ] 每份当前纯英文技术文档都有明确的简体中文镜像或中文入口。
  - [ ] 中文索引能从根 README 到达，并能反向定位英文原文。
  - [ ] `AGENTS.md` 要求后续修改英文技术文档时同步更新其中文镜像。
  - [ ] WORKLOG 从本 Issue 起使用中文记录新增工作，历史记录保持不变。

---

## 3. MVP 后 Backlog（默认不进入十周承诺）

### JAI-B01 增加扫描 PDF OCR

- `priority:P2`；仅当高价值来源中扫描 PDF 占比显著且人工处理成为瓶颈时启动。

### JAI-B02 增加 pgvector 语义召回

- `priority:P2`；先建立带人工标注的基准集，证明相对规则召回有增益后再实施。

### JAI-B03 增加 LLM rerank

- `priority:P2`；只对规则/向量 Top N 使用，并设置成本上限与离线评测。

### JAI-B04 增加 Playwright 动态来源

- `priority:P2`；仅为高价值且无稳定公开接口的来源引入，独立运行以隔离资源消耗。

### JAI-B05 增加第二推送通道

- `priority:P2`；当现有通道长期不可用或确有多端需求时再做。

## 4. 推荐执行顺序

每周只把对应 Milestone 中的 P0 拉入进行中，个人 WIP 上限为 2：最多一个主要功能 Issue 加一个小型测试/文档 Issue。出现阻塞时先拆 Issue 或切换到同一里程碑内无依赖任务，不提前启动 Agent 和增强项。
