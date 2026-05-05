import hashlib
import json
from collections.abc import Iterable
from functools import lru_cache
from urllib.parse import quote

import httpx
from fastapi import APIRouter, HTTPException, Request
from starlette.background import BackgroundTask
from starlette.responses import Response, StreamingResponse

from api.util.aes_gcm import decrypt_token, derive_key
from oai_proxy.core.config import settings
from oai_proxy.core.response_cache import CachedResponse, ResponseCache


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
RESPONSE_CACHE_HEADER = 'x-evmbench-response-cache'
RESPONSE_CACHE_PATHS = {
    'completions',
    'chat/completions',
    'responses',
    'v1/completions',
    'v1/chat/completions',
    'v1/responses',
    # vLLM-specific but deterministic; caching this keeps repeated contract analysis
    # runs from paying tokenize latency when the source is identical.
    'tokenize',
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


@lru_cache(maxsize=1)
def _response_cache() -> ResponseCache:
    return ResponseCache(
        db_path=settings.OAI_PROXY_RESPONSE_CACHE_DIR / 'response_cache.sqlite3',
        ttl_seconds=settings.OAI_PROXY_RESPONSE_CACHE_TTL_SECONDS,
        max_entry_bytes=settings.OAI_PROXY_RESPONSE_CACHE_MAX_ENTRY_BYTES,
        max_entries=settings.OAI_PROXY_RESPONSE_CACHE_MAX_ENTRIES,
    )


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
        if key_lower == RESPONSE_CACHE_HEADER:
            continue
        headers[key_lower] = value
    return headers


def _target_base_url() -> str:
    return settings.OAI_PROXY_UPSTREAM_BASE_URL.rstrip('/')


def _should_strip_web_search(*, method: str, path: str) -> bool:
    if not settings.OAI_PROXY_STRIP_WEB_SEARCH:
        return False
    if method.upper() != 'POST':
        return False
    normalized_path = path.strip('/').rstrip('/')
    return normalized_path in {'responses', 'v1/responses'}


def _request_disables_response_cache(request: Request) -> bool:
    cache_control = request.headers.get('cache-control', '').lower()
    pragma = request.headers.get('pragma', '').lower()
    return 'no-store' in cache_control or 'no-cache' in cache_control or 'no-cache' in pragma


def _is_response_cache_path(*, method: str, path: str) -> bool:
    if not settings.OAI_PROXY_RESPONSE_CACHE_ENABLED:
        return False
    if method.upper() != 'POST':
        return False
    normalized_path = path.strip('/').rstrip('/')
    return normalized_path in RESPONSE_CACHE_PATHS


def _is_streaming_request(body: bytes) -> bool:
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return isinstance(payload, dict) and payload.get('stream') is True


def _cache_key(*, method: str, base_url: str, path: str, query: str, body: bytes, token: str) -> str:
    auth_part = ''
    if settings.OAI_PROXY_RESPONSE_CACHE_INCLUDE_AUTH:
        auth_part = hashlib.sha256(token.encode('utf-8')).hexdigest()

    digest = hashlib.sha256()
    for part in ('v1', method.upper(), base_url.rstrip('/'), path.strip('/'), query, auth_part):
        digest.update(part.encode('utf-8'))
        digest.update(b'\0')
    digest.update(body)
    return digest.hexdigest()


def _cached_response(cached: CachedResponse) -> Response:
    headers = dict(cached.headers)
    headers[RESPONSE_CACHE_HEADER] = 'hit'
    return Response(
        content=cached.body,
        status_code=cached.status_code,
        headers=headers,
    )


async def _read_raw_body(upstream: httpx.Response) -> bytes:
    chunks = []
    async for chunk in upstream.aiter_raw():
        chunks.append(chunk)
    return b''.join(chunks)


async def _forward_body(request: Request, *, path: str, force_bytes: bool = False) -> bytes | Iterable[bytes]:
    if not _should_strip_web_search(method=request.method, path=path):
        if force_bytes:
            return await request.body()
        return request.stream()

    try:
        payload = await request.json()
    except json.JSONDecodeError:
        return await request.body()

    if not isinstance(payload, dict):
        return await request.body()

    tools = payload.get('tools')
    if isinstance(tools, list):
        payload['tools'] = [
            tool for tool in tools if not isinstance(tool, dict) or tool.get('type') != 'web_search'
        ]

    return json.dumps(payload).encode('utf-8')


async def _proxy_request(request: Request, path: str) -> Response:
    token = _get_authorization_token(request)
    openai_key = _resolve_openai_key(token)
    forward_headers = _filter_headers(request.headers.items())
    forward_headers['authorization'] = f'Bearer {openai_key}'

    target_path = path.lstrip('/')
    encoded_path = quote(target_path, safe='/')
    base_url = _target_base_url()
    target_url = f'{base_url}/{encoded_path}' if encoded_path else base_url

    cache_candidate = (
        _is_response_cache_path(method=request.method, path=target_path)
        and not _request_disables_response_cache(request)
    )
    body = await _forward_body(request, path=target_path, force_bytes=cache_candidate)
    params = request.query_params
    response_cache_key: str | None = None

    if cache_candidate and isinstance(body, bytes) and not _is_streaming_request(body):
        response_cache_key = _cache_key(
            method=request.method,
            base_url=base_url,
            path=target_path,
            query=request.url.query,
            body=body,
            token=token,
        )
        cached = _response_cache().get(response_cache_key)
        if cached is not None:
            return _cached_response(cached)

    client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
    upstream = await client.send(
        client.build_request(
            request.method,
            target_url,
            params=params,
            headers=forward_headers,
            content=body,
        ),
        stream=True,
    )

    response_headers = _filter_headers(upstream.headers.items())

    async def _cleanup() -> None:
        await upstream.aclose()
        await client.aclose()

    if response_cache_key is not None:
        try:
            response_body = await _read_raw_body(upstream)
        finally:
            await _cleanup()

        cache_headers = dict(response_headers)
        if _response_cache().set(
            response_cache_key,
            status_code=upstream.status_code,
            headers=cache_headers,
            body=response_body,
        ):
            response_headers[RESPONSE_CACHE_HEADER] = 'miss'
        else:
            response_headers[RESPONSE_CACHE_HEADER] = 'bypass'
        return Response(content=response_body, status_code=upstream.status_code, headers=response_headers)

    return StreamingResponse(
        upstream.aiter_raw(),
        status_code=upstream.status_code,
        headers=response_headers,
        background=BackgroundTask(_cleanup),
    )


@router.api_route('/', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
@router.api_route('/{path:path}', methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD'])
async def proxy_all(request: Request, path: str = '') -> Response:
    return await _proxy_request(request, path)
