# JOBAGENT 持续开发工作日志

> 语言：简体中文。英文镜像：[`../WORKLOG.md`](../WORKLOG.md)。
>
> 截至 JAI-046 的原中英文混合历史已逐字节保存在
> [`../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`](../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)，
> SHA-256 为 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`。
>
> 最后更新：2026-09-05
>
> 当前分支：`feature/jai-025-top-20-quality-review`

## 1. 当前状态

| Issue | 状态 | 分支 / 提交 | 说明 |
|---|---|---|---|
| JAI-001 至 JAI-010 | 完成，已合并到 `develop` | 见历史归档 | 工程基线、采集框架、原始公告版本化和附件存储 |
| JAI-036 | 完成，已合并到 `develop` | `develop` / `82adb73` | 首批简体中文镜像和双语导航 |
| JAI-011 | 完成，已合并到 `develop` | `develop` / `368c369` | 三个官方来源 Adapter、固定样本、持久化和幂等验收 |
| JAI-037 | 完成，已合并到 `develop` | `develop` / `c649862` | 官方来源扩展路线、外企候选和参考来源边界 |
| JAI-046 | 完成，已合并并推送到 `develop` | `develop` / `f07b6d5` | 独立双语文件规则和仓库级 Git 作者身份规则 |
| JAI-047 | 完成，已合并并推送到 `develop` | `develop` / `87cd753` | 存量迁移基线、独立双语工作日志和 JAI-048 清单 |
| JAI-012 | 已完成、合并并推送到 `develop` | `develop` / `70dd3b2` | 手动运行、持久化计数、运行摘要和只重跑失败 URL 的幂等验收已通过 |
| JAI-013 | 已完成、合并并推送到 `develop` | `develop` / `36d389f` | MIME 注册表、可追溯文本/表格 Schema、状态、错误码、测试和双语文档已验证 |
| JAI-014 | 已完成、合并并推送到 `develop` | `develop` / `8f21745` | 页级文本、元数据、确定性扫描判断、加密/损坏诊断、测试和双语文档已验证 |
| JAI-015 | 已完成、合并并推送到 `develop` | `develop` / `fca197d` | XLSX 多工作表/表头/数据解析、合并单元格证据、复核诊断、测试和双语文档已验证 |
| JAI-016 | 已完成、合并并推送到 `develop` | `develop` / `1dc7a10` | 10 份脱敏 PDF/XLSX 样本、已审查中间快照、离线评估、测试和双语文档已验证 |
| JAI-017 | 已完成、合并并推送到 `develop` | `develop` / `c7a2ebe` | 确定性日期/时区、地区、URL、人数、学历/类别、原值/规范值和解析器证据已验证 |
| JAI-018 | 已完成、合并并推送到 `develop` | `develop` / `c013544` | 可替换 provider、严格结构化输出、Prompt 版本、受限重试、用量/成本记录和单日预算排队已验证 |
| JAI-019 | 已完成、合并并推送到 `develop` | `develop` / `82797d1` | 确定性正文/附件优先级、显式冲突、抽取版本与持久字段证据已验证 |
| JAI-020 | 已完成、合并并推送到 `develop` | `develop` / `f56365f` | 校验严重度、复核/推荐资格和指定文档幂等重解析已验证 |
| JAI-021 | 已完成、合并并推送到 `develop` | `develop` / `8cc0b2e` | Day 3 按已记录的外部入口豁免接受；实际 4/5 结果保留；合并后 PostgreSQL 门禁通过 |
| JAI-022 | 已完成、合并并推送到 `develop` | `develop` / `e7948c9` | 已保留 JAI-021/JAI-022 双方历史；合并后 PostgreSQL 门禁以 254 项测试通过 |
| JAI-023 | 已完成、合并并推送到 `develop` | `develop` / `5935b52` | 已保留 JAI-021 至 JAI-023 全部历史；合并后 PostgreSQL 门禁以 271 项测试通过 |
| JAI-024 | 已完成、合并并普通推送到 `develop` | `develop` / `0aa6b23` | 合并后 PostgreSQL 门禁以 282 项测试、87.96% 覆盖率通过 |
| JAI-025 | 进行中；实现门禁通过，等待负责人决策 | `feature/jai-025-top-20-quality-review` / `4fe0274` | 本地不存在历史记录；合成拟议标注未被描述为历史人工标注 |

## 2. 当前决策

### D-015 双语文档必须使用独立文件

英文和简体中文文档分别维护。既有文档保留原有主要语言，通过新增缺失版本补齐配对；两种语言在同一提交中更新。

### D-016 把混合语言 WORKLOG 原样保存为历史归档

原 `docs/WORKLOG.md` 同时包含英文和中文历史。JAI-047 把其原始字节保存在 `docs/archive/`，并新建英文与简体中文活动日志。历史归档仅作证据，不再追加记录。

### D-017 按独立 Issue 分批迁移存量文档

JAI-047 只处理使新规则可执行所必需的计划/Backlog 镜像、双语索引和 WORKLOG 拆分。其余存量单语文档由 JAI-048 盘点并迁移，不在功能 Issue 中顺手大规模改写。

### D-018 JAI-012 提供命令边界，不提前建设维护 API

JAI-012 通过可复用的编排器与仓储契约提供 `scripts/manage_crawl.py run/show/retry`。来源/运行维护 API 仍属于 JAI-030，调度与锁仍属于 JAI-026，避免当前 Issue 提前重叠后续范围。

### D-019 失败条目重跑采用重新发现后过滤

重跑会再次执行来源公开列表发现以恢复来源专用元数据，再只抓取原运行结构化失败中保存的 URL。命令不接受任意重跑 URL，不直接访问已经无法重新发现的条目，也不重新抓取原运行中的成功 URL。

### D-020 手动采集在计为成功前先完成原文持久化

手动运行把每个已抓取详情交给 `SqlAlchemyRawDocumentRepository`。运行统计记录 `created`、`updated`、`skipped` 和全部失败，同时保留只统计详情阶段的失败计数。重复执行结果不确定或已经成功的写入会返回 `skipped`，保持原始公告幂等。

### D-021 先把解析输出定义为严格内存契约，再由后续 Issue 编排持久化

JAI-013 定义不可变的 `ParseSource`、定位、块、Issue 和结果契约，以及显式 MIME 注册。本 Issue 不新增中间块数据表、附件解析 worker、PDF/Excel 实现或字段抽取。后续 Issue 可把完成结果的状态和安全诊断映射到现有附件字段。

### D-022 每个中间块都必须携带证据坐标

文本块和表格块保留持久化来源引用，以及从 1 开始的页码、包含端点的行范围或工作表/A1 单元格范围。表格单元格携带自身定位；表格/结果构造都会在下游抽取消费前拒绝混合来源输出。

### D-023 PDF 扫描判断使用可配置的确定性文本阈值

`PdfTextPolicy` 默认按整个文档计算每页平均 40 个非空白字符。低于阈值时返回 `ocr_required`，同时保留已经提取的部分页面块供人工复核。解析器不调用 OCR；更广泛的阈值评估属于 JAI-016，OCR 实现仍属于 JAI-B01。

### D-024 PDF 失败返回安全状态对象，不暴露第三方异常

密码保护 PDF 返回 `parser.encrypted_document`；空、无效、损坏或不可读 PDF 返回 `parser.corrupt_document`；错误 MIME 输入返回 `parser.invalid_input`。结果只包含安全固定消息，不包含文件正文、密码或原始 PyMuPDF 异常文本。

### D-025 JAI-017 抽取保持可追溯的纯内存边界

确定性抽取按解析器文本块或表格行对输出分组。每个字段都携带原值、规范值、来源引文和解析器位置。跨块/正文/附件合并及数据库 `field_evidence` 持久化继续属于 JAI-019，避免 JAI-017 在不同来源之间静默取舍。

### D-026 有证据但矛盾或不支持的值生成诊断

无效日期、倒置日期范围、没有显式 base 的相对 URL、非精确招聘人数，以及未知地区/学历/类别值都不会生成规范字段。安全的 `ExtractionIssue` 保留原值和证据；没有标签但看似关键的正文会被忽略，而不是猜测填充。

### D-027 复核与推荐资格由持久化校验结果推导

JAI-020 使用 `approved`、`review_required` 和 `blocked` 作为确定性结果。警告需要复核但仍可推荐；任何错误都会阻止自动推荐。旧数据显式标记为 `legacy-unvalidated` 且不可推荐，不会被静默批准。

### D-028 重解析版本是显式幂等 key

同一文档/抽取版本只有在合并结果哈希不变时才能重复。规则修正使用新版本，并追加公告、岗位、证据和校验历史。默认已存文档流水线不发起线上来源或 LLM 请求。

### D-029 并行匹配开发使用显式合并列车

用户批准在 JAI-021 仍处于自然日观测期间开发 JAI-023。JAI-023 分支从已推送的 JAI-022 末端 `44ed50292aa6609c7c4eaa1fb16e0793082d4e0a` 创建。集成顺序为：JAI-021 合并到 `develop`；更新后的 `develop` 普通合并到 JAI-022，随后完成 JAI-022 合并；再次更新的 `develop` 再普通合并到 JAI-023。每个边界都保留双语日志、显式解决冲突并重跑 PostgreSQL 完整门禁；继续禁止 rebase 和改写已发布历史。

### D-030 缺失证据不得变成猜测的硬过滤失败

只有显式学历不足、到达截止时间、命中排除词或 JAI-020 推荐阻塞才会过滤岗位。缺少学历或截止证据时仍保持可推荐，只损失相应紧迫度/完整度信号。这样既不虚构字段，也能把需要确认的数据留给 JAI-024。

### D-031 评估时间与偏好确认都是事务输入

匹配引擎显式接收带时区的 `evaluated_at`，不会读取进程时钟，因此紧迫度和哈希可复现。全量重算会锁定 JAI-022 单例，并只在所有当前岗位结果写入的同一事务中确认粘性信号。失败会同时回滚结果与确认，成功确认则保留代表偏好值身份的 `updated_at`。

### D-032 JAI-024 在不修改祖先分支的前提下扩展隔离合并列车

用户已批准在 JAI-021 等待自然日观测时继续并行推进后续开发。JAI-024 从已推送的 JAI-023 末端 `9592a16d7dee12fbe6c555407a3607a492b2cd03` 在独立 worktree 创建。集成顺序为 JAI-021 → JAI-022 → JAI-023 → JAI-024；每个下游分支都通过普通合并接收最新 `develop`，保留双语日志、显式解决冲突并重跑 PostgreSQL 完整门禁。继续禁止 rebase、force push 和改写已发布历史。

### D-033 JAI-025 保留 v1 基线并显式评估 v2

质量评审必须原样重放 `jai-023-v1`，并在同一份固定、脱敏、可人工复核的样本集上与新评分版本对比。标注、原因、Top 20 误推荐与漏召回都作为显式产物保留；调权只能改变新版本。调度、投递、LLM 重排、向量召回和线上来源采集均不属于 JAI-025。

## 3. 当前工作记录

### 2026-08-14 — JAI-046 双语文档与 Git 身份规则完成

- 核验交接分支 `feature/jai-046-bilingual-docs-git-identity` 位于 `29071dff1a80d26bac892d7bce548cf593c78eec`；工作区干净，分支尚未合并到 `develop`。
- 核验 JAI-037 已在 `c649862` 合并，`main` 仍为 `e72f50e`，`develop` 与缓存的远程跟踪引用无分歧。
- 核验仓库级和全局 Git 作者均为 `user9527448 <2537759248@qq.com>`；没有改写既有提交或作者历史。
- 第一轮质量门禁的 Ruff、Mypy 和 83 项非数据库测试通过，但 Docker 未运行导致 6 项 PostgreSQL 测试跳过，覆盖率 83.06%，低于 85% 门槛。
- Docker Desktop 启动后，数据库启用门禁通过：Ruff format/lint、Mypy、全部 89 项测试和 88.35% 覆盖率均达标。
- 以非快进合并 `f07b6d5` 把 JAI-046 纳入 `develop` 并普通推送；本地 HEAD、`origin/develop` 和 GitHub `ls-remote` 均为 `f07b6d50ed9abda08d38883eefa3904b98b99455`。

### 2026-08-14 — JAI-047 双语文档迁移基线开始

- 从已同步的 `develop` 提交 `f07b6d5` 创建 `feature/jai-047-bilingual-docs-migration`；没有从 `main` 或未合并 feature 分支开始。
- 盘点确认 `docs/DEVELOPMENT_PLAN.md`、`docs/GITHUB_ISSUES.md` 和混合语言 `docs/WORKLOG.md` 尚无独立的中英文配对，其他若干仓库文档仍属于存量单语文件。
- 本 Issue 仅登记 JAI-046 至 JAI-048、为本次实质修改的计划与 Backlog 补英文镜像、无损拆分活动工作日志，并同步双语索引。
- 原 WORKLOG 已逐字节复制到 `docs/archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`；源文件与归档 SHA-256 均为 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`。
- 本 Issue 不修改应用代码、来源 Adapter、数据库 Schema、网络采集行为或延期技术。
- 已为开发计划、Issue Backlog 和活动 WORKLOG 建立相互链接的独立中英文版本；两份文档索引明确区分已配对文档、不可变历史归档和 JAI-048 清单。
- 结构检查通过：开发计划标题 45/45、Backlog 标题 70/70、活动日志标题 13/13、索引标题 5/5，两份 Backlog 的 JAI 编号顺序完全一致。
- 相对链接检查覆盖 35 份 Markdown，未发现失效链接；`git diff --check` 通过，归档 SHA-256 保持不变。
- 数据库启用的最终门禁通过：Ruff format 检查 94 个文件，Ruff lint 通过，56 个源文件的 Mypy 通过，89 项测试全部通过，覆盖率 88.35%。
- 第一次暂存后的 `git diff --cached --check` 在新英文开发计划页眉中发现 4 行行尾空格。PowerShell 没有因前一条原生命令的非零状态停止，仍创建了尚未推送的本地提交；随后立即修正这 4 行，并准备独立的同范围修复提交，不改写历史。

