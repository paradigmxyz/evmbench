try:
    from uvloop import run  # type: ignore[unresolved-import]
except ImportError:
    from asyncio import run

import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile
from pathlib import Path

from httpx import AsyncClient
from loguru import logger


SECRET_SVC_HOST = os.getenv('SECRETSVC_HOST', 'secretsvc')
SECRET_SVC_PORT = os.getenv('SECRETSVC_PORT', '8081')
SECRET_REF = os.getenv('SECRETSVC_REF', '')
SECRET_SVC_TOKEN = os.getenv('SECRETSVC_TOKEN', '')
RESULTSVC_HOST = os.getenv('RESULTSVC_HOST', '')
RESULTSVC_PORT = os.getenv('RESULTSVC_PORT', '8083')
RESULTSVC_JOB_TOKEN = os.getenv('RESULTSVC_JOB_TOKEN', '')
OAI_PROXY_BASE_URL = os.getenv('OAI_PROXY_BASE_URL', '').strip()
OAI_PROXY_WIRE_API = os.getenv('OAI_PROXY_WIRE_API', 'responses').strip()

AGENT_DIR = Path(os.getenv('AGENT_DIR') or str(Path.home()))
AUDIT_DIR = Path(os.getenv('AUDIT_DIR') or str(AGENT_DIR / 'audit'))
SUBMISSION_DIR = Path(os.getenv('SUBMISSION_DIR') or str(AGENT_DIR / 'submission'))
LOGS_DIR = Path(os.getenv('LOGS_DIR') or '/home/logs')

JOB_ID = os.getenv('JOB_ID', 'job').strip()
MODEL_KEY = os.getenv('AGENT_ID', '').strip()

RUNNER_DIR = Path(os.getenv('EVM_BENCH_RUNNER_DIR') or '/opt/evmbench/worker_runner')
DETECT_MD_PATH = RUNNER_DIR / 'detect.md'
MODEL_MAP_PATH = RUNNER_DIR / 'model_map.json'
CODEX_RUNNER_SH = RUNNER_DIR / 'run_codex_detect.sh'


def _write_codex_proxy_config(*, home: Path) -> None:
    """Configure Codex to call our local proxy provider.

    In proxy-token mode, OPENAI_API_KEY is not an OpenAI key; it's an opaque token.
    Codex is pointed at oai_proxy which decrypts the token and forwards upstream.
    """
    if not OAI_PROXY_BASE_URL:
        msg = 'Missing OAI_PROXY_BASE_URL for proxy mode'
        raise RuntimeError(msg)

    base_url = OAI_PROXY_BASE_URL.rstrip('/')
    if not base_url.endswith('/v1'):
        base_url = f'{base_url}/v1'

    config_dir = home / '.codex'
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / 'config.toml'
    config = (
        'model_provider = "proxy"\n\n'
        '[model_providers.proxy]\n'
        'name = "proxy"\n'
        f'base_url = "{base_url}"\n'
        f'wire_api = "{OAI_PROXY_WIRE_API}"\n'
        'env_key = "OPENAI_API_KEY"\n'
    )
    config_path.write_text(config, encoding='utf-8')


def _load_model_map() -> dict[str, str]:
    try:
        data = json.loads(MODEL_MAP_PATH.read_text(encoding='utf-8'))
    except FileNotFoundError:
        logger.warning(f'Missing {MODEL_MAP_PATH=}; falling back to MODEL_KEY passthrough')
        return {}
    except Exception as err:  # noqa: BLE001
        logger.warning(f'Unable to parse {MODEL_MAP_PATH=}: {err}')
        return {}

    if not isinstance(data, dict):
        logger.warning(f'Unexpected model map type: {type(data)}; expected object')
        return {}

    model_map: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str) and k.strip() and v.strip():
            model_map[k.strip()] = v.strip()
    return model_map


def _resolve_codex_model(*, model_key: str, model_map: dict[str, str]) -> str:
    key = (model_key or '').strip()
    if key and key in model_map:
        return model_map[key]
    if key:
        # Allow passing a raw Codex model id via AGENT_ID.
        return key
    return model_map.get('codex-gpt-5.2', 'gpt-5.2-2025-12-11')


def _extract_fenced_json(text: str) -> str:
    start = text.find('```json')
    if start == -1:
        return text
    start = text.find('\n', start)
    if start == -1:
        return text
    end = text.find('```', start + 1)
    if end == -1:
        return text
    return text[start + 1 : end].strip()


def _validate_report_payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        msg = 'audit.md JSON payload must be an object'
        raise TypeError(msg)

    vulns = payload.get('vulnerabilities')
    if not isinstance(vulns, list):
        msg = 'audit.md JSON payload must contain vulnerabilities: [...]'
        raise TypeError(msg)

    # Lightweight schema sanity checks (keep UI robust to agent weirdness).
    for v in vulns:
        if not isinstance(v, dict):
            msg = 'Each vulnerability must be an object'
            raise TypeError(msg)
        title = v.get('title')
        severity = v.get('severity')
        if not isinstance(title, str) or not title.strip():
            msg = 'Each vulnerability must contain a non-empty title'
            raise ValueError(msg)
        if not isinstance(severity, str):
            msg = 'Each vulnerability must contain a severity'
            raise TypeError(msg)
        if not severity.strip():
            msg = 'Each vulnerability must contain a severity'
            raise ValueError(msg)

    return payload


def _extract_json_payload(audit_md: str) -> dict:
    text = (audit_md or '').strip()
    if not text:
        msg = 'Empty audit.md'
        raise ValueError(msg)

    # Prefer fenced JSON block; fall back to raw text.
    json_text = _extract_fenced_json(text)
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as err:
        msg = f'audit.md does not contain valid JSON: {err}'
        raise ValueError(msg) from err

    return _validate_report_payload(payload)


