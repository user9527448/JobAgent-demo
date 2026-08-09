"""Asynchronous PostgreSQL connection pool."""

from typing import Protocol

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from jobagent.core.config import Settings
from jobagent.core.exceptions import TransientJobAgentError


class DatabaseHealth(Protocol):
    """Minimal database interface consumed by application lifecycle and readiness."""

    async def ping(self) -> None:
        """Raise when the database cannot serve a query."""

    async def close(self) -> None:
        """Release database resources."""


class Database:
    """Own the SQLAlchemy asynchronous engine and its connection pool."""

    def __init__(self, database_url: str) -> None:
        self._engine: AsyncEngine = create_async_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            pool_recycle=1800,
        )
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    @property
    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        """Expose short-lived ORM sessions to repository implementations."""
        return self._session_factory

    async def ping(self) -> None:
        """Verify that PostgreSQL accepts a trivial query."""
        try:
            async with self._engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        except SQLAlchemyError as error:
            raise TransientJobAgentError(
                "Database is temporarily unavailable.",
                code="database.unavailable",
            ) from error

    async def close(self) -> None:
        """Dispose the engine and all pooled connections."""
        await self._engine.dispose()


def create_database(settings: Settings) -> Database:
    """Build a database service without exposing the configured URL in logs."""
    return Database(settings.database_url.get_secret_value())