### 2026-08-14 — JAI-012 运行统计、手动触发与失败重跑开始

- JAI-047 已普通推送到 `b428e43`，再以非快进合并 `87cd753` 纳入 `develop`；本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均核对为 `87cd7538af5cc3da41a811e1d48051358e6c6977`。
- 从该已同步的 `develop` 创建 `feature/jai-012-run-stats-retry`；没有从 `main` 或未合并 feature 分支开始。
- 范围遵循 Backlog：按来源手动触发并返回 run ID、查看运行摘要与失败条目，以及不会复制成功数据的失败重跑。
- 实施前先检查现有编排器、运行仓储/模型、API/CLI 边界、来源注册表、采集文档和测试；不加入调度、解析/抽取或延期来源集成。
- 实现持久化 `CrawlRunSummary` 查询和结构化失败的兼容解析；JAI-012 之前缺少 `step` 字段的失败记录仍可安全读取。
- 扩展采集编排：接入幂等原始公告持久化计数，并隔离单条持久化错误。`created`、`updated`、`skipped` 和总 `failed` 与详情专用计数、步骤状态一并保存。
- 增加失败运行重跑：要求原运行处于终态，只从持久化失败中提取 URL，重新发现公开列表以恢复元数据，筛选失败 URL，安全记录无法重新发现的条目，并通过 `retry_of_run_id` 创建关联的新运行。
- 为三个已启用官方来源增加显式运行时网站库匹配与 Adapter 接线。数据库来源必须精确匹配一个可运行网站库条目；仍禁止动态导入和执行配置中的任意 Adapter。
- 新增 `scripts/manage_crawl.py`，提供同步 `run`、只读 `show` 和失败条目 `retry` 命令。命令使用既有 PostgreSQL 配置和低频公开来源 HTTP 策略；没有增加维护 API 或调度器。
- 第一轮定向 Ruff 只发现 `__all__` 顺序和测试 import 分组，均已修正。第一轮 Mypy 发现脚本被识别为两个模块；新增 `scripts/__init__.py` 后只保留一个可导入命令包。第二轮 Mypy 暴露失败解析/测试设置中的窄 JSON 类型问题，通过显式校验修正，没有使用 suppression。
- 随后的定向检查通过：Ruff、62 个源文件的 Mypy，以及包含 PostgreSQL 的 23 项相关测试。
- PostgreSQL 验收证明：首次运行创建 2 条公告并记录 1 个失败；重跑重新发现 3 条但只抓取失败 URL，并新建 1 条公告；再次对同一原失败运行重跑仍只抓取该 URL，结果为 `skipped`，数据库最终恰有 3 条原始公告。
- 最终复核发现，原始公告持久化期间发生取消可能让运行停留在 `running`。编排器现在会把运行标记为 `cancelled`、保存安全进度并重新抛出取消；专用单元测试覆盖该路径。
- 最终数据库启用门禁通过：Ruff format 检查 100 个文件，Ruff lint 通过，62 个源文件的 Mypy 通过，105 项测试全部通过，覆盖率 88.38%。
- 已同步中英文采集文档、计划/Backlog 状态和活动 WORKLOG。没有新增依赖、Schema 迁移、凭据、运行数据、线上来源请求或延期技术。
- GitHub 端口 443 临时超时恢复后，已普通推送 feature 分支，并核对本地 HEAD、`origin/feature/jai-012-run-stats-retry` 与 GitHub `ls-remote` 均为 `7e5e888a09ff8bd13094f277631e87d021c27f7a`；没有改写历史或远程配置。

### 2026-08-15 — JAI-013 解析器协议与标准中间格式完成

- 以非快进合并 `70dd3b2` 把 JAI-012 纳入 `develop` 并普通推送；本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `70dd3b2144c12aff8e483ec89420ee4486374c2e`。
- 从该已同步的 `develop` 创建 `feature/jai-013-parser-protocol-intermediate-format`；没有从 `main` 或未合并 feature 分支开始。
- 范围仅限按 MIME 选择解析器、可追溯的文档/表格中间 Schema、解析状态和错误码、不支持格式处理、测试与双语文档；PDF 提取、OCR、Excel 表格启发式和字段抽取仍留给后续 Issue。
- 新增 `jobagent.parsers`，包含不可变来源/请求契约、从 1 开始的页/行/A1 单元格定位、文本/表格块、稳定状态/错误枚举、诊断和结果不变量；无需新增依赖或 Schema 迁移。
- 新增显式注册表：规范 MIME 参数、防止重复解析器名称/MIME、拒绝不一致的来源/名称输出，并在没有注册解析器时以 `parser.unsupported_media_type` 返回 `unsupported`。
- 新增 31 项定向测试，覆盖 HTML、PDF、XLS/XLSX 选择，来源与坐标校验，块/单元格可追溯性，注册冲突，以及不支持或不一致输出。
- 新增配对的中英文解析文档和索引条目，并同步附件指南、开发计划、Backlog 和活动日志。
- 第一轮统一门禁发现 `test_contracts` 测试模块重名；把 `tests/parsers` 设为包后解决。第二轮发现新 A1 校验器中的正则分组类型过宽；显式传递捕获组后解决，未使用 suppression。
- 最终启用 PostgreSQL 的 `scripts/check.py` 门禁通过：Ruff format 检查 108 个文件，Ruff lint 通过，68 个源文件的 Mypy 通过，136 项测试全部通过，覆盖率 88.85%。
- 已普通推送 JAI-013，并核对本地 HEAD、`origin/feature/jai-013-parser-protocol-intermediate-format` 与 GitHub `ls-remote` 均为 `269648a384027de772b2fa2c4dd5661cb183594c`。

### 2026-08-16 — JAI-014 PDF 文本解析与扫描件识别完成

- 以非快进合并 `36d389f` 把 JAI-013 纳入 `develop` 并普通推送；本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `36d389fbe1edffe5131eba09ea16a21623d0f3d6`。
- 从该已同步的 `develop` 创建 `feature/jai-014-pdf-text-scan-detection`；没有从 `main` 或未合并 feature 分支开始。
- 范围仅限已注册 PDF 解析器、页级文本与元数据、确定性的扫描/低文本判断、加密/损坏诊断、测试和双语文档。OCR 实现、Excel 解析、解析 worker 持久化和字段抽取均不在范围内。
- 新增 `PdfTextParser`、`PdfTextPolicy` 和显式生产注册表构造。正常 PDF 生成带从 1 开始证据页码的规范化页面块；结果元数据保留页数、字符统计和非空的标准 PDF 元数据。
- 图像-only 和低文本 PDF 返回 `ocr_required`，但不执行 OCR。加密、损坏、空/不可读和错误 MIME 输入返回稳定安全 Issue，不泄露第三方异常。
- 新增 11 项 PDF 测试，使用既有真实四页固定样本，以及运行时生成的图像-only、低文本、加密和损坏输入。全部 42 项解析器测试均离线通过，没有访问线上来源或提交运行文件。
- 已同步中英文解析/附件文档、计划、Backlog 和活动日志。没有新增依赖、数据库迁移、worker、网络采集器、OCR 引擎或 Excel 行为。
- 首轮定向静态检查只发现格式/导出顺序，以及窄 PyMuPDF 和 JSON 联合类型边界；通过显式类型收窄和 Spike 已确立的同类有限第三方 suppression 解决，行为测试始终通过。
- Docker Desktop 和既有 Compose 数据库最初未运行；启动现有安装与 `db` 服务后恢复既有 `jobagent_test`，没有重建或删除数据。
- 最终启用 PostgreSQL 的 `scripts/check.py` 门禁通过：Ruff format 检查 111 个文件，Ruff lint 通过，71 个源文件的 Mypy 通过，147 项测试全部通过，覆盖率 89.07%。
- 已普通推送 JAI-014；推送时本地 HEAD、`origin/feature/jai-014-pdf-text-scan-detection` 与 GitHub `ls-remote` 均为 `8964272973ef581ec3cc2ff36425810b7998e22e`。后续合并前重试 `ls-remote` 时连接被重置，仓库状态未发生变化。

### 2026-08-16 — JAI-015 Excel 岗位表解析启动

- 已推送 JAI-014 交接提交 `028bbfb` 并核对本地、跟踪和 GitHub feature 引用一致，随后以非快进合并 `8f21745` 纳入 `develop` 并普通推送。本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `8f21745bf0d7f3b0ca6736c3bebe2db86e9fdf86`。
- 从该已同步的 `develop` 创建 `feature/jai-015-excel-position-table-parsing`；没有从 `main` 或未合并 feature 分支开始。
- 范围仅限 XLSX 工作表、确定性表头/数据区识别、空行、合并单元格、可追溯单元格/行证据、复核诊断、测试和同步文档。黄金样本批量评估仍属于 JAI-016；字段抽取仍属于 JAI-017。
- 既有 `.venv` 不含 `openpyxl`、`xlrd` 或 `pandas`。JAI-015 将使用最小且声明明确的 `openpyxl` 依赖支持 XLSX；不会为旧版 XLS 提前引入未经验证的第二套解析依赖，而是保持显式不支持。
- 新增已声明的 `openpyxl>=3.1,<4` 运行时依赖，并向既有 `.venv` 安装 3.1.5；未下载新 Python、`pandas` 或 `xlrd`。
- 新增 `ExcelPositionTableParser`、有界 `ExcelTablePolicy`、XLSX 生产注册和 `parser.header_not_recognized`。有效表头必须包含岗位标签和另一项已知招聘标签；候选选择具有确定性。
- 每个已识别工作表生成一个 `TableBlock`，其单元格保留工作表/A1 证据。全空数据行会跳过并记录；继承合并单元格的值指向完整原合并范围；多个表格保持工作簿原顺序。
- 无法识别或只有表头的工作表携带 `review_required=true`。若其他工作表成功，这些 Issue 保留在 `parsed` 结果；若全部失败，结果为 `failed`。这里复用既有持久化状态词汇直到 JAI-020，不提前新增计划外数据库状态。
- 旧版 XLS 未注册，因为环境没有既有 XLS 依赖，JAI-015 也没有代表性 XLS 固定样本。注册表分发返回显式 `unsupported`；JAI-016 可为后续依赖决策提供证据。
- 新增 8 项 XLSX 测试，覆盖中英文及两层合并表头、多工作表、空行、纵向合并单元格、单元格/范围证据、复核诊断、损坏/错误输入、策略校验和 XLS 注册行为。首轮定向检查只发现导出排序、JSON 联合类型收窄、日期规范化及既有 PDF 注册表预期，均已修正，50 项解析器测试通过。
- 已同步中英文解析文档、计划、Backlog 验收和活动日志。最终启用 PostgreSQL 的 `scripts/check.py` 通过：Ruff format 检查 113 个文件，Ruff lint 通过，73 个源文件的 Mypy 通过，155 项测试全部通过，覆盖率 89.51%。
- 最终文档检查确认 37 份 Markdown 无失效相对链接；4 组本次修改的双语文档标题数量一致，两份 Backlog 中 161 次 Issue 编号出现顺序一致，且 `git diff --check` 通过。
- 已普通推送 JAI-015，并核对本地 HEAD、`origin/feature/jai-015-excel-position-table-parsing` 与 GitHub `ls-remote` 均为 `7a5f3a3d29d7bb40459dbaa10fb30ce6c2835f5b`。

