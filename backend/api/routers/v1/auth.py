import secrets
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from secrets import compare_digest
from typing import Annotated

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import RedirectResponse

from api.core.config import settings
from api.core.deps import TokenDep
from api.core.impl import auth_backend
from api.core.tokens import encode_token
from api.schemas.auth import UserObject


router = APIRouter(prefix='/auth', tags=['auth'])
STATE_COOKIE_NAME = 'oauth_state'
STATE_TTL_SECONDS = 10 * 60


@router.get('/')
async def redirect_to_auth() -> RedirectResponse:
    if not auth_backend:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Not found')

    state = secrets.token_urlsafe(32)
    redirect = RedirectResponse(
        url=await auth_backend.get_redirect_url(
            state,
            settings.BACKEND_PUBLIC_URL.rstrip('/') + '/v1/auth/callback',
        ),
        status_code=HTTPStatus.TEMPORARY_REDIRECT,
    )
    redirect.set_cookie(
        key=STATE_COOKIE_NAME,
        value=state,
        httponly=True,
        samesite='lax',
        secure=not settings.BACKEND_DEV,
        max_age=STATE_TTL_SECONDS,
        expires=datetime.now(tz=UTC) + timedelta(seconds=STATE_TTL_SECONDS),
    )
    return redirect


@router.get('/callback')
async def auth_callback(
    code: str | None = None,
    state: str | None = None,
    oauth_state: Annotated[str | None, Cookie(alias=STATE_COOKIE_NAME)] = None,
) -> RedirectResponse:
    if not auth_backend:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Not found')

    redirect = RedirectResponse(
        url=settings.FRONTEND_PUBLIC_URL,
        status_code=HTTPStatus.TEMPORARY_REDIRECT,
    )
    redirect.delete_cookie(
        key=STATE_COOKIE_NAME,
        samesite='lax',
    )

    if not code or not state or not oauth_state or not compare_digest(state, oauth_state):
        return redirect

    token = await auth_backend.get_token(code)
    if not token:
        return redirect

    ttl_seconds = settings.BACKEND_JWT_TTL_SECONDS
    redirect.set_cookie(
        key='session',
        value=encode_token(token),
        httponly=True,
        samesite='lax',
        max_age=ttl_seconds,
        expires=datetime.now(tz=UTC) + timedelta(seconds=ttl_seconds),
    )
    return redirect


@router.get('/me')
async def get_me(token: TokenDep) -> UserObject:
    return UserObject(
        avatar_url=token.avatar_url,
        username=token.login,
    )


@router.get('/logout')
async def logout() -> RedirectResponse:
    if not auth_backend:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Not found')
    redirect = RedirectResponse(
        url=settings.FRONTEND_PUBLIC_URL,
        status_code=HTTPStatus.TEMPORARY_REDIRECT,
    )
    redirect.delete_cookie(
        key='session',
        samesite='lax',
        secure=not settings.BACKEND_DEV,
    )
    return redirect