def _run_codex_detect(*, openai_token: str, key_mode: str) -> Path:
    env = os.environ.copy()
    env['OPENAI_API_KEY'] = openai_token
    # Codex CLI supports using CODEX_API_KEY; keep it aligned to avoid surprises.
    env['CODEX_API_KEY'] = openai_token
    env['HOME'] = str(AGENT_DIR)
    env['AGENT_DIR'] = str(AGENT_DIR)
    env['SUBMISSION_DIR'] = str(SUBMISSION_DIR)
    env['LOGS_DIR'] = str(LOGS_DIR)

    # Proxy-token mode: write Codex config to route requests through oai_proxy.
    if key_mode in {'proxy', 'proxy_static'}:
        _write_codex_proxy_config(home=AGENT_DIR)

    if not DETECT_MD_PATH.exists():
        msg = f'Missing detect instructions: {DETECT_MD_PATH}'
        raise RuntimeError(msg)
    if not CODEX_RUNNER_SH.exists():
        msg = f'Missing Codex runner: {CODEX_RUNNER_SH}'
        raise RuntimeError(msg)

    model_map = _load_model_map()
    model = _resolve_codex_model(model_key=MODEL_KEY, model_map=model_map)
    env['CODEX_MODEL'] = model
    env['EVM_BENCH_DETECT_MD'] = str(DETECT_MD_PATH)

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(  # noqa: S603
        [str(CODEX_RUNNER_SH)],
        cwd=str(AGENT_DIR),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    (LOGS_DIR / 'runner.log').write_text(proc.stdout or '', encoding='utf-8')
    if proc.returncode != 0:
        msg = f'Codex runner failed with code={proc.returncode}:\n{proc.stdout}'
        raise RuntimeError(msg)

    audit_md_path = SUBMISSION_DIR / 'audit.md'
    if not audit_md_path.exists():
        msg = f'Missing expected output: {audit_md_path}'
        raise RuntimeError(msg)

    return audit_md_path


def _unpack_bundle(bundle: bytes, work_dir: Path) -> tuple[Path, str, str]:
    upload_zip_path = work_dir / 'upload.zip'
    key_payload: dict | None = None

    with tarfile.open(fileobj=io.BytesIO(bundle), mode='r:*') as tar:
        for member in tar.getmembers():
            fileobj = tar.extractfile(member)
            if fileobj is None:
                msg = f'Failed to extract bundle entry: {member.name}'
                raise RuntimeError(msg)

            data = fileobj.read()
            if member.name == 'upload.zip':
                upload_zip_path.write_bytes(data)
            else:
                key_payload = json.loads(data.decode('utf-8'))

    if key_payload is None:
        msg = 'Missing key.json in bundle'
        raise RuntimeError(msg)

    openai_token = key_payload.get('openai_token') or key_payload.get('openai_key')
    if not isinstance(openai_token, str) or not openai_token:
        msg = 'Missing openai_token in bundle'
        raise RuntimeError(msg)

    key_mode = key_payload.get('key_mode') or 'direct'
    if not isinstance(key_mode, str):
        key_mode = 'direct'
    key_mode = key_mode.strip().lower()
    if key_mode not in {'direct', 'proxy', 'proxy_static'}:
        key_mode = 'direct'

    if not upload_zip_path.exists():
        msg = 'Missing upload.zip in bundle'
        raise RuntimeError(msg)

    return upload_zip_path, openai_token, key_mode


async def main() -> None:
    logger.info('Requesting bundle...')
    async with AsyncClient() as client:
        response = await client.get(
            f'http://{SECRET_SVC_HOST}:{SECRET_SVC_PORT}/v1/bundles/{SECRET_REF}',
            headers={'X-Secrets-Token': SECRET_SVC_TOKEN},
        )
        response.raise_for_status()
        bundle = response.content

    logger.info(f'Got {len(bundle)} bytes of bundle, extracting..')
    report_payload = {
        'job_id': JOB_ID,
        'status': 'failed',
        'error': 'No audit generated',
    }

    with tempfile.TemporaryDirectory(prefix='evmbench-worker-') as tmpdir:
        work_dir = Path(tmpdir)
        upload_zip_path, openai_token, key_mode = _unpack_bundle(bundle, work_dir)

        if AUDIT_DIR.exists():
            shutil.rmtree(AUDIT_DIR)

        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(upload_zip_path, 'r') as zf:
            zf.extractall(AUDIT_DIR)  # noqa: S202

        logger.info('Extracted the bundle, running detect-only agent...')
        try:
            audit_md = _run_codex_detect(openai_token=openai_token, key_mode=key_mode)
            audit_text = audit_md.read_text()
            _extract_json_payload(audit_text)

            report_payload = {
                'job_id': JOB_ID,
                'status': 'succeeded',
                'report': audit_text,
            }
            logger.info('audit.md validated successfully')
        except Exception as err:  # noqa: BLE001
            report_payload = {
                'job_id': JOB_ID,
                'status': 'failed',
                'error': str(err),
            }
            logger.opt(exception=err).error('Unable to run detect-only agent')

    logger.info(f'{report_payload=}')
    try:
        async with AsyncClient() as client:
            response = await client.post(
                f'http://{RESULTSVC_HOST}:{RESULTSVC_PORT}/v1/results',
                json=report_payload,
                headers={'X-Results-Token': RESULTSVC_JOB_TOKEN},
                timeout=30,
            )
            response.raise_for_status()
    except Exception as err:  # noqa: BLE001
        logger.opt(exception=err).exception('Failed to upload result')


if __name__ == '__main__':
    run(main())
