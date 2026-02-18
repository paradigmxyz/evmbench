from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.database import DatabaseManager
from api.core.impl import auth_backend
from api.core.tokens import Token, decode_token


_db = DatabaseManager(
    database_url=str(settings.DATABASE_DSN.get_secret_value()),
    pool_size=settings.BACKEND_DATABASE_POOL_SIZE,
    max_overflow=settings.BACKEND_DATABASE_MAX_OVERFLOW,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    async with _db.acquire() as session:
        yield session


def get_token(session: str | None = Cookie(default=None)) -> Token:
    if auth_backend is None:
        return Token(user_id='local', login='local', avatar_url=None)

    if not session:
        raise HTTPException(status_code=401, detail='Authorization required')

    token = decode_token(session)
    if token is None:
        raise HTTPException(status_code=401, detail='Invalid session token')

    return token


def get_optional_token(session: str | None = Cookie(default=None)) -> Token | None:
    try:
        return get_token(session)
    except HTTPException:
        return None


TokenDep = Annotated[Token, Depends(get_token)]
OptionalTokenDep = Annotated[Token | None, Depends(get_optional_token)]
