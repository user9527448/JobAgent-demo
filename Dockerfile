FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system jobagent && adduser --system --ingroup jobagent jobagent

COPY pyproject.toml README.md alembic.ini ./
COPY src ./src
COPY migrations ./migrations

RUN python -m pip install --no-cache-dir .

USER jobagent

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "jobagent.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
