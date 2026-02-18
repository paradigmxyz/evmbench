import os
import re
from collections.abc import Callable
from contextlib import suppress
from hmac import compare_digest
from pathlib import Path
from typing import Annotated

import aiofiles
import aiofiles.os as aioos
from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from loguru import logger
from starlette.background import BackgroundTask

from secretsvc.core.config import settings


router = APIRouter(prefix='/bundles')
_SECRET_REF_RE = re.compile(r'^[a-f0-9]{1,64}$')

TokenHeader = Annotated[str | None, Header()]


def _require_token(*, w: bool) -> Callable[[TokenHeader], None]:
    def cb(x_secrets_token: TokenHeader = None) -> None:
        expected = settings.SECRETSVC_SECRETS_TOKEN_RO.get_secret_value()
        if w:
            expected = settings.SECRETSVC_SECRETS_TOKEN_WO.get_secret_value()

        provided = (x_secrets_token or '').encode()
        if expected and not compare_digest(provided, expected.encode()):
            raise HTTPException(status_code=401, detail='unauthorized')

    return cb


async def _ensure_private_dir(path: Path) -> None:
    await aioos.makedirs(path, exist_ok=True)
    with suppress(OSError):
        path.chmod(0o700)


def _secret_path(secret_ref: str) -> Path:
    if not _SECRET_REF_RE.fullmatch(secret_ref):
        raise HTTPException(status_code=400, detail='invalid secret_ref')
    return settings.SECRETSVC_SECRETS_DIR / f'{secret_ref}.tar'


def _secret_hits_path(secret_ref: str) -> Path:
    if not _SECRET_REF_RE.fullmatch(secret_ref):
        raise HTTPException(status_code=400, detail='invalid secret_ref')
    return settings.SECRETSVC_SECRETS_DIR / f'{secret_ref}.hits'


async def _read_hits(path: Path) -> int:
    try:
        async with aiofiles.open(path) as handle:
            content = await handle.read()
        return int(content.strip() or 0)
    except (FileNotFoundError, ValueError):
        return 0


async def _write_hits(path: Path, count: int) -> None:
    tmp = path.with_suffix(path.suffix + f'.tmp.{os.getpid()}')
    async with aiofiles.open(tmp, 'w') as handle:
        await handle.write(str(count))
        await handle.flush()
        os.fsync(handle.fileno())
    with suppress(OSError):
        tmp.chmod(0o600)
    await aioos.replace(tmp, path)


async def _increment_hits(secret_ref: str) -> int:
    hits_path = _secret_hits_path(secret_ref)
    current = await _read_hits(hits_path)
    current += 1
    await _write_hits(hits_path, current)
    return current


@router.put('/{secret_ref}', dependencies=[Depends(_require_token(w=True))])
async def store_bundle(secret_ref: str, bundle: Annotated[UploadFile, File()]) -> dict[str, str]:
    await _ensure_private_dir(settings.SECRETSVC_SECRETS_DIR)
    target = _secret_path(secret_ref)
    tmp = target.with_suffix(target.suffix + f'.tmp.{os.getpid()}')

    await bundle.seek(0)
    async with aiofiles.open(tmp, 'wb') as handle:
        while chunk := await bundle.read(1024 * 1024):
            await handle.write(chunk)
        await handle.flush()
        os.fsync(handle.fileno())

    with suppress(OSError):
        tmp.chmod(0o600)

    await aioos.replace(tmp, target)
    logger.info('Stored bundle secret_ref={}', secret_ref)
    return {'secret_ref': secret_ref}


@router.get('/{secret_ref}', dependencies=[Depends(_require_token(w=False))])
async def get_bundle(secret_ref: str) -> FileResponse:
    path = _secret_path(secret_ref)
    if not path.exists():
        raise HTTPException(status_code=404, detail='secret not found')

    hits = await _increment_hits(secret_ref)
    task = None
    if hits >= settings.SECRETSVC_BUNDLE_MAX_READS:
        task = BackgroundTask(_delete_bundle_file, path, _secret_hits_path(secret_ref))

    logger.info('Serving bundle secret_ref={} hits={}', secret_ref, hits)
    return FileResponse(
        path,
        media_type='application/x-tar',
        filename='bundle.tar',
        background=task,
    )


@router.delete('/{secret_ref}', dependencies=[Depends(_require_token(w=True))])
async def delete_bundle(secret_ref: str) -> dict[str, str]:
    path = _secret_path(secret_ref)
    await _delete_bundle_file(path, _secret_hits_path(secret_ref))
    logger.info('Deleted bundle secret_ref={}', secret_ref)
    return {'secret_ref': secret_ref}


async def _delete_bundle_file(path: Path, hits_path: Path | None = None) -> None:
    with suppress(FileNotFoundError):
        await aioos.remove(path)
    if hits_path is not None:
        with suppress(FileNotFoundError):
            await aioos.remove(hits_path)