### 2026-08-16 — JAI-016 附件黄金样本与回归启动

- 已推送 JAI-015 交接提交 `633ebc1` 并核对本地、跟踪和 GitHub feature 引用一致，随后以非快进合并 `fca197d` 纳入 `develop` 并普通推送。本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `fca197de89634517a0aac6fbd84f1e63cc5573f0`。
- 从该已同步的 `develop` 创建 `feature/jai-016-attachment-golden-samples-regression`；没有从 `main` 或未合并 feature 分支开始。
- 范围仅限至少 10 份脱敏 PDF/XLSX 固定样本、已提交的期望中间结果、离线批量评估器、回归测试和同步文档。解析器功能扩展和字段抽取仍不在范围内。
- 新增 5 份纯合成 PDF 和 5 份纯合成 XLSX，覆盖多页、稀疏/空白文本、中英文表头、多工作表、合并单元格、空行、3 种日期表示和无法识别表头的复核结果；不含下载的来源材料或真实个人数据。
- 新增已审查的 `manifest.json`，保存完整规范文本/表格块与页码/A1 证据。`serialize_parse_result()` 排除不稳定来源 ID 和第三方库元数据，同时保留与解析行为相关的输出。
- 新增 `evaluate_golden_fixtures()`、稳定汇总/差异报告和 `scripts/evaluate_attachment_fixtures.py`。评估器使用生产注册表、不访问网络，输出总数/匹配数/成功率及完整逐样本 expected/actual 差异，发生回归时返回非零退出码。
- 保留独立显式生成器，使纯合成二进制来源可审查；常规回归测试不会重新生成或静默批准快照。新增测试证明 10 份已提交样本全部匹配，且篡改一项期望后会产生 1 条详细差异和 90% 成功率。
- 新增独立中英文固定样本说明，并同步两份文档索引、解析文档、计划、Backlog 验收和活动日志。
- 最终离线评估为 10/10、成功率 100%、无差异。启用 PostgreSQL 的 `scripts/check.py` 通过：Ruff format 检查 119 个文件，Ruff lint 通过，77 个源文件的 Mypy 通过，157 项测试全部通过，覆盖率 89.30%。
- 最终文档检查确认 39 份 Markdown 无失效相对链接；6 组本次修改的双语文档标题数量一致，两份 Backlog 中 161 次 Issue 编号出现顺序一致，且 `git diff --check` 通过。
- 已普通推送 JAI-016；推送时本地 HEAD、`origin/feature/jai-016-attachment-golden-samples-regression` 与 GitHub `ls-remote` 均为 `819c63fa00d31225ad65723605e91c0b8366bc2d`。后续合并前重试 `ls-remote` 时 GitHub 443 超时，仓库状态未发生变化。
- 已推送 JAI-016 交接提交 `7bb600e`，以非快进合并 `76ecd4b` 把已核验 feature 分支纳入 `develop`，并在 GitHub 443 临时故障恢复后普通推送。本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `76ecd4b8bd087a277b4cc0ecc55135f0e11ae86d`；JAI-016 是其祖先，工作区干净。

### 2026-08-22 — JAI-017 确定性字段抽取与规范化启动

- 已核验干净的 `develop` 位于 `1dc7a100d7dfb8b17ac33a2d03ee2255e4500b65`；本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致，JAI-016 feature 提交 `05bac9cf4fba48330fbab3424535a90422b17a4b` 已合并。
- 已核验仓库本地作者为 `user9527448 <2537759248@qq.com>`，并保留现有 HTTPS origin。
- 已从同步后的 `develop` HEAD 创建 `feature/jai-017-deterministic-field-extraction`。
- 范围仅限确定性日期/时区、地区字典匹配、URL、招聘人数、学历/枚举，以及同时保留原值、规范值和来源证据的输出。LLM provider/Prompt/预算、正文与附件合并、数据库 `field_evidence` 持久化仍分别属于 JAI-018/JAI-019。
- 下一步：检查解析器中间契约与黄金样本，定义抽取契约，再先实现定向测试，最后运行完整质量门禁。
- 新增 `jobagent.extraction` 契约、有界地区/学历/类别字典和确定性正文/表格规则。只有日期的边界使用配置时区的当地日期，所有日期时间统一规范为 UTC；无效/倒置日期保留为有证据诊断。
- 新增 16 项定向测试，包括实际解析已提交 XLSX 黄金样本中的 `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYY年M月D日`，显式/默认时区、报名 URL 规范化、不支持值诊断和无证据/无标签行为。
- 新增配对的中英文抽取文档和两份文档索引条目。没有新增依赖、配置字段、数据库迁移、LLM 行为、正文/附件合并、持久化代码、OCR、凭据、个人数据、运行数据或线上来源请求。
- 完整 `scripts/check.py` 门禁通过：Ruff format 检查 128 个文件，Ruff lint 通过，84 个源文件的 Mypy 通过，166 项测试通过；Docker 未运行，因此 7 项仅 PostgreSQL 测试按既有机制跳过；覆盖率为 85.27%。本 Issue 没有数据库或迁移改动；该 Docker 限制已如实记录，不把跳过项当作通过。
- 文档检查通过：开发计划标题 45/45、Backlog 70/70、新抽取文档 6/6、活动日志 28/28、索引 5/5；两份 Backlog 的 161 次 Issue 编号出现顺序一致，所有 Markdown 相对链接有效，`git diff --check` 通过。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建 feature 提交 `c1da6cec5969cdb40952fd2c0205b5ce196f6554`；提交后工作区干净。
- 两次 HTTPS 普通推送和一次只读 `git ls-remote` 均在约 21 秒后因 GitHub 443 无法连接而失败。远程 URL、协议、分支历史和提交均未改变；网络恢复后继续重试同一非强制推送。
- 第三次相同的普通推送成功，已创建远端 JAI-017 分支并建立跟踪引用。本地 HEAD 与 `origin/feature/jai-017-deterministic-field-extraction` 均为 `c1da6cec5969cdb40952fd2c0205b5ce196f6554`；紧接着的 `ls-remote` 核验再次遇到 443 连接失败，因此最终交接日志提交后仍须完成三端核验。
- 已普通推送恢复日志提交 `35f657e62f557182fc1af3590a820177a7e1a185`；又一次短暂 `ls-remote` 失败后，本地 HEAD、跟踪引用与 GitHub `ls-remote` 均核对为该提交。这次仅状态更新的最终日志关闭 JAI-017 feature 交接；没有合并到 `develop`。

### 2026-08-22 — JAI-018 可替换 LLM 抽取服务启动

- 已用非快进合并 `c7a2ebe1082588257fd0353c04c650a698fd6e06` 把核验后的 JAI-017 feature 分支纳入 `develop`，并在 GitHub 443 临时故障后完成普通推送。本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为该提交，且 JAI-017 是其祖先。
- 已从同步后的 `develop` HEAD 创建 `feature/jai-018-replaceable-llm-extraction`，仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 范围仅限可配置 provider 边界、严格 JSON Schema 输出校验、Prompt 版本、超时/重试、token/成本调用记录、测试替身和单日预算排队。正文/附件结果合并及数据库 `field_evidence` 持久化仍属于 JAI-019。
- 下一步：定义内存契约和 provider 适配器，实现基于 mock transport 的定向测试，再同步双语文档并运行相称的质量门禁。
- 新增严格 Pydantic candidate/payload 契约、单一来源解析器片段、与 provider 无关的协议，以及复用现有 `httpx` 依赖的 `OpenAIResponsesProvider`。适配器发送严格 `text.format` JSON Schema，防御性解析输出和用量，区分可重试失败，且不暴露 provider 响应正文或 API key。
- 新增 `LlmExtractionService`，实现显式 Prompt 版本、原值/引文/来源片段逐字校验、有界指数退避、逐请求模型/Prompt/token/成本/状态记录、并发安全的最大成本预留，以及将会跨过单日预算的请求送入待处理队列。非法输出保留用量/成本元数据，但不暴露候选 payload，也不能写入业务表。
- 调用记录与待处理任务均保留在协议之后，当前只提供进程内默认实现。没有新增数据库迁移、`field_evidence` 持久化、正文/附件合并、优先级、冲突解决、真实 provider 请求、新 SDK 依赖、凭据或硬编码的 provider 价格/模型。
- 新增 12 项 provider/契约测试和 7 项服务测试，使用脚本化 provider 与 `httpx.MockTransport`。首次完整测试为 181 项通过、7 项 PostgreSQL 跳过，但覆盖率 84.90%，未达到保持不变的 85% 门槛；补充错误/配置边界测试后覆盖率提高。后续组合检查的 Pytest 已在 85.58% 通过，但暴露一处仅 Mypy 发现的动态测试字典类型错误，已改为显式类型参数。
- 最终 `scripts/check.py` 通过：Ruff format 检查 136 个文件，Ruff lint 通过，90 个源文件的 Mypy 通过，189 项测试通过；Docker 未运行，因此 7 项仅 PostgreSQL 测试按既有机制跳过；覆盖率为 85.58%。JAI-018 不新增数据库或迁移行为，该环境限制已如实记录，不把跳过项当作通过。
- 文档检查通过：42 份 Markdown 无失效相对链接；开发计划标题 45/45、Backlog 70/70、活动日志 29/29、索引 5/5、新 LLM 指南 6/6；两份 Backlog 的 161 次 Issue 编号出现顺序一致，且 `git diff --check` 通过。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建实现提交 `d70b8a98fdc70fd65e9754451e563d33c5cd7336`，并普通推送到新建的跟踪分支。紧接着的 `ls-remote` 核验遇到一次 GitHub 443 瞬时连接失败；重试已成功，在本次仅状态交接更新之前，本地 HEAD、跟踪引用与 GitHub 均为 `d70b8a98fdc70fd65e9754451e563d33c5cd7336`。
- 用户启动 Docker Desktop 后，已启动仓库既有 `db` Compose 服务，未重建容器或删除数据卷；服务进入 healthy，隔离的 `jobagent_test` 数据库已存在。将 `JOBAGENT_TEST_DATABASE_URL` 指向该 `_test` 数据库后，完整 `scripts/check.py` 再次通过：Ruff format 检查 136 个文件，Ruff lint 通过，90 个源文件的 Mypy 通过，包含 7 项 PostgreSQL 集成测试在内的 196 项测试全部通过、无跳过，覆盖率为 88.64%。
- 已创建 PostgreSQL 验证提交 `0aa57178e962b81d355d8edd7a0a927a8f77690e`。随后三次普通推送和两次只读 `ls-remote` 均因 GitHub 443 持续不可达而失败，其中包含一次 15 秒退避后的重试。工作区与已发布历史均未改变；本地 feature 分支安全领先跟踪分支，须在 HTTPS 连通性恢复后继续普通推送。
- 后续系统 TCP 探测确认 GitHub 443 已恢复。保持不变的普通 HTTPS 推送随即把远程 feature 分支推进到故障日志提交 `ccc64a14bcd59df7d8d1677906e55f0ad9739705`；又一次瞬时读取失败后，第二次 TCP 探测与 `ls-remote` 已确认在本次最终状态更新之前，本地 HEAD、跟踪引用与 GitHub 均为该提交。

