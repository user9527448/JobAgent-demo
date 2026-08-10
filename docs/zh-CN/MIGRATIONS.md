# 数据库迁移

> 英文原文：[Database migrations](../../migrations/README.md)。修改原文时必须在同一提交中同步更新本镜像。

Alembic 从正常的 JOBAGENT Settings 中读取数据库 URL。凭据应保存在 `.env` 或运行时环境变量中，绝不能写入 `alembic.ini`。

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

迁移文件发布后不可修改。之后每次 Schema 变更都应新增一个 revision。
