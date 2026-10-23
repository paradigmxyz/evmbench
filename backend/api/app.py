from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse
from loguru import logger

import api.models.job  # noqa: F401  (registers the jobs table on Base)
from api.core.config import settings
from api.core.database import Base
from api.core.deps import get_database
from api.core.dispatch import LocalJobDispatcher
from api.core.rabbitmq import RabbitMQPublisher

from .routers.v1 import router as v1_router


async def _auto_create_tables() -> None:
    # Local no-Docker runs skip alembic and create the single jobs table directly.
    engine = get_database().engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info('database tables created (DATABASE_AUTO_CREATE_TABLES)')


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    if settings.DATABASE_AUTO_CREATE_TABLES:
        await _auto_create_tables()

    if settings.BACKEND_QUEUE_BACKEND == 'local':
        publisher: RabbitMQPublisher | LocalJobDispatcher = LocalJobDispatcher()
    else:
        publisher = RabbitMQPublisher(
            dsn=settings.RABBITMQ_DSN.get_secret_value(),  # type: ignore[union-attr]
            queue=settings.rabbitmq_queue_name,
        )
    await publisher.connect()
    fastapi_app.state.rabbitmq = publisher
    try:
        yield
    finally:
        await publisher.close()


app = FastAPI(
    docs_url='/' if settings.BACKEND_DEV else None,
    openapi_url='/openapi.json' if settings.BACKEND_DEV else None,
    redoc_url=None,
    version='0.0.1',
    title='evmbench-backend',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,  # type: ignore[invalid-argument-type]
    allow_origins=[
        settings.FRONTEND_PUBLIC_URL,
        *settings.BACKEND_CORS_EXTRA_ORIGINS,
    ],
    allow_origin_regex=r'https://.*\.vercel\.app|https://.*\.paradigm\.xyz|http://(localhost|127\.0\.0\.1)(:\d+)?',
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(v1_router)