### 2026-08-23 — JAI-019 字段证据合并与持久化启动

- 已重新核验干净的 JAI-018 feature 分支为 `3da9ccad55aeb9eb0962f220e3c500288208ed93`，`develop` 为 `c7a2ebe1082588257fd0353c04c650a698fd6e06`；GitHub 443 临时故障恢复后，本地、跟踪与 GitHub 引用一致。
- 已用非快进合并 `c013544f3339efd776121c6792978f83d958062f` 把 JAI-018 纳入 `develop`，完成普通推送，并核验本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致。仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 已从同步后的 `develop` HEAD 创建 `feature/jai-019-field-evidence-merging`。
- 范围仅限确定性正文/附件优先级、显式保留冲突、置信度与抽取版本元数据、`job_posts`/`job_positions` 实体化和持久 `field_evidence`。JAI-020 的校验/复核/重解析 API 及所有后续来源接入不在范围内。
- 下一步：基于现有抽取模型和 PostgreSQL Schema 定义合并与持久化契约，新增保留版本历史所需的最小迁移，再先实现单元和数据库验收测试，最后运行完整门禁。
- 新增 `ExtractionMergeInput`、LLM 片段绑定、按字段目标区分的确定性优先级、LLM 值语义校验、稳定候选去重、显式落选冲突证据、部分岗位记录和 SHA-256 合并结果哈希。规则证据使用置信度 1.0000，LLM 方法使用 0.6000；不信任模型自评分数。
- 公告字段优先使用确定性正文证据，岗位字段优先使用确定性附件证据；确定性候选始终先于 LLM 候选。所有矛盾规范值和精确坐标保持可查询。没有证据能证明不同来源岗位相同时，各岗位行保持独立；不会虚构占位名称。
- 新增迁移 `0004_versioned_field_evidence`：为 `job_posts` 增加版本/哈希/当前/前序元数据和逐版本唯一约束；为 `job_positions` 增加稳定记录 key 并允许无证据名称为空；为 `field_evidence` 增加原值/规范值、方法/版本、选中/冲突标记和页/行/工作表/单元格坐标。既有行回填为 `legacy-v1`。
- 新增 `SqlAlchemyExtractionRepository`，实现逐公告 advisory lock、附件归属校验、公告/岗位/证据原子写入、相同版本/哈希复用、同版本哈希漂移拒绝，以及保留旧实体与证据的追加式新版本。
- 新增 5 项合并单元测试、1 项 PostgreSQL 仓库验收测试和 1 项旧数据迁移测试，覆盖正文/附件冲突、确定性优先于 LLM、非法 LLM 语义、与输入顺序无关的哈希、岗位/证据坐标、幂等重跑、版本链、历史保留、空 Schema 升级/检查/降级和 0003 数据回填。
- 早期迁移测试期间 Docker Desktop 停止，两次重复 Pytest 调用仍在等待同一个测试 Schema。已确认进程命令行，仅终止这些测试进程，通过系统注册项重新启动 Docker Desktop，并在不重建/删除数据卷的情况下恢复既有 `db` 服务；随后先逐项重跑数据库测试，再运行完整门禁。
- 首次启用 PostgreSQL 的完整 `scripts/check.py` 通过：Ruff format 检查 141 个文件，Ruff lint 通过，94 个源文件的 Mypy 通过，203 项测试全部通过、无跳过，覆盖率为 88.07%。
- 新增配对的中英文合并/证据文档和索引条目，并同步数据库文档、计划、Backlog 验收与活动日志。文档检查确认 44 份 Markdown 无失效相对链接；开发计划标题 45/45、Backlog 70/70、活动日志 30/30、索引 5/5、数据库文档 6/6、新指南 6/6；两份 Backlog 的 161 次 Issue 编号出现顺序一致，且 `git diff --check` 通过。
- 文档同步后的首次门禁未设置 `JOBAGENT_TEST_DATABASE_URL`：194 项测试通过、9 项 PostgreSQL 测试跳过，覆盖率降至 83.51%，因此门禁按预期失败。补入仓库文档登记的测试库 URL 后，最终 `scripts/check.py` 通过：Ruff format 检查 143 个文件，Ruff lint 通过，94 个源文件的 Mypy 通过，203 项测试全部通过、无跳过，覆盖率为 88.07%。
- 没有新增 JAI-020 的校验严重度、复核状态、推荐资格、修正流程或重解析命令/API；也没有线上来源/provider 请求、凭据、个人数据、下载文件或运行数据进入提交。
- 已使用核验无误的仓库本地作者创建 JAI-019 功能提交 `a2c41fee65bfcbf0374af96f5b028ab40bf565a6`。三次普通 HTTPS 推送均在网络层失败（两次 GitHub 443 连接超时、一次连接重置），其中已在 TCP 探测暂时恢复后重试。没有改变远程地址、协议、已发布历史或提交作者；本地 feature 提交安全保留，须在网络恢复后继续普通推送。
- 再次有界退避且 TCP 探测成功后，保持不变的普通 HTTPS 推送已发布功能提交和阻塞日志提交，推进至 `a7d5e17f44832acc774e86752be0421fdacb3adc`。后续网络恢复时，`ls-remote` 已确认在本次最终状态更新之前，本地 HEAD、跟踪引用和 GitHub 均为该提交；GitHub `develop` 仍为 `c013544f3339efd776121c6792978f83d958062f`。

### 2026-08-25 — JAI-020 数据校验、待复核与重解析启动

- GitHub 连通性恢复后，已普通推送 JAI-019 最终交接提交。本地 HEAD、跟踪引用与 GitHub `ls-remote` 均为 `01417b89256f8730f78317c17bb1101ed3707818`。
- 已用非快进合并 `82797d1fa91b1f5e77296d04e3138a9fabe7b499` 把 JAI-019 纳入 `develop`，在一次 GitHub 443 瞬时超时后完成普通推送，并核验本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致。仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 已从同步后的 `develop` HEAD 创建 `feature/jai-020-validation-review-reparse`。两份 Backlog 的下一项未完成 Issue 均为 JAI-020。
- 范围仅限必填、时间逻辑、URL、枚举和冲突校验；记录原因/严重度；复核与自动推荐资格；以及规则修正后对指定文档执行幂等重解析的命令/API。新增来源、评分/匹配、OCR、调度扩展和绕过来源限制均不在范围内。
- 下一步：检查 JAI-019 版本化实体及既有 CLI/API 模式，定义最小校验/重解析契约和持久化改动，再先实现定向单元/数据库/API 测试，最后运行完整的 PostgreSQL 门禁。
- 新增确定性 `ExtractionValidator` 问题，包含稳定 issue key、`warning`/`error` 严重度、推导出的 `approved`/`review_required`/`blocked` 状态和自动推荐资格。缺少关键字段、非法日期/URL/枚举及严重冲突会阻止推荐；非关键不完整/冲突保留为复核警告，不猜测值。
- 新增迁移 `0005_validation_review_reparse`：`job_posts` 保存校验/复核元数据，`validation_issues` 通过受限外键保存逐版本安全原因和严重度。旧公告回填为 `review_required`、不可推荐和 `legacy-unvalidated`。
- 扩展 `SqlAlchemyExtractionRepository`，使每个新抽取版本在同一事务写入校验与问题；幂等重复复用相同实体和计数。新增 `StoredDocumentReparsePipeline`、共享 `ReparseService`、`POST /extraction/documents/{document_id}/reparse` 和带显式安全版本标识符的 `scripts/manage_extraction.py reparse`。
- 重解析使用已存 `raw_text` 或从已存 HTML 清理出的文本，并在解析前核验每个持久附件的路径、字节数和 SHA-256。附件缺失/无法解析时显式失败。默认流水线只执行确定性解析/抽取/合并，不访问来源或调用 LLM。
- 102 个源文件的静态检查通过，11 项定向校验/API/命令测试通过。Docker Desktop 未运行，因此启动了已安装应用和既有 `db` Compose 服务，未重建或删除数据卷；`jobagent_test` 健康。
- 首轮 PostgreSQL 测试为 1 项通过、3 项失败：两项 Alembic 漂移失败暴露校验约束误挂到 `raw_documents`；一项仓库预期使用了旧式手工值 `CN-11`/`CN-31`，与当前 `beijing`/`shanghai` 字典不一致。已把约束移至 `job_posts`，并让测试对齐生产字典而不放宽校验；随后 4 项迁移/仓库/重解析数据库测试全部通过。
- 首轮启用 PostgreSQL 的完整 `scripts/check.py` 通过：Ruff format 检查 152 个文件，Ruff lint 通过，102 个源文件的 Mypy 通过，215 项测试全部通过、无跳过，覆盖率为 88.06%。
- 新增配对的校验/重解析文档和索引条目，并同步数据库文档、计划、Backlog 验收与活动日志。没有新增来源 4/5、匹配/评分、OCR、调度、手工改值/审批 API、凭据、个人数据、下载来源文件或运行数据。
- 文档核验确认仓库 46 份 Markdown 无失效相对链接；开发计划标题 45/45、Backlog 70/70、活动日志 33/33、索引 5/5、数据库文档 6/6、新指南 7/7；两份 Backlog 的 161 个 Issue ID 顺序一致，且 `git diff --check` 通过。首次全仓库链接检查命令存在 PowerShell 变量插值语法错误；修正后的只读命令通过，未修改文件。
- 畸形 URL 防御测试通过，但首次组合静态检查发现仅为触发校验而访问 `parsed.port` 的 Ruff `B018`；已改为显式接收校验值，未增加忽略规则。
- 所有文档和防御性测试完成后，最终启用 PostgreSQL 的 `scripts/check.py` 通过：Ruff format 检查 154 个文件，Ruff lint 通过，102 个源文件的 Mypy 通过，216 项测试全部通过、无跳过，覆盖率为 88.07%。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建功能提交 `67120101ea0c926f327b781a6e69c05350d41df7`，并普通推送新 feature 分支。在本次最终状态更新之前，本地 HEAD、跟踪引用和 GitHub `ls-remote` 均为该提交；GitHub `develop` 仍为 `82797d1fa91b1f5e77296d04e3138a9fabe7b499`。

### 2026-08-29 — JAI-022 单用户偏好并行启动

- 已确认 JAI-020 完成合并：本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为非快进合并 `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`，其第二父提交是 JAI-020 feature 末端 `9c86cad8eb621b20fa70e1e6a07a377f929608a3`。
- 用户明确批准 JAI-021 只剩自然日观测期间的一次有边界 WIP 例外。已直接从三端核验一致的 `develop` 创建 `feature/jai-022-single-user-preferences`；其 `git log` 祖先不包含任何未合并的 JAI-021 提交。
- 合并边界固定：JAI-021 只在自己的分支继续并必须先完成/合并；随后把最新 `develop` 普通合并到 JAI-022，保留两份双语 WORKLOG 历史，显式处理文档冲突并重跑启用 PostgreSQL 的完整门禁。绝不 rebase 或改写已发布历史。
- JAI-022 只实现一个结构化用户偏好模型和读取/更新 API，覆盖地区、学历、专业、岗位关键词、单位类型和排除词；必须具备输入校验、更新时间、重算信号和不会过滤全部岗位的默认值。JAI-023 评分/过滤保持在范围外。
- 下一步：检查现有模型、迁移、API 约定和测试，在实施前定义最小偏好契约与持久化边界。

