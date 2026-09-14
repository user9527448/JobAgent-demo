# JOBAGENT 产品界面设计规范

> English: [JOBAGENT Product UI Design Specification](../DESIGN.md)

## 1. 状态与范围

本文档是 JAI-050 的可版本控制视觉与交互权威，约束正式前端基底及首个只读**晨间简报**页面。
后续 UI Issue 可通过同步修改中英文文件扩展本规范，但不得静默替换其 token、证据规则或无障碍基线。

选定视觉参考为[晨间简报方案 1](../assets/jai-050/morning-briefing-reference.png)
（`1484x1060`，SHA-256 `09D55CFD2B5550E6D4D199004F690992DA90703B73AC38828808F94295AF8DE4`）。
它只定义构图和信息层级，不是业务事实来源。生成图中的日期、数量、公司、岗位和状态文案必须替换为
API 证据或明确空状态。

## 2. 产品结果与证据边界

首个页面帮助本地单用户在一分钟内回答三个问题：

1. 最新持久日报是什么，哪些机会值得关注？
2. 台账对最近流水线及各阶段证明了什么？
3. 固定每日作业下次何时计划执行，安全投递状态是什么？

JAI-050 只读，不包含运行、补跑、重试、发送、补发、来源启停、偏好写入或反馈写入。缺失台账行
必须显示为**无运行记录**，不得推断为成功、失败、取消或 misfire。页面必须区分 API 存活、数据库
就绪、scheduler 证据、流水线证据和投递能力。

## 3. 设计来源优先级

来源冲突时按以下顺序判断：

1. 后端持久证据、API 契约、测试及仓库安全规则。
2. 本双语 DESIGN 规范与选定参考的信息层级。
3. shadcn/ui 官方组件/主题契约，其次为 Tailwind CSS v4 主题变量契约。
4. 外部 DESIGN.md 示例只作为文档结构参考。

不得因参考图虚构指标、加入私有招聘数据、复制第三方品牌、引入外部 registry 代码、渐变、Emoji
图标或未批准交互。D-038 已明确批准 Lucide 图标；所有非装饰图标必须带文字标签。

## 4. 应用架构

- 根目录：`frontend/`，由 pnpm 管理并提交锁文件。
- 运行时：React、TypeScript、Vite，启用严格类型检查。
- 样式：Tailwind CSS v4 和语义 CSS 变量。
- 组件：仓库自有的 shadcn/ui 源码组件，使用 Radix primitives。
- 图标：Lucide React，统一使用 18～20 px 描边图标。
- 开发：Vite 只代理页面需要的窄 FastAPI 路由前缀。
- 生产：确定性前端构建复制到 Python 镜像，由既有 FastAPI 同源 `/app/` 提供；已登记客户端路由
  均回退到同一 `index.html`。
- 数据访问：一个页面级查询边界聚合只读看板证据；既有健康端点保持独立，使页面壳可安全显示
  数据库失败。

不引入独立前端部署、认证层、服务端渲染框架、设计 SaaS 运行时、分析 SDK 或客户端密钥。

## 5. 信息架构与响应式布局

桌面页面遵循选定的编辑式布局：

- 68 px 应用页眉：产品名、基于证据的健康摘要与本地时间。
- 196 px 左侧导航。JAI-050 只有**晨间简报**是活动路由；未来项目可标注“计划中”，但不得表现为
  已完成页面。
- 自适应主阅读列：参考视口下约 760～860 px，包含页面标题、最新日报身份、执行摘要、指标条和
  推荐列表。
- 340～360 px 证据栏：下次计划、缺失记录证据、最近流水线阶段及投递能力/状态。

响应式行为必须保留内容语义：

- `>= 1280px`：完整页眉、导航、阅读列和证据栏。
- `768px–1279px`：收窄导航；证据栏移到日报之后，语义不变。
- `< 768px`：单列、键盘可操作导航 Sheet、纵向指标及可换行推荐元数据；页面不得横向滚动。

页面最大内容宽度 1484 px，桌面边距 24～32 px，窄屏边距 16 px，并使用 8 px 间距网格。相关内容
优先通过排版和分隔线组织；不得仅为制造层级嵌套卡片。

## 6. 视觉 token

JAI-050 只提供默认浅色主题。token 使用 shadcn/ui 语义命名，组件通过 Tailwind 工具类消费，不在
组件内部写原始颜色值。

```css
:root {
  --background: oklch(0.985 0.004 250);
  --foreground: oklch(0.205 0.035 255);
  --card: oklch(1 0 0);
  --card-foreground: var(--foreground);
  --popover: oklch(1 0 0);
  --popover-foreground: var(--foreground);
  --primary: oklch(0.56 0.16 250);
  --primary-foreground: oklch(0.985 0.005 250);
  --secondary: oklch(0.955 0.018 245);
  --secondary-foreground: oklch(0.31 0.055 250);
  --muted: oklch(0.96 0.009 250);
  --muted-foreground: oklch(0.52 0.035 255);
  --accent: oklch(0.94 0.03 245);
  --accent-foreground: oklch(0.32 0.08 250);
  --destructive: oklch(0.58 0.21 25);
  --border: oklch(0.90 0.012 250);
  --input: var(--border);
  --ring: oklch(0.63 0.15 250);
  --evidence: oklch(0.53 0.105 205);
  --attention: oklch(0.72 0.15 72);
  --success: oklch(0.62 0.15 155);
  --radius: 0.625rem;
}
```

