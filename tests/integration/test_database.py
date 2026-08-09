"""PostgreSQL integration checks using an explicitly isolated test database."""

from __future__ import annotations

import asyncio
import os

import pytest

from jobagent.db.database import Database

pytestmark = pytest.mark.integration


def test_postgresql_accepts_health_query() -> None:
    """Exercise the real asynchronous driver and connection pool."""
    database_url = os.getenv("JOBAGENT_TEST_DATABASE_URL")
    if database_url is None:
        pytest.skip("Set JOBAGENT_TEST_DATABASE_URL to run PostgreSQL integration tests.")

    async def verify_connection() -> None:
        database = Database(database_url)
        try:
            await database.ping()
        finally:
            await database.close()

    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(verify_connection())