### 2026-08-30 — JAI-022 实现与功能分支验收完成

- 新增迁移 `0006_single_user_preferences` 和固定 `id=1` 的 ORM 单例。迁移插入不会筛空的默认值：地区/专业/关键词/单位类型/排除词均为空数组，`education=null`，且没有待处理重算。数据库约束会校验 JSON 数组形状和学历值。
- 新增 `GET /preferences` 和全量替换 `PUT /preferences`。地区和学历复用确定性抽取枚举；单位类型有意使用独立的 `government`/`public_institution`/`state_owned`/`private`/`foreign_enterprise` 词表，避免把来源分类误作单位属性。文本会进行 NFKC/空白规范化，并按稳定顺序去重。
- 更新会锁定单例行并保存 `updated_at`。`trigger_recompute=true` 会设置粘性的待处理标志和请求时间；延迟重算的更新不能抹除已有请求。信号消费、硬过滤、评分与实际重算属于 JAI-023，本分支没有提前实现。
- 新增 API/模型/迁移/仓库/枚举对齐测试，并同步偏好、数据库、索引、计划、Backlog 和日志双语文档。首次定向仓库测试仅因新 Windows 测试使用默认 Proactor 事件循环而失败，psycopg async 不支持该循环；改为仓库既有的 `asyncio.SelectorEventLoop` 后，3 项定向 PostgreSQL 测试全部通过。首次枚举测试 Mypy/完整门禁还暴露了重复的裸模块名 `test_contracts`；将其改名为 `test_preference_contracts` 后修复包发现，不改变断言。
- 已启动 Docker Desktop 和既有 `db` 服务，未重建容器或删除数据卷；确认现有隔离库 `jobagent_test`。最终 `scripts/check.py` 通过：Ruff format 检查 164 个文件，Ruff lint 通过，109 个源文件的 Mypy 通过，224 项测试全部通过、无跳过，覆盖率 88.18%。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建功能提交 `38cca14`。两次普通推送均未更新远端：首次连接被重置，第二次在 GitHub 443 端口超时；只读 `ls-remote` 同样超时。DNS 仍将 `github.com` 解析为 `20.205.243.166`，Git 未配置代理，但直接 TCP 443 探测失败。本地提交和分支保持完整，没有使用 force/rebase。
- 2026-08-30 01:27 +08:00 继续重试时，GitHub 443 仍然超时。只读诊断确认没有 `HTTP_PROXY`/`HTTPS_PROXY` 环境设置，WinHTTP 采用直接连接，Windows 用户代理已禁用，常见本地代理端口也没有监听。当前日期仍属于 JAI-021 合格 Day 2；2026-08-31 之前不能如实执行 Day 3。
- 后续普通推送已经成功。本地 HEAD、跟踪引用和 GitHub `ls-remote` 均为 `e8e29610bfe3d84051b75defa83adcb8c72a9ad3`；GitHub `develop` 保持 `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`，没有被改动。
- 下一步：JAI-021 完成并先合并后，把更新后的 `develop` 普通合并到本分支，保留两份双语日志、处理配对文档冲突、重跑 PostgreSQL 完整门禁，之后才合并 JAI-022。

### 2026-08-30 — JAI-023 硬过滤与版本化规则评分并行启动

- 用户明确批准在 JAI-021 继续验收观测时并行推进后续开发，前提是完整记录依赖、合并边界并保持版本历史安全。
- 已核验 `feature/jai-023-hard-filter-versioned-scoring` 位于 `44ed50292aa6609c7c4eaa1fb16e0793082d4e0a`；其 HEAD 与已推送 JAI-022 末端的 merge base 完全一致。仓库本地作者仍为 `user9527448 <2537759248@qq.com>`，现有 HTTPS origin 未改变。
- 合并顺序固定为：JAI-021 → `develop`；更新后的 `develop` → JAI-022 并完成 JAI-022 合并；再次更新的 `develop` → JAI-023。所有双语 WORKLOG 历史都必须保留，冲突须显式解决，每个边界重跑 PostgreSQL 完整门禁，绝不 rebase 或改写已发布历史。
- 范围仅限学历/截止/排除词硬过滤，地区/岗位方向/专业/单位类型/截止紧迫度/信息完整度分项评分，确定性评分版本，逐分项规则/输入/得分/解释持久化，以及消费 JAI-022 偏好信号执行全量重算。
- JAI-024 的日报查询、渲染、快照和通知均保持在范围外。
- 下一步：检查 JAI-022 偏好契约和现有岗位实体，再新增最小匹配契约、迁移、确定性引擎、重算仓储及边界测试。
- 新增纯 `DeterministicMatchingEngine` 版本 `jai-023-v1`：显式记录校验资格/学历/截止/排除词决定，并固定地区 25、方向 30、专业 15、单位 10、紧迫度 10、完整度 10 六个分项。UTC 标准 JSON 分别生成输入、偏好和结果 SHA-256。
- 新增迁移 `0007_versioned_match_results`、ORM 当前/历史关系、JSONB 规则/分项解释、计算唯一性、分数/哈希约束，以及指向岗位/偏好/自身历史的受限外键。
- 新增 `SqlAlchemyMatchingService.recompute_if_requested()`：锁定单例偏好，按 ID 稳定顺序评估当前公告版本下的全部岗位，追加/切换结果，并只在完整事务提交时清除粘性信号；信号确认不改变偏好值更新时间。
- 只对语义直接的类别推导单位类型（`civil_service`、`public_institution`、`state_owned`）；`campus` 和 `social` 保持未知。不会猜测单位类型、截止、学历或其他缺失值。
- 新增 16 项引擎边界测试和 PostgreSQL 全量重算验收测试。最终文档同步前的首轮完整门禁已通过：Ruff format 检查 172 个文件，Ruff lint 通过，116 个源文件的 Mypy 通过，241 项测试全部通过、无跳过，覆盖率 88.47%。
- 新增配对匹配文档，并同步数据库/偏好指南与两份索引。文档检查通过：配对标题数量一致，两份 Backlog 保持相同的 171 个 Issue 标识及顺序，仓库 Markdown 相对链接均有效，`git diff --check` 通过。
- 文档同步后的最终 `scripts/check.py` 门禁通过：Ruff format 检查 174 个文件，Ruff lint 通过，116 个源文件的 Mypy 通过，241 项测试全部通过、无跳过，覆盖率 88.47%。
- 未新增 JAI-024 日报查询/分组/渲染/快照/通知、调度、LLM rerank、向量召回、公开匹配 API、凭据、个人数据、下载来源文件或运行数据。
- 下一步：提交并普通推送该独立 feature 分支，核验本地/跟踪/GitHub 引用，再等待已记录的 JAI-021/JAI-022 集成顺序完成后同步 `develop`。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建功能提交 `8a334e5`。首次 HTTPS 普通推送在约 21 秒后因 GitHub 443 不可达而失败；只读 `ls-remote` 同样失败，TCP 探测把 `github.com` 解析到 `20.205.243.166`，但 443 端口不通。远程分支、协议、历史和作者均未改变；连通性恢复后重试相同的非强制推送。
- 后续保持不变的普通推送已经成功。本地 HEAD、跟踪引用和 GitHub `ls-remote` 均为阻塞记录末端 `18cdc97c16cc02fbb2cdd6383258c811bd062cea`；`develop`、JAI-021 与 JAI-022 均保持不变并相互隔离。

### 2026-09-03 — JAI-024 日报查询与渲染并行启动

- 已确认 JAI-024 是 JAI-023 后下一项未完成计划 Issue，且仅依赖 JAI-023。从已推送的 JAI-023 末端 `9592a16d7dee12fbe6c555407a3607a492b2cd03` 创建 `feature/jai-024-daily-report-rendering` 和隔离 worktree `data/worktrees/jai024`；其与 JAI-023 的 merge base 完全一致。
- 范围仅限优先投递、即将截止、今日新增、需要确认四组；同输入/同日期稳定排序；Markdown/HTML 渲染；日报快照和原文链接。JAI-025 质量评审、JAI-026 调度、JAI-027 通知发送及全部凭据/通道行为保持在范围外。
- 集成边界明确：先合并 JAI-021，再依次合并 JAI-022、JAI-023，最后合并 JAI-024。每个分支都先普通合并最新 `develop`，保留双方 WORKLOG 历史、解决配对文档冲突，并在集成前重跑 PostgreSQL 完整门禁。
- 新增纯日报版本 `jai-024-v1`。显式报告日期和时区定义本地自然日窗口，不读取进程时钟。当前硬过滤通过的匹配按稳定且各组独立的顺序进入优先投递（评分至少 70）、未来七日即将截止和今日新增组；需要复核或证据字段不完整的记录进入需要确认组。同一岗位可以出现在多个行动组，缺失字段只显示缺失，不进行猜测。
- 新增确定性中文 Markdown 与转义后的独立 HTML 渲染。每条均包含单位、标题、地区、截止、规则理由、证据派生风险、评分和原文链接；四组始终保留，并在无内容时明确显示空组。
- 新增迁移 `0008_daily_report_snapshots`、对应 ORM 模型、规范输入/内容 SHA-256 标识及幂等 SQLAlchemy 服务。同日期/时区/版本/输入会复用不可变快照；同一标识若生成不同内容则显式失败。新增生成、结构化读取、Markdown 和 HTML API，未加入调度或推送行为。
- 新增构建器/渲染/API/模型/迁移/PostgreSQL 服务测试，并同步日报、数据库、索引双语文档。首轮静态检查发现 Ruff 歧义字符、导入及性能问题，以及递归 JSON 别名直接作为响应字段导致的 Pydantic 递归错误；均未使用抑制而是修正实现，API 通过非递归响应注解返回相同结构化对象。
- 无数据库门禁中，Ruff format 检查 187 个文件、Ruff lint 以及 126 个源文件的 Mypy 均通过。首次完整门禁尝试成功执行 238 项，并因 `JOBAGENT_TEST_DATABASE_URL` 不可用跳过 13 项 PostgreSQL 测试；覆盖率相应为 81.58%，低于 85%，因此 `scripts/check.py` 仍如实记为失败，不能作为验收通过。后续新增 `Asia/Shanghai` 本地零点和七日右开边界测试，非数据库通过项增至 239。
- Docker Desktop 4.85.0 已安装，但后端在启动任何引擎前崩溃。日志最初指向 Windows Unix socket 重解析点不可访问。已将易失的 `C:\Users\benbenhu\AppData\Local\Docker\run` 和 `C:\Users\benbenhu\AppData\Local\docker-secrets-engine` 目录改名为带 `.stale-20260903-*` 的备份并重启 Docker；未删除镜像、卷、项目数据或配置。新创建的 `dockerInference` 套接字仍发生相同故障，证明剩余阻塞属于 Docker Desktop/Windows 运行时，而非项目陈旧状态。5432 端口仍关闭，本机也没有独立 PostgreSQL 服务。
- JAI-024 尚未标记完成，验收框保持未勾选，实现也未提交或推送。JAI-025 评分评审、JAI-026 调度/锁和 JAI-027 通知/渠道逻辑仍在范围外。
- Windows 重启后，Docker Desktop 4.85.0 与现有 PostgreSQL 容器在未恢复出厂设置的情况下恢复，5432 端口上的数据库已健康。首次定向 PostgreSQL 测试中迁移/模型检查通过，但一项日报服务断言失败：测试假定持久化的人工确认原因总在风险数组首项，而既定确定性顺序会先放复核状态。断言已改为要求完整风险集合中存在该原因；没有修改生产排序或放宽验收。
- 修正后的 PostgreSQL 迁移/模型/日报服务定向测试 7/7 通过。首次完整门禁随后在 Ruff format 停止，因为修正后的生成式断言需要规范化为单行；`ruff format` 只执行了这一项机械调整。
- 最终启用 PostgreSQL 的 `scripts/check.py` 通过：Ruff format 检查 187 个文件、Ruff lint 通过、126 个源文件的 Mypy 通过、252 项测试全部通过且无跳过，覆盖率 88.53%。JAI-024 双语验收完成，未实现 JAI-025、JAI-026 或 JAI-027 行为。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建范围明确的功能提交 `ffa065f2877c833b5b98e48640a61aa891a0bb4f`，并普通推送新分支。本状态记录提交前，本地 HEAD、跟踪引用和 GitHub `ls-remote` 均与该提交一致；未使用 force push、rebase，未修改远程地址或已发布历史。
- 已创建配对的验收/推送状态提交 `1e60ee9`。首次普通推送及一次原样重试均因 GitHub 443 端口不可达而失败；直接 TCP 探测为 false，`ls-remote` 同样失败。已发布功能末端仍安全保持 `ffa065f`，本地仅领先状态文档，没有修改远端状态或改写历史。
- 随后的只读诊断发现 Windows 已在 `127.0.0.1:7892` 启用并运行本地代理，而 Git 没有仓库级/全局代理，之前一直使用失败的直连路径。仅对单次命令使用该现有用户代理作为 `http.proxy`，未持久化配置，也未改变 HTTPS origin。普通推送成功；本最终状态记录提交前，本地 HEAD、跟踪引用和 GitHub `ls-remote` 均为 `b1724881668540e6ec18b684079387c33d977b66`。
- 下一步：保持 JAI-024 独立且不变，直至 JAI-021、JAI-022、JAI-023 依次集成；随后把最新 `develop` 普通合并到 JAI-024，保留双方日志、显式解决双语文档冲突，并在集成前重跑 PostgreSQL 完整门禁。

