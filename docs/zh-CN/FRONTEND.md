# JOBAGENT 前端基底

> English: [JOBAGENT Frontend Foundation](../FRONTEND.md)

## 范围

JAI-050 引入生产前端基底和首个只读 **今日简报** 页面。视觉权威为
[DESIGN.md](DESIGN.md)。该页面只读取持久化证据；不会启动、重试、补跑、发送、补发、配置或编辑任何内容。

## 技术栈与目录

- `frontend/`：React、严格 TypeScript、Vite、Tailwind CSS v4、仓库自有的 shadcn/ui 风格组件、
  Radix primitives 和 Lucide 图标。
- `src/jobagent/dashboard/`：有界只读证据聚合。
- `GET /dashboard/briefing`：稳定的页面级契约。
- `src/jobagent/api/frontend.py`：同源 `/app/` 外壳与静态资源托管。

已提交的 `pnpm-lock.yaml` 是依赖权威。不得提交 `node_modules`、`dist`、Vite 缓存、pnpm store、
运行时 API 响应或包含业务数据的截图。

## 本地开发

复用仓库已有 Python 环境，并单独在 8000 端口启动 API。然后执行：

```powershell
Set-Location frontend
pnpm install --frozen-lockfile
pnpm dev
```

Vite 在 `/app/` 提供页面，只把 `/dashboard`、`/health` 和 `/reports` 代理到本地 FastAPI。
前端不持有 provider token 或其他密钥。

## 检查与生产构建

```powershell
pnpm format
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm test:sites
```

`pnpm build` 把客户端写入 `frontend/dist/client`。Docker 多阶段构建按 frozen lockfile 安装、构建，
再把客户端复制到 `/app/frontend-dist`，并为 FastAPI 设置 `JOBAGENT_FRONTEND_DIST_PATH`。
`/app/` 下的客户端路径回退到构建后的 `index.html`；API 前缀保持独立，绝不会回退为 HTML。

## 证据与错误规则

- 缺少台账行始终显示为**无运行记录**，不得转换成推测状态。
- 投递表不存在是能力状态，不是发送失败。
- 前端错误使用固定安全文案。不得渲染数据库/provider 原始错误、含凭据 URL、Token、哈希或 provider payload。
- 外部来源链接只接受 `http` 或 `https`，明确打开，并携带安全 `rel` 属性。
- 已载入、空数据、不可用和加载中状态分别存在且可测试。

## Issue 边界

未来导航标签只是禁用占位。JAI-051 负责可写反馈及其 schema 和 API。JAI-050 不授权迁移 `0010`、
真实 PushPlus 请求、scheduler 变更、补跑、JAI-028 无人值守试运行或 JAI-029 发布工作。
