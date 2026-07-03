import io
import zipfile

import pytest
from fastapi import UploadFile

from api.util.zip_validate import UNIX_SYMLINK_TYPE, ZipValidationError, validate_upload_zip


def _zip_bytes(entries: dict[str, bytes | str]) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return data.getvalue()


def _symlink_zip_bytes() -> bytes:
    data = io.BytesIO()
    info = zipfile.ZipInfo('contracts/Linked.sol')
    info.create_system = 3
    info.external_attr = (UNIX_SYMLINK_TYPE | 0o777) << 16
    with zipfile.ZipFile(data, 'w') as zf:
        zf.writestr(info, 'Target.sol')
    return data.getvalue()


def _upload(data: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(data), filename='contracts.zip', size=len(data))


def _validate(
    data: bytes,
    *,
    max_uncompressed_bytes: int = 1024 * 1024,
    max_files: int = 10,
    max_ratio: int = 100,
    require_solidity: bool = True,
) -> None:
    validate_upload_zip(
        _upload(data),
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_files=max_files,
        max_ratio=max_ratio,
        require_solidity=require_solidity,
    )


def test_validate_upload_zip_accepts_solidity_zip_and_resets_stream() -> None:
    upload = _upload(_zip_bytes({'src/Vault.sol': 'contract Vault {}'}))

    validate_upload_zip(
        upload,
        max_uncompressed_bytes=1024,
        max_files=10,
        max_ratio=100,
        require_solidity=True,
    )

    assert upload.file.tell() == 0


@pytest.mark.parametrize(
    ('data', 'message'),
    [
        (_zip_bytes({'../Vault.sol': 'contract Vault {}'}), 'Path traversal'),
        (_zip_bytes({'README.md': '# docs'}), 'Solidity'),
        (_symlink_zip_bytes(), 'Symlinks'),
    ],
)
def test_validate_upload_zip_rejects_unsafe_archives(data: bytes, message: str) -> None:
    with pytest.raises(ZipValidationError, match=message):
        _validate(data)


def test_validate_upload_zip_rejects_too_many_files() -> None:
    data = _zip_bytes({'a.sol': 'contract A {}', 'b.sol': 'contract B {}'})

    with pytest.raises(ZipValidationError, match='Too many files'):
        _validate(data, max_files=1)


def test_validate_upload_zip_rejects_uncompressed_size_limit() -> None:
    data = _zip_bytes({'Large.sol': 'a' * 128})

    with pytest.raises(ZipValidationError, match='uncompressed size too large'):
        _validate(data, max_uncompressed_bytes=32)


def test_validate_upload_zip_rejects_high_compression_ratio() -> None:
    data = _zip_bytes({'Large.sol': 'a' * 8192})

    with pytest.raises(ZipValidationError, match='compression ratio too high'):
        _validate(data, max_ratio=1)


def test_validate_upload_zip_rejects_bad_zip() -> None:
    with pytest.raises(ZipValidationError, match='Invalid zip file'):
        _validate(b'not a zip')
