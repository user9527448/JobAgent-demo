FROM node:24-alpine AS frontend-builder

WORKDIR /frontend

RUN corepack enable

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile

COPY frontend ./
RUN pnpm build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system jobagent && adduser --system --ingroup jobagent jobagent

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations
COPY config ./config
COPY --from=frontend-builder /frontend/dist/client /app/frontend-dist

RUN python -m pip install --no-cache-dir .

RUN mkdir -p /app/data/attachments && chown -R jobagent:jobagent /app/data

USER jobagent

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "jobagent.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
