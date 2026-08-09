# JOBAGENT V1.0

面向个人的招聘情报 Agent：采集、解析、筛选并推送企业校招和公职考试信息。

> 当前状态：工程基线搭建中。业务能力将按 [GitHub Issues Backlog](docs/GITHUB_ISSUES.md) 逐步实现。

## 环境要求

- Python 3.11 或更高版本
- Git

后续接入数据库时还会需要 Docker Desktop；当前工程基线无需 Docker 即可运行。

## 本地开发

使用本机现有的 Python 3.11+ 创建项目虚拟环境；这不会下载新的 Python 版本。PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

如果本机存在多个 Python 版本，请在创建 `.venv` 前确认上述 `python` 指向希望使用的现有 Python 3.11+ 环境。后续命令均在激活的 `.venv` 中执行。

验证安装：

```powershell
jobagent
```

预期输出：

```text
JOBAGENT project bootstrap is ready.
```

## 质量检查

```powershell
ruff format --check .
ruff check .
mypy src tests
pytest
```

自动修复格式和可安全修复的问题：

```powershell
ruff format .
ruff check --fix .
```

## 项目结构

```text
JOBAGENTV1.0/
├─ src/jobagent/      # Python 应用包
├─ tests/             # 自动化测试
├─ docs/              # 产品与开发文档
├─ .env.example       # 环境变量示例（不含密钥）
└─ pyproject.toml     # 依赖、构建和质量工具配置
```

## 配置与密钥

需要本地配置时，将 `.env.example` 复制为 `.env`。禁止将 `.env`、访问令牌、数据库密码、下载附件和个人数据提交到仓库。

## 开发流程

1. 从 `develop` 创建 `feature/<issue>-<description>` 分支。
2. 每个分支只处理一个 Issue。
3. 提交前运行全部质量检查。
4. 通过 Pull Request 合并到 `develop`；发布时再合并到 `main`。

## API 与数据库

Docker Desktop 启动后，可运行完整开发环境：

```powershell
Copy-Item .env.example .env
docker compose up --build -d
docker compose ps
```

健康检查：

```powershell
Invoke-RestMethod http://localhost:8000/health/live
Invoke-RestMethod http://localhost:8000/health/ready
```

- `/health/live` 只检查 API 进程是否存活。
- `/health/ready` 会执行 PostgreSQL `SELECT 1`；数据库不可用时返回 HTTP 503。
- OpenAPI 文档位于 `http://localhost:8000/docs`。

停止服务但保留数据库数据：

```powershell
docker compose down
```

本地不使用 Docker 启动 API 时，先配置 `.env`，再运行：

```powershell
python -m uvicorn jobagent.api.app:create_app --factory --reload
```

## 文档

- [详细开发计划](docs/DEVELOPMENT_PLAN.md)
- [GitHub Issues Backlog](docs/GITHUB_ISSUES.md)
- [配置、日志与错误约定](docs/CONFIGURATION.md)
- [持续开发工作日志](docs/WORKLOG.md)
