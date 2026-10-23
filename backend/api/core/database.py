from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, select
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
        if database_url.startswith('sqlite'):
            self._apply_sqlite_pragmas()

        self.SessionFactory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    def _apply_sqlite_pragmas(self) -> None:
        # Local no-Docker runs share the file across the api/resultsvc
        # processes; WAL plus a busy timeout keeps them from locking each other.
        @event.listens_for(self.engine.sync_engine, 'connect')
        def _set_sqlite_pragma(dbapi_connection: object, _record: object) -> None:
            cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
            cursor.execute('PRAGMA journal_mode=WAL')
            cursor.execute('PRAGMA busy_timeout=30000')
            cursor.execute('PRAGMA foreign_keys=ON')
            cursor.close()

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
