"""Tests for structured logging and secret redaction."""

import json
from io import StringIO

from pydantic import SecretStr

from jobagent.core.config import Settings
from jobagent.core.logging import REDACTED, bind_log_context, configure_logging, get_logger


def test_json_logging_includes_context_and_redacts_secrets() -> None:
    output = StringIO()
    settings = Settings(
        environment="test",
        log_level="INFO",
        timezone="UTC",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
    configure_logging(settings, stream=output)
    logger = get_logger("jobagent.tests")

    with bind_log_context(request_id="request-123", run_id="run-456", source_id=7):
        logger.info(
            "crawler.started",
            extra={"api_token": "do-not-log", "stats": {"password": "hidden", "items": 3}},
        )

    payload = json.loads(output.getvalue())
    assert payload["event"] == "crawler.started"
    assert payload["request_id"] == "request-123"
    assert payload["run_id"] == "run-456"
    assert payload["source_id"] == 7
    assert payload["api_token"] == REDACTED
    assert payload["stats"] == {"password": REDACTED, "items": 3}


def test_log_context_does_not_leak_after_scope() -> None:
    output = StringIO()
    settings = Settings(
        environment="test",
        log_level="INFO",
        timezone="UTC",
        database_url=SecretStr("postgresql+psycopg://jobagent:test-only@localhost/jobagent_test"),
    )
    configure_logging(settings, stream=output)
    logger = get_logger("jobagent.tests")

    with bind_log_context(request_id="scoped"):
        logger.info("inside")
    logger.info("outside")

    lines = [json.loads(line) for line in output.getvalue().splitlines()]
    assert lines[0]["request_id"] == "scoped"
    assert "request_id" not in lines[1]
