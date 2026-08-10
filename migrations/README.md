# Database migrations

> 简体中文：[数据库迁移](../docs/zh-CN/MIGRATIONS.md)

Alembic reads the database URL from normal JOBAGENT settings. Keep credentials in `.env` or runtime environment variables, never in `alembic.ini`.

```powershell
alembic upgrade head
alembic current
alembic downgrade -1
```

Migration files are immutable after publication. Add a new revision for every later schema change.
