from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from api.core.config import settings
from api.core.rabbitmq import RabbitMQPublisher

from .routers.v1 import router as v1_router


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    publisher = RabbitMQPublisher(
        dsn=settings.RABBITMQ_DSN.get_secret_value(),
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
    title='svmbench-backend',
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