### 2026-08-26 — JAI-021 来源 4、5 与三日稳定性验证启动

- 已重新核验干净的 JAI-020 feature 分支为 `9c86cad8eb621b20fa70e1e6a07a377f929608a3`；本地 HEAD、跟踪引用与 GitHub 引用一致，仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 已用非快进合并 `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5` 把 JAI-020 纳入 `develop`，完成普通推送，并核验本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为该提交。
- 已确认两种语言的计划与 Backlog 中下一项未完成 Issue 都是 JAI-021，并从同步后的 `develop` HEAD 创建 `feature/jai-021-sources-four-five-stability`。
- 范围仅限接入来源 4、5、使全部 5 个来源具备 Adapter 契约测试，并连续三个自然日记录成功率、重复率和核心字段完整率。优先来源为国家大学生就业服务平台与上海市事业单位公开招聘；只使用稳定、公开、只读的官方入口。
- 若动态页面要求登录、验证码、进入报名系统、浏览器自动化或规避访问控制，则明确标记阻塞，或改用同一官方主体的稳定入口。不会提前加入 JAI-022 匹配/偏好或后续调度运维功能。
- 三日验收期不能预先登记。下一步：检查现有目录和 Adapter 契约，核验官方公开入口，实现离线样本/契约及相称测试；仅在真实的有界运行成功后登记第 1 日。
- 已通过低频只读访问核验官方公开边界。NCSS 提供公开页面自身使用的免登录 GET 列表及公开详情；登录提示只属于投递动作，Adapter 不会调用。上海人社提供更精确的事业单位专栏；Adapter 只接受招聘公告路径并排除拟聘公示。
- 已新增 `NcssJobsAdapter`、`ShanghaiPublicInstitutionAdapter`、显式手工/预览运行时注册、活动目录配置，以及每站三份手工构造的合成详情契约。没有下载页面、凭据、求职者数据或运行输出进入提交。
- 已新增只输出 JSON 的有界每日评估，统计来源/详情成功率、规范 URL/内容指纹重复率，以及有证据的单位/标题/地区/截止时间/来源链接完整率。命令并发为 1，复用共享限速/重试策略，每站限 1～10 条，不写数据库或文件。
- 日期规则只为直接有证据的官方公告格式扩展：支持冒号或“为”、值位于下一行，以及“即日起”/“自公告发布之日起”后的唯一明确截止日期；相对开始时间仍保持为空。上海单位只取精确标题固定招聘后缀之前的文本，并保留标题证据。
- 2026-08-26 首次全来源观测不是合格稳定日：国资委来源因可重试 `PoolTimeout` 三次重试耗尽；5 个来源中 4 个成功，8 条尝试详情全部成功，重复率 0%，修正规则前完整率 55%。诊断复跑为 NCSS 80%、江苏 60%、修正后上海 100%；修正后可比组合为 82.5%，但并非一次完整全来源运行。
- 已按 JAI-021 验收登记明确整改 Issue JAI-049。该 Issue 禁止把发布时间当截止时间或把发布机构当招聘单位，必须在 MVP 发布闸门前处理有证据完整率差距；JAI-021 后主线下一功能仍为 JAI-022。
- Adapter/抽取/稳定性定向测试通过，PostgreSQL JAI-021 验收通过：来源 4/5 的 6 份合成文档首次写入均为 `created`，第二次均为 `unchanged`，最终仍为 6 条版本 1 记录。首次数据库调用使用了过时示例口令并认证失败；改用仓库登记的 `jobagent-dev-only` 测试 URL 后通过。新测试 docstring 的一处 Ruff EN DASH 问题也已修正。
- 首次启用 PostgreSQL 的完整门禁中 Ruff format/lint 通过，但在测试里的一个 `JsonValue` Mypy 类型缩窄问题处停止。增加显式字符串检查后，最终 `scripts/check.py` 通过：Ruff format 检查 168 个文件，Ruff lint 通过，110 个源文件的 Mypy 通过，238 项测试全部通过、无跳过，覆盖率为 87.79%。
- JAI-021 实质修改了存量中文来源网站库，因此仓库规则要求在同一提交补齐英文版本。已新增 `docs/en-US/SOURCE_CATALOG.md`，同步五来源状态和当前环境限制，更新两份索引，并仅把该文档从有边界的 JAI-048 清单移除；没有混入其他存量迁移。
- 文档核验确认 54 份 Markdown 无失效相对链接；开发计划标题 45/45、Backlog 71/71、活动日志 34/34、索引 5/5、稳定性指南 7/7、来源网站库 6/6。两份 Backlog 的 168 个 Issue ID 顺序一致，且 `git diff --check` 通过。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建实现基线提交 `52d435f35b8fb2a7ac013ac3f7d783261a97e0e5`，并普通推送新 feature 分支。在本次仅状态交接更新之前，本地 HEAD、跟踪引用与 GitHub `ls-remote` 均为该提交，工作区干净。由于尚未形成连续三个合格自然日，JAI-021 仍为进行中。
- 已创建仅状态的双语交接提交 `da2d3c68f47a012177be1fdd9d5311c5baa32e8d`。随后两次保持不变的普通 HTTPS 推送均因 GitHub 443 端口约 21 秒后仍无法连接而失败；直接只读 TCP 探测也返回 `TcpTestSucceeded=False`。远程 URL、协议、分支历史和提交均未改变；连通性恢复后重试同一非强制推送。
- 最后一次 TCP 探测返回 `True`；随后保持不变的普通 HTTPS 推送成功发布至故障记录提交 `5d67be09bc294d15af325c9279446a40ed7bfa81`。在本次最终仅状态更新之前，本地 HEAD、跟踪引用与 GitHub `ls-remote` 均为该提交，工作区干净。
- 已普通推送最终基线状态提交 `a2e3a15da994c97439d449b4be54a3248f236267`，并核验本地 HEAD、跟踪引用与 GitHub `ls-remote` 一致。后续同日有界全来源复观测仍不合格：国资委耗尽三次 `PoolTimeout` 重试，其余 4 个来源运行和全部 7 条尝试详情均成功；重复率为 0%，有证据完整率为 82.86%（29/35）。不保存正文的 IPv4 `curl` 诊断也在约 21 秒后无法连接国资委官方 443 端口并返回 HTTP `000`；用户另行确认普通浏览器同样无法打开该公开 URL。这印证了来源/网络路径故障，而非仅限 Python 的解析器问题，因此未尝试修改解析器或规避访问控制。
- 已创建观测记录提交 `4efaf87a122c9a82e4e1378b9b3f4463b672e28e`。首次保持不变的普通 HTTPS 推送被远端连接重置，紧接着的只读 GitHub 443 端口探测返回 `False`。本地提交与工作区保持安全；没有改变远程 URL、协议或历史。
- 后续 443 端口探测仍返回 `False`，但有界的普通 Git HTTPS 重试成功发布至中断记录提交 `b3fa11a9e2ce8140fab90a71af37f28faf018ffa`。在本次最终仅状态更新之前，本地 HEAD、跟踪引用与 GitHub `ls-remote` 均为该提交，工作区干净。

### 2026-08-27 — JAI-021 阻塞来源替换

- 从干净的 `feature/jai-021-sources-four-five-stability` 分支 `24af39c9c3a6ad39caadef3d6afd2060418251ca` 继续；本地 HEAD、跟踪引用和 GitHub `ls-remote` 一致，仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 替换前的有界五来源观测再次仅在国资委处失败，三次可重试 `PoolTimeout` 均耗尽。5 个来源中 4 个成功，8 条尝试详情全部成功，重复率 0%，有证据完整率 80%（32/40）；该次运行不是合格稳定日。
- 用户授权在国资委仍不可用时替换来源。国资委准确路径是被搜索引擎收录的官方公开 URL，并非内网地址，但用户浏览器和项目环境仍无法访问；`www` CDN 路径无法建立 443 连接，官方 `wap` 域名又返回证书过期。未绕过 TLS 验证或访问控制。
- 以有界只读请求评估了无需登录的官方替代站。中国电信静态栏目、国家电网和中国石油在本机返回 HTTP 412，中国电信招聘门户依赖 JavaScript/digest 流程；中国移动官方公告页返回 HTTP 200，并声明包含近期公告的同域静态列表 JSON，详情壳也声明公开同域详情 JSON，因此选为第五个活动来源。
- 新增 `ChinaMobileRecruitmentAdapter`、运行时/预览注册、严格官方 URL 与纯数字 ID 校验、标题过滤、发布时间游标和纯 GET 列表/详情物化。Adapter 保留页面展示的机构、标题、发布时间、可见正文、附件和来源信息。公开详情脚本不展示内部 `text5`/`downTime` 值，因此只把它保留为元数据，绝不猜测为报名截止时间。
- 网站库升级至版本 3，将国资委标记为 `blocked` 并停用，启用中国移动；按照用户调整的优先级，把 JAI-041 有边界的公开公告范围吸收到 JAI-021。新增三组纯合成固定样本与契约/错误测试，同步目录和运行时测试，并把 JAI-021 PostgreSQL 验收扩展到 9 份公告。首次中国移动线上预览成功，同时暴露维护公告排除词过窄，已从 `系统升级` 修正为 `升级公告`；第二次预览首请求遇到瞬时 `PoolTimeout`，环境中没有代理变量，WinHTTP 为直接访问。
- 首次 PostgreSQL 验收因 Docker Desktop 未运行而停滞，已在不修改仓库数据的情况下中断。启动已有 Docker Desktop 且只启动既有 Compose `db` 服务后，`jobagent-db-1` 进入健康状态，9 份公告验收在 2.87 秒内通过。定向测试和 Mypy 通过；Ruff 报告的导出排序和全角冒号歧义已在不增加忽略规则的情况下修正，定向复跑通过。
- 首次替换后全来源运行中，4 个来源完全成功、详情成功 10/11；中国移动公告 `54614` 的公开正文只有一张同域图片且无可见文字，因而失败。新增合成回归测试，在不下载、不做 OCR 的前提下保留经过校验的图片 URL 作为证据。该测试初版因 HTML 引号未转义而生成无效 JSON，并触发一处 Ruff 全角冒号问题；改为结构化构造 JSON 后，17 项定向测试、Ruff 和 Mypy 全部通过。
- 后续一次全来源运行又因中国移动列表瞬时耗尽三次 `PoolTimeout` 重试而只有 4 个来源完全成功。最后一次有界复跑成为合格第 1 日：来源运行 5/5、尝试详情 11/11 全部成功，重复率 0%，有证据完整率 78.18%（43/55）。完整率差距继续明确交给 JAI-049；未虚构缺失的单位、地区或截止时间。
- 纯图片修复后的首次完整门禁立即停在 Ruff format：新回归测试的两处断言需要自动换行。只格式化该文件后问题消失；最终启用 PostgreSQL 的 `scripts/check.py` 通过 Ruff format/lint、112 个源文件的 Mypy、全部 246 项测试且无跳过，覆盖率 87.45%。
- 文档核验确认 55 份 Markdown 没有失效相对链接。首次只读链接检查未处理根目录文件的空父路径，因而输出 `Join-Path` 错误；把其父路径按 `.` 处理后命令通过。开发计划标题 45/45、Backlog 71/71、活动日志 35/35、稳定性指南 7/7、采集指南 11/11、来源网站库 6/6、索引 5/5；两份 Backlog 的 172 个 Issue 引用顺序一致，`git diff --check` 通过。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建替代来源实现提交 `ea690a40cfc02d149d08776dcd23774808eda643`。首次普通 HTTPS 推送被远端连接重置；紧接着的只读 `ls-remote` 与第二次保持不变的普通推送都在约 21 秒后无法连接 GitHub 443。提交与工作区保持安全；未改变远程地址、协议、历史或作者。
- 已创建双语故障记录提交 `0f9102692735bd9995fd8244a6fb844ef208063e`。第三次对保持不变分支的普通 HTTPS 推送仍在约 21 秒后无法连接 GitHub 443。本地 HEAD 比未变化的跟踪引用 `24af39c9c3a6ad39caadef3d6afd2060418251ca` 领先 2 个提交；两个新提交均保留配置的用户作者。
- 后续从本地 HEAD `550d7629bd28e23b446eda21878d6b23dcfc45b6` 发起的第四次普通推送仍失败在相同的 GitHub 443 边界。只读诊断确认没有 Git 代理、代理环境变量、WinHTTP 代理或已启用的 Windows 用户代理；DNS 将 `github.com` 解析为 `20.205.243.166`，但 TCP 443 连接失败。继续直连重试需要外部网络路径变化；仓库配置保持不变。
- 用户恢复可用的外部网络路径后，保持不变的普通 HTTPS 推送成功发布至网络诊断提交 `6d30ad909e8af6c7947a4db7188d2081c22a9d75`，本地 HEAD 与跟踪引用立即一致。首次沙箱内 `ls-remote` 因其隔离网络路径在 11 毫秒后失败；随后在与推送相同的外部网络环境中执行只读核验成功，确认 GitHub 也为同一提交。
- 下一步：2026-08-28 起继续替换后五来源的第 2、3 日观测；连续三个合格自然日齐全前不得关闭 JAI-021。

