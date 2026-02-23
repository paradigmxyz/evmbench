import io
import os
import tarfile

import orjson
from fastapi import UploadFile


def build_secret_bundle(
    *,
    upload: UploadFile,
    openai_token: str,
    key_mode: str,
    codex_auth_json: str | None = None,
) -> bytes:
    upload_file = upload.file

    # NOTE(es3n1n): upload.size is optional
    upload_file.seek(0, os.SEEK_END)
    upload_size = upload_file.tell()
    upload_file.seek(0)

    key_data: dict[str, str] = {'openai_token': openai_token, 'key_mode': key_mode}
    if codex_auth_json is not None:
        key_data['codex_auth_json'] = codex_auth_json
    key_payload = orjson.dumps(key_data)

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as tar:
        upload_info = tarfile.TarInfo(name='upload.zip')
        upload_info.size = upload_size
        tar.addfile(upload_info, fileobj=upload_file)

        key_info = tarfile.TarInfo(name='key.json')
        key_info.size = len(key_payload)
        tar.addfile(key_info, fileobj=io.BytesIO(key_payload))

    return buffer.getvalue()
