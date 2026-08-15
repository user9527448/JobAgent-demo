# JOBAGENT 持续开发工作日志

> 语言：简体中文。英文镜像：[`../WORKLOG.md`](../WORKLOG.md)。
>
> 截至 JAI-046 的原中英文混合历史已逐字节保存在
> [`../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md`](../archive/WORKLOG-LEGACY-THROUGH-JAI-046.md)，
> SHA-256 为 `E9CB9D3652A065491F5C88D3D24610A0593B6079AA49353A912F8B40B9E9A0F7`。
>
> 最后更新：2026-08-15
>
> 当前分支：`feature/jai-012-run-stats-retry`

## 1. 当前状态

| Issue | 状态 | 分支 / 提交 | 说明 |
|---|---|---|---|
| JAI-001 至 JAI-010 | 完成，已合并到 `develop` | 见历史归档 | 工程基线、采集框架、原始公告版本化和附件存储 |
| JAI-036 | 完成，已合并到 `develop` | `develop` / `82adb73` | 首批简体中文镜像和双语导航 |
| JAI-011 | 完成，已合并到 `develop` | `develop` / `368c369` | 三个官方来源 Adapter、固定样本、持久化和幂等验收 |
| JAI-037 | 完成，已合并到 `develop` | `develop` / `c649862` | 官方来源扩展路线、外企候选和参考来源边界 |
| JAI-046 | 完成，已合并并推送到 `develop` | `develop` / `f07b6d5` | 独立双语文件规则和仓库级 Git 作者身份规则 |
| JAI-047 | 完成，已合并并推送到 `develop` | `develop` / `87cd753` | 存量迁移基线、独立双语工作日志和 JAI-048 清单 |
| JAI-012 | 已完成并推送 feature 分支，待合并到 `develop` | `feature/jai-012-run-stats-retry` / 实现提交 `7e5e888` | 手动运行、持久化计数、运行摘要和只重跑失败 URL 的幂等验收已通过 |

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

## 4. 检查与阻塞

- JAI-046 最终门禁：Ruff format/lint 通过；56 个源文件的 Mypy 通过；PostgreSQL 启用时 89 项测试全部通过；覆盖率 88.35%。
- JAI-046 推送核验：本地 `develop`、`origin/develop` 与 `git ls-remote --heads origin develop` 均为 `f07b6d50ed9abda08d38883eefa3904b98b99455`。
- 推送前一次只读 GitHub 检查遇到临时 443 故障；后续普通推送和显式 `ls-remote` 已成功。
- JAI-047 检查完成：35 份 Markdown 无失效相对链接；双语标题与 Issue 编号一致；`git diff --check`、Ruff format/lint、Mypy、89 项 PostgreSQL 启用测试和 88.35% 覆盖率全部通过。
- 推送前格式修正：已删除 `docs/en-US/DEVELOPMENT_PLAN.md` 暂存检查发现的 4 行行尾空格；推送前必须确认最终暂存区和工作区差异检查均通过。
- JAI-012 最终门禁：Ruff format/lint 通过；62 个源文件的 Mypy 通过；PostgreSQL 启用时 105 项测试通过；覆盖率 88.38%。离线 JAI-012 验收未访问线上来源，也未在仓库留下运行数据。
- 2026-08-15 的 JAI-012 交接复查中，首次 Mypy 命令误用了计划中的非现存 `app` 目录，随后改为仓库配置目标；首次测试未设置 `JOBAGENT_TEST_DATABASE_URL`，因此 98 项通过、7 项 PostgreSQL 测试跳过，覆盖率仅 83.18%。启动现有 Docker Desktop 并使用既有 `jobagent_test` 数据库后，Ruff format/lint、Mypy、全部 105 项测试和 88.38% 覆盖率均通过。

## 5. 下一步

1. 提交并普通推送本次 JAI-012 交接状态更新，再次核对本地、跟踪分支与 GitHub 分支哈希。
2. 把 JAI-012 合并到 `develop` 并普通推送，再从最新且已同步的 `develop` 开始 JAI-013。
3. 使用独立文档 Issue 执行 JAI-048；不得把大规模存量文档迁移混入功能开发。

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