### 2026-08-29 — JAI-021 稳定性序列重新开始

- 从干净的 `feature/jai-021-sources-four-five-stability` 分支 `a6bdcfbe3e96c3ab7d1257873aacf2749f8a1c04` 继续；本地 HEAD 与跟踪引用一致，仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 2026-08-28 没有登记有证据的真实运行，因此 2026-08-27 的合格结果不能补录或延续为连续序列。
- 2026-08-29 的有界替换观测合格：5 个来源运行和 8 条尝试详情全部成功，重复率 0%，有证据完整率 80%（32/40）。NCSS 与 Firstjob 返回有效空列表；江苏、上海事业单位和中国移动分别返回 2、3、3 条详情。未写数据库、运行文件或来源正文。
- 连续序列于 2026-08-29 重新从第 1 日开始。下一步：在 2026-08-30、2026-08-31 分别登记合格运行；任何缺失或失败日都会再次重置序列。
- 用户明确批准 JAI-021 仅剩验收观测期间并行开发 JAI-022。已确认 JAI-020 确实位于 `develop`：本地与跟踪 `develop` 均指向非快进合并 `f56365f9fabe1d6ee49e67fb5fc1f56350cb8ac5`，其第二父提交为 JAI-020 最终 feature 提交 `9c86cad8eb621b20fa70e1e6a07a377f929608a3`。活动分支的状态表已经写明合并提交；用户在较旧 `develop` 副本中看到的是 JAI-021 之前的措辞，JAI-021 合并时会带入澄清后的表格。
- 本次对 GitHub `develop` 的实时 `ls-remote` 复核遇到已知的间歇性 443 超时；创建分支前必须成功重试。版本控制边界：JAI-022 只能从三端核验一致的 `develop` 创建；JAI-021 观测继续留在现有分支；先将 JAI-021 合并到 `develop`，再把更新后的 `develop` 普通合并到 JAI-022，保留两份双语 WORKLOG 历史并重跑完整门禁。不会 rebase 或改写已发布历史。

### 2026-08-30 — JAI-021 稳定性合格第 2 日

- 从干净且已推送的 JAI-022 启动分支切回 `feature/jai-021-sources-four-five-stability`；没有任何 JAI-022 提交或文件改动进入本分支。
- 有界只读观测合格：5 个来源运行和 9 条尝试详情全部成功，重复率 0%，有证据完整率 80%（36/45）。Firstjob 返回有效空列表；NCSS、江苏、上海事业单位和中国移动分别返回 1、2、3、3 条详情。未写数据库、运行文件或线上来源正文。
- 当前序列包含 2026-08-29 合格第 1 日和 2026-08-30 合格第 2 日。下一步：2026-08-31 执行同一有界观测；只有全来源成功才完成 JAI-021 验收。

### 2026-08-30 — JAI-021 并行核验通道准备

- 用户明确批准把 JAI-021 剩余核验与后续开发任务并行推进，前提是记录完整并保持版本控制隔离。本通道现使用独立 worktree `data/worktrees/jai021` 和 `feature/jai-021-sources-four-five-stability`；没有携带任何 JAI-022/JAI-023 提交或文件改动。
- 实际 `Asia/Shanghai` 时间为 `2026-08-30 11:47`。今日已经登记第 2 日，因此没有执行或把同日重复运行计为第 3 日；最早有效的第 3 日观测仍是 2026-08-31。
- 已复用主仓库现有 `.venv` 和本 worktree 的 `src` 完成离线准备：NCSS、上海事业单位、中国移动、稳定性指标、运行时和网站库共 32 项测试在 2.11 秒内全部通过。命令帮助退出码为 0，`--limit 0` 被以退出码 2 拒绝，确认限制为 1～10。检查没有访问线上来源、数据库，也没有写运行文件或来源正文。
- 本 worktree 在 2026-08-31 的准确命令为：

  ```powershell
  $env:PYTHONPATH = 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\src'
  & 'F:\CXG\JOBAGENTV1.0\.venv\Scripts\python.exe' 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\scripts\evaluate_source_stability.py' --catalog 'F:\CXG\JOBAGENTV1.0\data\worktrees\jai021\config\source_catalog.toml' --limit 3
  ```

- 观测仍严格限定为 5 个 `active`/`enabled` 的公开官方来源、并发 1、共享限速/重试、仅 GET 访问和 JSON 标准输出；不得进入登录、验证码、简历/投递流程，不得写数据库/文件或留存线上来源正文。
- 合格第 3 日要求 `observation_date=2026-08-31`、5/5 来源全部成功且所有尝试详情无失败；重复率必须保持在 MVP 上限 2% 以内。有证据完整率只做真实记录、不猜测补值；85% 目标或已经登记的 JAI-049 整改路径仍是文档约定的验收二选一条件。
- 合并顺序固定：完成 JAI-021 与最终门禁后，先把 JAI-021 合并到 `develop`；此后 JAI-022/JAI-023 才能通过普通合并同步最新 `develop`，保留两边双语 WORKLOG 历史、解决配对文档冲突，并在后续合并到 `develop` 前重跑各自完整门禁。继续禁止 rebase、force push 和改写已发布历史。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建仅含准备记录的提交 `dee0632`。首次保持不变的普通 HTTPS 推送在约 21 秒后因 GitHub 443 不可达而失败；只读 `Test-NetConnection` 把 `github.com` 解析为 `20.205.243.166`，但返回 `TcpTestSucceeded=False`。本地提交保持安全，远程 URL、协议、分支历史和作者均未改变。
- 后续保持不变的普通推送已经成功。本地 HEAD、跟踪引用和 GitHub `ls-remote` 均为阻塞记录末端 `00de7d1423482d99695a1de99dd451dd79c93f85`；JAI-022 与 JAI-023 继续隔离在各自 worktree。

### 2026-09-03 — JAI-021 稳定性序列重新开始

- 从干净且已推送的 JAI-021 worktree `05f41406693f9d659dc53550b31102f1e0ddd2e8` 继续；JAI-022 与 JAI-023 仍相互隔离，没有下游提交进入本分支。仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 2026-08-31、2026-09-01 和 2026-09-02 均没有登记有证据的真实运行。因此 2026-08-29/30 的合格两日不能事后补全，连续序列从 2026-09-03 重新开始。
- 2026-09-03 的有界只读观测合格并记为新 Day 1：5/5 来源运行和 9/9 尝试详情全部成功，详情失败为 0，重复率 0%，有证据完整率 80%（36/45）。Firstjob 返回有效空列表；NCSS、江苏、上海事业单位和中国移动分别返回 1、2、3、3 条详情。
- 命令保持批准边界：每来源最多 3 条、并发 1、共享限速/重试、仅访问公开官方端点、只输出 JSON，不写数据库、文件或线上来源正文。缺失的截止时间、单位和地区继续保持为空，不猜测补值。
- 应用户要求，在同一 2026-09-03 自然日再次执行有界观测。5/5 来源运行及 9/9 尝试详情再次全部成功，失败为 0、重复为 0、有证据完整率为 80%（36/45）；来源数量仍为 NCSS 1、Firstjob 0、江苏 2、上海事业单位 3、中国移动 3。该次仅登记为同日可重复性补充证据，不会把序列推进到 Day 2。
- 配对观测记录更新后，32 项定向离线 Adapter、稳定性指标、运行时和目录测试在 1.68 秒内通过；双语标题一致性与 `git diff --check` 也通过。
- 下一次合格运行必须分别在 2026-09-04 和 2026-09-05 完成。任何自然日缺失或失败都会再次重置序列；完整序列和最终门禁完成前不合并 JAI-021。

### 2026-09-04 — JAI-021 稳定性合格第 2 日

- 从已推送的观测记录提交 `816bee92d09d6f080e7e705e6ee75f5f2cc83ac5` 干净继续；运行前本地 HEAD 与跟踪引用一致，没有下游分支改动进入本 worktree。
- 有界只读观测合格：5/5 来源运行与 9/9 尝试详情全部成功，详情失败为 0、重复率为 0%、有证据完整率为 80%（36/45）。Firstjob 返回有效空列表；NCSS、江苏、上海事业单位和中国移动分别返回 1、2、3、3 条详情。
- 32 项定向离线 Adapter、稳定性指标、运行时和目录测试在 1.67 秒内通过；配对 WORKLOG/稳定性指南标题一致，`git diff --check` 通过。
- 当前连续序列为 2026-09-03 Day 1 加 2026-09-04 Day 2。2026-09-05 只执行一次相同有界观测；只有全部合格才能关闭 JAI-021 并启动最终门禁/合并工作。

### 2026-09-05 — JAI-021 稳定性观测失败

