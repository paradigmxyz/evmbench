from __future__ import annotations

import os
import tempfile
import zipfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, BinaryIO


if TYPE_CHECKING:
    from fastapi import UploadFile


UNIX_FILE_TYPE_MASK = 0o170000
UNIX_SYMLINK_TYPE = 0o120000
ZIP_SANDBOX_DIR = Path(tempfile.gettempdir()) / 'zip-validate'


class ZipValidationError(ValueError):
    pass


def _ensure_max_files(file_count: int, max_files: int) -> None:
    if file_count > max_files:
        msg = f'Too many files in zip (>{max_files}).'
        raise ZipValidationError(msg)


def _ensure_safe_name(name: str) -> None:
    base_dir = ZIP_SANDBOX_DIR
    candidate = (base_dir / name).resolve()
    if not candidate.is_relative_to(base_dir.resolve()):
        msg = 'Path traversal detected in zip.'
        raise ZipValidationError(msg)


def _ensure_not_symlink(info: zipfile.ZipInfo) -> None:
    is_unix_symlink = (info.external_attr >> 16) & UNIX_FILE_TYPE_MASK == UNIX_SYMLINK_TYPE
    if is_unix_symlink:
        msg = 'Symlinks in zip are not allowed.'
        raise ZipValidationError(msg)


def _ensure_uncompressed_limit(total_uncompressed: int, max_uncompressed_bytes: int) -> None:
    if total_uncompressed > max_uncompressed_bytes:
        msg = f'Zip uncompressed size too large (>{max_uncompressed_bytes} bytes).'
        raise ZipValidationError(msg)


def _ensure_ratio(total_uncompressed: int, compressed_size: int, max_ratio: int) -> None:
    if compressed_size <= 0 or max_ratio <= 0:
        return
    ratio = total_uncompressed / compressed_size
    if ratio > max_ratio:
        msg = f'Zip compression ratio too high ({ratio:.1f} > {max_ratio}).'
        raise ZipValidationError(msg)


def _ensure_solidity(*, has_solidity: bool, require_solidity: bool) -> None:
    if require_solidity and not has_solidity:
        msg = 'Zip does not contain Solidity (*.sol) files.'
        raise ZipValidationError(msg)


@dataclass
class _ZipScanResult:
    total_uncompressed: int
    file_count: int
    has_solidity: bool


def _scan_zip(
    zf: zipfile.ZipFile,
    *,
    max_files: int,
    max_uncompressed_bytes: int,
    require_solidity: bool,
) -> _ZipScanResult:
    total_uncompressed = 0
    file_count = 0
    has_solidity = False

    for info in zf.infolist():
        name = info.filename
        if name.endswith('/'):
            continue

        file_count += 1
        _ensure_max_files(file_count, max_files)
        _ensure_safe_name(name)
        _ensure_not_symlink(info)

        total_uncompressed += int(info.file_size)
        _ensure_uncompressed_limit(total_uncompressed, max_uncompressed_bytes)

        if require_solidity and name.lower().endswith('.sol'):
            has_solidity = True

    return _ZipScanResult(
        total_uncompressed=total_uncompressed,
        file_count=file_count,
        has_solidity=has_solidity,
    )


def _get_stream_size(file_obj: BinaryIO) -> int:
    try:
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(0)
    except Exception as exc:
        msg = 'Unable to read uploaded file.'
        raise ZipValidationError(msg) from exc
    return int(size)


def validate_upload_zip(
    upload: UploadFile,
    *,
    max_uncompressed_bytes: int,
    max_files: int,
    max_ratio: int,
    require_solidity: bool = True,
) -> None:
    file_obj = upload.file
    compressed_size = _get_stream_size(file_obj)

    try:
        with zipfile.ZipFile(file_obj, 'r') as zf:
            scan = _scan_zip(
                zf,
                max_files=max_files,
                max_uncompressed_bytes=max_uncompressed_bytes,
                require_solidity=require_solidity,
            )
            _ensure_ratio(scan.total_uncompressed, compressed_size, max_ratio)
            _ensure_solidity(has_solidity=scan.has_solidity, require_solidity=require_solidity)
    except zipfile.BadZipFile as exc:
        msg = 'Invalid zip file.'
        raise ZipValidationError(msg) from exc
    finally:
        with suppress(Exception):
            file_obj.seek(0)