字体采用系统优先栈 `Inter, "Noto Sans SC", "Microsoft YaHei", system-ui, sans-serif`，产品不得依赖
在线字体 CDN。正文 14～16 px，行高至少 1.5；桌面页标题 36～40 px，窄屏 30～32 px；数字证据使用
等宽数字。边框为 1 px，阴影少量且克制，禁止渐变。

## 7. 组件、内容与状态

围绕 shadcn/ui primitives 构建可复用页面组件：

- `AppShell`、`AppHeader`、`PrimaryNavigation` 定义长期布局。
- `ReportBriefing` 展示不可变快照 ID、报告日期、创建时间及从分组确定性生成的简短摘要。
- `ReportMetrics` 只统计持久条目，并准确标注每个数字的口径。
- `RecommendationList` 保留日报分组及条目顺序；每行包含单位、岗位、地区、截止、分数、理由、
  风险及存在时的安全原文链接。
- `ScheduleEvidence`、`LedgerGapNotice`、`PipelineStages`、`DeliveryEvidence` 组成证据栏。
- `StatusBadge` 把后端状态映射为文字加颜色/图标，不能只靠颜色表达含义。

每个数据区域都有四种明确状态：加载 Skeleton、空证据、安全摘要错误及已加载。空不等于错误。
JAI-027 G5 前投递表不存在时，显示**投递尚未启用 · 等待迁移/配置**，不得显示投递失败。原始异常、
provider payload、哈希、Token 和数据库 URL 绝不能进入页面。

## 8. 只读 API 契约

JAI-050 只使用以下 GET 边界：

- `GET /health/live`：既有进程存活端点。
- `GET /health/ready`：既有数据库就绪端点。
- `GET /dashboard/briefing`：有界聚合服务端时间/时区、固定作业存在性和下次执行时间、最多七条最近
  流水线及最新阶段尝试、最新不可变日报及有序条目、预计执行日中没有流水线台账的日期，以及所选
  日报的投递能力/状态。
- `GET /reports/daily/{snapshot_id}/html`：指向明确快照的既有持久 HTML 链接；看板不生成或修改日报。

`/dashboard/briefing` 必须返回稳定 Pydantic 响应、确定性排序数组、限制所有集合大小，并只暴露枚举
安全错误码。查询 JAI-027 投递表前先检查其是否存在，使当前 `0009_pipeline_scheduling` 业务库可
诚实展示迁移前状态。数据库查询失败映射为脱敏的 503 响应。

## 9. 无障碍与交互规则

- 使用 `header`、`nav`、`main` 和辅助证据栏 landmark，并且只有一个页面级 `h1`。
- 所有链接和 disclosure 控件支持键盘并显示清晰 `:focus-visible` 焦点环。
- 文字、表达状态的控件/边框及焦点指示满足 WCAG 2.2 AA 对比度。
- 尊重 reduced motion；JAI-050 不需要装饰动画，加载提示不得闪烁。
- 原文链接使用可理解名称及安全 `rel` 属性，明确打开。
- 200% 缩放下不丢失证据标签，也不要求双向滚动。

## 10. 验证与交付闸门

JAI-050 交付前必须：

1. 基于锁定依赖的前端 format、lint、严格类型、单元测试和生产构建通过。
2. FastAPI 单元/契约测试覆盖已加载、空、`0010` 前和数据库错误脱敏状态。
3. 既有 Python `scripts/check.py` 在 PostgreSQL 下通过且无跳过。
4. 浏览器检查覆盖参考视口（`1484x1060`）、1440 px 桌面、平板和窄手机宽度，并实际操作主导航及
   日报/原文链接。
5. Design QA 在相同视口比较参考与实现，修复全部 P0～P2，并在 Issue 自有 QA 报告中记录
   `final result: passed`。

JAI-050 不得先于 JAI-027 合入 `develop`。它不授权业务迁移 `0010`、凭据、真实 PushPlus 请求、
scheduler 重启、补跑、线上来源、JAI-028 试运行、JAI-051 反馈迁移或 JAI-029 发布。

## 11. 决策历史与参考

- D-038/U1-R 与堆叠分支顺序于 2026-09-14 获批。
- U2 选择方案 1 **晨间简报**作为正式视觉基线。
- [Google DESIGN.md 规范](https://github.com/google-labs-code/design.md/blob/main/docs/spec.md)
- [shadcn/ui 主题](https://ui.shadcn.com/docs/theming)
- [shadcn/ui Vite 安装](https://ui.shadcn.com/docs/installation/vite)
- [Tailwind CSS 主题变量](https://tailwindcss.com/docs/theme)
- [Tailwind CSS 响应式设计](https://tailwindcss.com/docs/responsive-design)

