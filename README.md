# JOBAGENT V1.0

面向个人的招聘情报 Agent：采集、解析、筛选并推送企业校招和公职考试信息。

> 当前状态：API、PostgreSQL 与持续集成基线已就绪。业务能力将按 [GitHub Issues Backlog](docs/GITHUB_ISSUES.md) 逐步实现。

## 环境要求

- Python 3.11 或更高版本
- Git

运行完整开发环境和 PostgreSQL 集成测试需要 Docker Desktop；其余检查无需 Docker。

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
python scripts/check.py
```

该入口与 GitHub Actions 使用相同的格式、静态分析、类型、测试和覆盖率检查；任一步失败都会立即返回非零状态。覆盖率下限为 85%。

若本地 PostgreSQL Compose 服务正在运行，可同时启用真实数据库集成测试：

```powershell
$env:JOBAGENT_TEST_DATABASE_URL = "postgresql+psycopg://jobagent:jobagent-dev-only@localhost:5432/jobagent"
python scripts/check.py
Remove-Item Env:JOBAGENT_TEST_DATABASE_URL
```

未设置该专用变量时，仅跳过 PostgreSQL 集成测试，其余质量检查照常执行。CI 始终使用独立的 `jobagent_test` 数据库运行该测试。

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
├─ scripts/check.py   # 本地与 CI 共用的质量门禁
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

## 数据库迁移

升级当前配置的数据库：

```powershell
alembic upgrade head
alembic current
```

使用 Compose 镜像执行：

```powershell
docker compose exec api alembic upgrade head
```

迁移集成测试只允许操作名称以 `_test` 结尾的数据库，避免误清理开发或生产数据。详细字段、关系、索引和删除策略参见 [数据库模型文档](docs/DATABASE.md)。

## 文档

- [详细开发计划](docs/DEVELOPMENT_PLAN.md)
- [GitHub Issues Backlog](docs/GITHUB_ISSUES.md)
- [配置、日志与错误约定](docs/CONFIGURATION.md)
- [数据库模型与迁移](docs/DATABASE.md)
- [JAI-005 首个真实来源技术验证](docs/spikes/JAI-005-JINING-SOURCE.md)
- [持续开发工作日志](docs/WORKLOG.md)
