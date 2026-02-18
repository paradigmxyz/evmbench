from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from api.core.database import DatabaseManager
from resultsvc.core.config import settings


_db = DatabaseManager(
    database_url=str(settings.DATABASE_DSN.get_secret_value()),
    pool_size=settings.RESULTSVC_DATABASE_POOL_SIZE,
    max_overflow=settings.RESULTSVC_DATABASE_MAX_OVERFLOW,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with _db.acquire() as session:
        yield session