- 从干净的 JAI-021 worktree 提交 `94a0f7fba0c6630ae0cbaa80cdca9599e573abeb` 继续；运行前本地 HEAD 与跟踪引用一致，没有下游分支改动进入本 worktree。
- 有界只读观测未合格：由于中国移动公开公告入口在三次重试后仍发生可重试 `crawler.http_retry_exhausted` / `PoolTimeout`，仅 4/5 来源运行完成。其余四个来源完成；Firstjob 返回有效空列表，NCSS、江苏和上海事业单位分别产生 1、2、3 条详情。
- 6/6 尝试详情全部成功，重复率为 0%，有证据完整率为 86.67%（26/30）。命令继续遵守每来源最多三条、并发 1、仅公开 GET 的边界，且未持久化数据库、文件或来源正文。
- 该失败日中断 2026-09-03/04 合格两日序列。不通过同日再次运行挑选更好结果；下一次合格自然日观测重新计为 Day 1。
- 全仓 Markdown 相对链接检查通过。配对 WORKLOG、稳定性指南和计划的标题数分别一致为 41/41、7/7、45/45；两份 Backlog 的 Issue 编号顺序相同，`git diff --check` 通过。
- 使用仓库级作者 `user9527448 <2537759248@qq.com>` 创建观测记录提交 `8e5fbecac1a95d32d5ba79af84e88aaeb79fd7ba`。首次普通 HTTPS 推送因 GitHub 443 直连约 21 秒后超时失败；随后通过此前已验证的命令级临时代理 `127.0.0.1:7892` 原样推送成功，未修改 `origin` 或持久 Git 配置。本次网络状态更新前，本地 HEAD、跟踪引用与 GitHub `ls-remote` 均与该提交一致。

### 2026-09-05 — JAI-021 Day 3 豁免与合并火车授权

- 用户明确判断单独的中国移动超时大概率属于链接或外部网络链路异常，而不是爬虫缺陷，并接受已记录的 2026-09-05 运行作为 Day 3。该来源继续监测；本决策不改变实际 4/5 来源成功、三次重试耗尽或错误分类。
- 因此，JAI-021 通过有文档记录的产品负责人例外，以 2026-09-03 至 2026-09-05 三日记录完成验收。用户授权按既定 JAI-021 → JAI-022 → JAI-023 → JAI-024 顺序执行安全合并火车。
- 每次合并前使用普通 merge 将最新 `develop` 同步进对应 feature 分支，保留双方双语 WORKLOG 历史，一致处理配对文档冲突，并重新运行完整且相称的门禁。禁止 rebase、force push、改写已发布提交或更改作者。
- PostgreSQL 启用的最终 `scripts/check.py` 通过：Ruff format 检查 173 个文件，Ruff lint 通过，Mypy 检查 112 个源文件通过，246 项测试全部通过且无跳过，覆盖率为 87.45%。

### 2026-09-05 — JAI-021 合并后同步 JAI-022

- JAI-021 已通过非快进提交 `8cc0b2eb37b5ec7e2c560ce35b687a687da47b43` 合入 `develop`；合并后启用 PostgreSQL 的完整门禁以 246 项测试、无跳过和 87.45% 覆盖率通过。同步前本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致。
- 已将最新 `develop` 普通合并进 JAI-022。代码无冲突；预期冲突仅限配对计划、Backlog、索引和 WORKLOG。解决结果保留双方 Issue 历史、JAI-021 Day 3 的实际指标/豁免以及完整 JAI-022 实现记录。
- 双语标题一致性、Backlog Issue 编号顺序、Markdown 相对链接和 `git diff --check` 均通过。启用 PostgreSQL 的组合 `scripts/check.py` 通过：Ruff format 检查 183 个文件，Ruff lint 通过，Mypy 检查 119 个源文件通过，254 项测试全部通过且无跳过，覆盖率 87.57%。
- 下一步：提交并普通推送同步结果，再将 JAI-022 合入 `develop`。

### 2026-09-05 — JAI-022 合并后同步 JAI-023

- JAI-022 已通过非快进提交 `e7948c9225fba32e499786cc8400cf0dd975e4ca` 合入 `develop`；合并后启用 PostgreSQL 的完整门禁以 254 项测试、无跳过和 87.57% 覆盖率通过。同步前本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致。
- 已将最新 `develop` 普通合并进 JAI-023。代码与迁移无冲突；预期冲突仅限配对计划、Backlog、索引和 WORKLOG。解决结果保留 JAI-021、JAI-022、JAI-023 全部历史以及 Day 3 豁免的实际指标。
- 双语标题一致性、Backlog Issue 编号顺序、Markdown 相对链接和 `git diff --check` 均通过。启用 PostgreSQL 的组合 `scripts/check.py` 通过：Ruff format 检查 193 个文件，Ruff lint 通过，Mypy 检查 126 个源文件通过，271 项测试全部通过且无跳过，覆盖率 87.86%。
- 下一步：提交并普通推送，再将 JAI-023 合入 `develop`。

### 2026-09-05 — JAI-023 合并后同步 JAI-024

- JAI-023 已通过非快进提交 `5935b5206a933e8a14cb80b0421ed90f1a0e336c` 合入 `develop`；合并后启用 PostgreSQL 的完整门禁以 271 项测试、无跳过和 87.86% 覆盖率通过。同步前本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 一致。
- 已将最新 `develop` 普通合并进 JAI-024。代码、迁移与 Backlog 无冲突；预期冲突仅限配对计划、索引和 WORKLOG。解决结果保留 JAI-021 至 JAI-024 全部历史以及 Day 3 豁免的实际指标。
- 双语标题一致性、Backlog Issue 编号顺序、Markdown 相对链接和 `git diff --check` 均通过。启用 PostgreSQL 的组合 `scripts/check.py` 通过：Ruff format 检查 206 个文件，Ruff lint 通过，Mypy 检查 136 个源文件通过，282 项测试全部通过且无跳过，覆盖率 87.96%。
- 下一步：提交并普通推送，再将 JAI-024 合入 `develop`。

### 2026-09-05 — 合并火车完成并启动 JAI-025

- JAI-024 同步末端 `11551331a403942d9b78c758997c6ae7536a94e7` 已普通推送，随后通过非快进提交 `0aa6b233ea8216aecdbe1d1dce4031ad6884a442` 合入 `develop`。
- 合并后启用 PostgreSQL 的完整门禁通过：Ruff format 检查 206 个文件，Ruff lint 通过，Mypy 检查 136 个源文件通过，282 项测试全部通过且无跳过，覆盖率 87.96%。本地 `develop`、`origin/develop` 与 GitHub `ls-remote` 均为 `0aa6b233ea8216aecdbe1d1dce4031ad6884a442`；JAI-021 至 JAI-024 最终 feature 末端的祖先检查全部通过。
- 已核验两份 Backlog 均把 JAI-025 列为下一项未完成计划 Issue，随后从三端一致的 `develop` 基线创建 `feature/jai-025-top-20-quality-review`。仓库本地作者仍为 `user9527448 <2537759248@qq.com>`。
- 范围仅限至少 50 条脱敏、可人工复核的相关性标注，确定性 Top 20/漏召回分析，不变的 v1 基线，显式新评分版本，前后对比证据及 MVP 局限说明。JAI-026 调度和 JAI-027 通知行为继续保持范围外。
- 下一步：实现离线质量评审契约与固定样本，分类误推荐/漏召回，只调整新评分版本，并在完整 PostgreSQL 门禁前先运行定向测试。

### 2026-09-05 — JAI-025 评估实现与验收边界

- 新增离线质量评审契约、严格 JSON 加载器、稳定 Top-K 评估器、JSON 命令，以及 60 条完全合成/脱敏、带显式分类与依据的拟议标注。产物明确标记为等待项目负责人复核的“拟议”状态，没有把它描述成历史人工标注数据。
- 保留 `jai-023-v1` 作为可支持的重放基线，并新增候选版本 `jai-025-v2`。V2 提高直接岗位方向/专业权重，降低紧迫度/完整度权重；仅在要求正文出现的词不参与正向方向评分，但要求正文仍参与排除词硬过滤。
- 在拟议固定集上，v1 的 Top 20 有 15 个真阳性、5 个 `requirements_context_false_positive` 误推荐和 15 个漏召回（Precision@20 为 0.75，Recall@20 为 0.50）。V2 有 20 个真阳性、无 Top 20 误推荐，并显式保留 10 个漏召回（Precision@20 为 1.00，Recall@20 为 0.666667）。
- 首轮定向检查暴露一个 `__all__` 插入位置错误，以及三处需要明确更新为 v2 数值的 v1 预期；修正后定向 Ruff、Mypy 通过，22 项匹配测试全部通过。这是本地实现检查，不是生产故障。
- 启用 PostgreSQL 的完整 `scripts/check.py` 通过：Ruff format 检查 213 个文件，Ruff lint 通过，Mypy 检查 139 个源文件通过，288 项测试全部通过且无跳过，覆盖率 87.77%。`git diff --check` 也通过。
- 只读核对现有本地开发数据库得到 `raw_documents=0`、`job_posts=0`、`job_positions=0`；该库也尚未应用 JAI-023 的 `match_results` 迁移。因此本地没有 50 条真实历史岗位，不能基于当前数据如实声称已完成本 Issue 的历史/人工标注验收。
- 已使用仓库本地作者 `user9527448 <2537759248@qq.com>` 创建评审准备提交 `4fe0274cdc2fadbfe50c71086771fb50c0522a4b`，并通过已验证的命令级临时代理普通推送 feature 分支，未修改 `origin` 或持久 Git 设置。推送后本地 HEAD、跟踪引用与 GitHub `ls-remote` 均与该提交一致。
- 下一步：取得项目负责人对“是否接受 60 条脱敏拟议标注作为范围替代”的显式决定。如果没有该计划变更，也没有提供/写入带人工标注的历史样本，JAI-025 保持未完成且不得合入 `develop`。

## 4. 检查与阻塞

- JAI-046 最终门禁：Ruff format/lint 通过；56 个源文件的 Mypy 通过；PostgreSQL 启用时 89 项测试全部通过；覆盖率 88.35%。
- JAI-046 推送核验：本地 `develop`、`origin/develop` 与 `git ls-remote --heads origin develop` 均为 `f07b6d50ed9abda08d38883eefa3904b98b99455`。
- 推送前一次只读 GitHub 检查遇到临时 443 故障；后续普通推送和显式 `ls-remote` 已成功。
- JAI-047 检查完成：35 份 Markdown 无失效相对链接；双语标题与 Issue 编号一致；`git diff --check`、Ruff format/lint、Mypy、89 项 PostgreSQL 启用测试和 88.35% 覆盖率全部通过。
- 推送前格式修正：已删除 `docs/en-US/DEVELOPMENT_PLAN.md` 暂存检查发现的 4 行行尾空格；推送前必须确认最终暂存区和工作区差异检查均通过。
- JAI-012 最终门禁：Ruff format/lint 通过；62 个源文件的 Mypy 通过；PostgreSQL 启用时 105 项测试通过；覆盖率 88.38%。离线 JAI-012 验收未访问线上来源，也未在仓库留下运行数据。
- 2026-08-15 的 JAI-012 交接复查中，首次 Mypy 命令误用了计划中的非现存 `app` 目录，随后改为仓库配置目标；首次测试未设置 `JOBAGENT_TEST_DATABASE_URL`，因此 98 项通过、7 项 PostgreSQL 测试跳过，覆盖率仅 83.18%。启动现有 Docker Desktop 并使用既有 `jobagent_test` 数据库后，Ruff format/lint、Mypy、全部 105 项测试和 88.38% 覆盖率均通过。

## 5. 下一步

1. 完成 JAI-025 固定评审集、Top 20/漏召回对比、评分版本更新及双语局限说明。
2. 先运行定向匹配质量测试，再运行启用 PostgreSQL 的完整门禁；随后提交、普通推送，并在安全集成前核验三端引用。
3. JAI-026 调度、JAI-027 通知、OCR/JAI-B01、JAI-049 与 JAI-048 均保持在当前 Issue 范围外。

## 6. 更新模板

```markdown
### YYYY-MM-DD — JAI-XXX 标题

- 状态/分支：
- 完成工作：
- 决策/偏离：
- 检查：
- 阻塞/用户操作：
- 下一步：
```
