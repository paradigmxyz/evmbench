from collections.abc import Iterable
from functools import lru_cache
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from api.util.aes_gcm import decrypt_token, derive_key
from oai_proxy.core.config import settings


PROVIDER_BASE_URLS = {
    'openai': 'https://api.openai.com',
    'openrouter': 'https://openrouter.ai/api',
}
DEFAULT_PROVIDER = 'openai'
# Marker token that triggers use of the static key
STATIC_KEY_MARKER = 'STATIC'
HOP_BY_HOP_HEADERS = {
    'connection',
    'host',
    'keep-alive',
    'proxy-authenticate',
    'proxy-authorization',
    'te',
    'trailers',
    'transfer-encoding',
    'upgrade',
}

router = APIRouter()


@lru_cache(maxsize=1)
def _aesgcm_key() -> bytes:
    return derive_key(settings.OAI_PROXY_AES_KEY.get_secret_value())


@lru_cache(maxsize=1)
def _get_static_key() -> str | None:
    if settings.OAI_PROXY_STATIC_KEY:
        return settings.OAI_PROXY_STATIC_KEY.get_secret_value()
    return None


def _decrypt_token(token: str) -> str:
    try:
        return decrypt_token(token, key=_aesgcm_key())
    except ValueError as err:
        raise HTTPException(status_code=401, detail='Invalid token') from err


def _resolve_openai_key(token: str) -> str:
    """Resolve the actual OpenAI key from the provided token.

    If token is STATIC_KEY_MARKER, use the static key (if configured).
    Otherwise, decrypt the encrypted token.
    """
    if token == STATIC_KEY_MARKER:
        static_key = _get_static_key()
        if not static_key:
            raise HTTPException(
                status_code=501,
                detail='Static key not configured on proxy',
            )
        return static_key
    return _decrypt_token(token)


def _get_authorization_token(request: Request) -> str:
    auth_header = request.headers.get('authorization')
    if not auth_header:
        raise HTTPException(status_code=401, detail='Missing Authorization header')
    scheme, _, token = auth_header.partition(' ')
    if scheme.lower() != 'bearer' or not token:
        raise HTTPException(status_code=401, detail='Invalid Authorization header')
    return token


def _filter_headers(items: Iterable[tuple[str, str]]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in items:
        key_lower = key.lower()
        if key_lower in HOP_BY_HOP_HEADERS:
            continue
        if key_lower == 'content-length':
            continue
        headers[key_lower] = value
    return headers


def _get_provider_base_url(request: Request) -> str:
    """Get the base URL for the provider from query params."""
    provider = request.query_params.get('provider', DEFAULT_PROVIDER).lower()
    return PROVIDER_BASE_URLS.get(provider, PROVIDER_BASE_URLS[DEFAULT_PROVIDER])


def _filter_query_params(params: dict) -> dict:
    """Remove internal params like 'provider' from forwarded query."""
    return {k: v for k, v in params.items() if k != 'provider'}


async def _proxy_request(request: Request, path: str) -> StreamingResponse:
    token = _get_authorization_token(request)
    openai_key = _resolve_openai_key(token)
    base_url = _get_provider_base_url(request)
    forward_headers = _filter_headers(request.headers.items())
    forward_headers['authorization'] = f'Bearer {openai_key}'

    # Add OpenRouter-specific headers if routing to OpenRouter
    if 'openrouter.ai' in base_url:
        forward_headers['http-referer'] = 'https://svmbench.io'
        forward_headers['x-title'] = 'svmbench'

    target_path = path.lstrip('/')
    encoded_path = quote(target_path, safe='/')
    target_url = f'{base_url}/{encoded_path}' if encoded_path else base_url

    body = request.stream()
    # Filter out internal params
    filtered_params = _filter_query_params(dict(request.query_params))

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    upstream = await client.send(
        client.build_request(
            request.method,
            target_url,
            params=filtered_params,
            headers=forward_headers,
            content=body,
        ),
        stream=True,
    )

    response_headers = _filter_headers(upstream.headers.items())

    async def _cleanup() -> None:
        await upstream.aclose()
        await client.aclose()

    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(_cleanup),
    )


@router.api_route('/', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
async def proxy_all(request: Request, path: str = '') -> StreamingResponse:
    return await _proxy_request(request, path)
