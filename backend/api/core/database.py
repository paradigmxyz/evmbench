from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase): ...


class DatabaseManager:
    def __init__(
        self,
        database_url: str,
        pool_size: int | None = None,
        max_overflow: int | None = None,
    ) -> None:
        kw: dict[str, int] = {}
        if pool_size is not None:
            kw['pool_size'] = pool_size
        if max_overflow is not None:
            kw['max_overflow'] = max_overflow

        self.engine: AsyncEngine = create_async_engine(
            database_url,
            **kw,
        )
        self.SessionFactory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def acquire(self) -> AsyncGenerator[AsyncSession]:
        session = self.SessionFactory()
        try:
            yield session
            if session.in_transaction():
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def vibe_check(self) -> None:
        async with self.acquire() as session:
            await session.scalar(select(1))
