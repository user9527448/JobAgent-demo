"""Production construction helpers for the approved PushPlus boundary."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from jobagent.core import ConfigurationError, Settings
from jobagent.reports import SqlAlchemyDailyReportService

from .persistence import SqlAlchemyDeliveryLock, SqlAlchemyDeliveryRepository
from .pushplus import PushPlusProvider, PushPlusProviderConfig
from .service import SqlAlchemyNotificationDeliveryService


def build_pushplus_delivery_service(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
) -> tuple[PushPlusProvider, SqlAlchemyNotificationDeliveryService]:
    """Build a live-capable adapter only when both environment secrets exist."""
    if settings.pushplus_token is None or settings.pushplus_secret_key is None:
        raise ConfigurationError(
            "PushPlus delivery credentials are not configured.",
            code="notification.credentials_missing",
        )
    provider = PushPlusProvider(
        PushPlusProviderConfig(
            token=settings.pushplus_token,
            secret_key=settings.pushplus_secret_key,
        )
    )
    service = SqlAlchemyNotificationDeliveryService(
        SqlAlchemyDailyReportService(session_factory, settings.timezone),
        SqlAlchemyDeliveryRepository(session_factory),
        SqlAlchemyDeliveryLock(session_factory),
        provider,
    )
    return provider, service
