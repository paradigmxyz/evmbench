# ruff: noqa: PT009, SLF001
import io
import json
import os
import tarfile
import unittest
import zipfile
from importlib import import_module
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient


TEST_ENV = {
    'DATABASE_DSN': 'postgresql+asyncpg://localhost/test',
    'RABBITMQ_DSN': 'amqp://localhost/',
    'BACKEND_JWT_SECRET': 'test-jwt',
    'BACKEND_SECRETS_BACKEND': 'http',
    'BACKEND_STATIC_OAI_KEY': 'test-backend-shared-key',
    'BACKEND_USE_PROXY_STATIC_KEY': 'true',
    'OAI_PROXY_STATIC_KEY': 'test-proxy-shared-key',
    'OAI_PROXY_AES_KEY': 'test-encryption-key',
    'AUTH_BACKEND': '',
}

# Settings are initialized at import time. Never read credentials from the caller's environment.
with patch.dict(os.environ, TEST_ENV, clear=True):
    api_config = import_module('api.core.config')
    proxy_config = import_module('oai_proxy.core.config')
    jobs = import_module('api.routers.v1.jobs')
    integration = import_module('api.routers.v1.integration')
    job_schema = import_module('api.schemas.job')
    proxy = import_module('oai_proxy.routers.catch_all')
    aes = import_module('api.util.aes_gcm')

REPO_ROOT = Path(__file__).resolve().parents[2]
worker_spec = spec_from_file_location('worker_init', REPO_ROOT / 'backend/docker/worker/init.py')
worker = module_from_spec(worker_spec)
worker_spec.loader.exec_module(worker)


def upload_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('Example.sol', 'pragma solidity ^0.8.0; contract Example {}')
    return buffer.getvalue()


class SharedKeyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.enterContext(patch.dict(os.environ, TEST_ENV, clear=True))
        self.api_settings = api_config.Settings(_env_file=None)
        self.proxy_settings = proxy_config.Settings(_env_file=None)
        for module in (jobs, integration, job_schema):
            self.enterContext(patch.object(module, 'settings', self.api_settings))
        self.enterContext(patch.object(proxy, 'settings', self.proxy_settings))
        proxy._get_static_key.cache_clear()
        proxy._aesgcm_key.cache_clear()
        self.addCleanup(proxy._get_static_key.cache_clear)
        self.addCleanup(proxy._aesgcm_key.cache_clear)

        self.session = MagicMock()
        self.session.commit = AsyncMock()
        self.publisher = AsyncMock()
        self.storage = AsyncMock()
        self.enterContext(patch.object(jobs, 'secret_storage', self.storage))
        app = FastAPI()
        app.include_router(jobs.router, prefix='/v1')
        app.include_router(integration.router, prefix='/v1')
        app.dependency_overrides[jobs.get_db] = lambda: self.session
        app.dependency_overrides[jobs.get_rabbitmq_publisher] = lambda: self.publisher
        self.client = self.enterContext(TestClient(app))

        proxy_app = FastAPI()
        proxy_app.include_router(proxy.router)
        self.proxy_client = self.enterContext(TestClient(proxy_app))

    def test_shared_keys_disabled_by_default_and_explicit_false(self) -> None:
        for value in (None, 'false'):
            with self.subTest(value=value):
                if value is not None:
                    os.environ['OAI_SHARED_KEY_ENABLED'] = value
                backend_settings = api_config.Settings(_env_file=None)
                proxy_settings = proxy_config.Settings(_env_file=None)
                self.assertIsNone(backend_settings.BACKEND_STATIC_OAI_KEY)
                self.assertFalse(backend_settings.BACKEND_USE_PROXY_STATIC_KEY)
                self.assertIsNone(proxy_settings.OAI_PROXY_STATIC_KEY)
        response = self.client.get('/v1/integration/frontend')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['key_predefined'])

    def test_job_requires_user_key_despite_legacy_settings(self) -> None:
        for key in (None, '', '   '):
            with self.subTest(key=key):
                data = {'model': 'codex-gpt-5.2'}
                if key is not None:
                    data['openai_key'] = key
                response = self.client.post(
                    '/v1/jobs/start',
                    data=data,
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 412)
        self.session.add.assert_not_called()
        self.storage.save_secret.assert_not_awaited()
        self.publisher.publish_job_start.assert_not_awaited()

    def test_user_key_validated_and_bundled_in_both_modes(self) -> None:
        for mode in ('direct', 'proxy'):
            with self.subTest(mode=mode), patch.object(jobs, 'AsyncClient') as client_factory:
                self.api_settings.BACKEND_OAI_KEY_MODE = mode
                upstream = client_factory.return_value.__aenter__.return_value
                upstream.get.return_value = httpx.Response(200)
                response = self.client.post(
                    '/v1/jobs/start',
                    data={'model': 'codex-gpt-5.2', 'openai_key': 'test-user-key'},
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 200, response.text)
                upstream.get.assert_awaited_once_with(
                    'https://api.openai.com/v1/models',
                    headers={'Authorization': 'Bearer test-user-key'},
                )
                bundle = self.storage.save_secret.await_args.args[1]
                with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
                    payload = json.load(archive.extractfile('key.json'))
                self.assertEqual(payload['key_mode'], mode)
                if mode == 'proxy':
                    payload['openai_token'] = aes.decrypt_token(
                        payload['openai_token'],
                        key=aes.derive_key(TEST_ENV['OAI_PROXY_AES_KEY']),
                    )
                self.assertEqual(payload['openai_token'], 'test-user-key')
        self.assertEqual(self.publisher.publish_job_start.await_count, 2)

    def test_invalid_user_key_is_rejected(self) -> None:
        with patch.object(jobs, 'AsyncClient') as client_factory:
            upstream = client_factory.return_value.__aenter__.return_value
            upstream.get.return_value = httpx.Response(401)
            response = self.client.post(
                '/v1/jobs/start',
                data={'model': 'codex-gpt-5.2', 'openai_key': 'invalid-user-key'},
                files={'file': ('example.zip', upload_zip())},
            )
        self.assertEqual(response.status_code, 401)
        self.session.add.assert_not_called()
        self.storage.save_secret.assert_not_awaited()
        self.publisher.publish_job_start.assert_not_awaited()

    def test_every_ui_model_can_be_submitted_and_resolved_by_worker(self) -> None:
        models = json.loads((REPO_ROOT / 'frontend/src/data/models.json').read_text())
        with patch.object(worker, 'MODEL_MAP_PATH', REPO_ROOT / 'backend/worker_runner/model_map.json'):
            model_map = worker._load_model_map()
        model_ids = [model['id'] for model in models]
        self.assertEqual(len(model_ids), len(set(model_ids)))
        self.assertEqual(set(model_ids), jobs.ALLOWED_MODELS)
        self.assertEqual(set(model_ids), set(model_map))

        for model_id in model_ids:
            with self.subTest(model=model_id), patch.object(jobs, 'AsyncClient') as client_factory:
                upstream = client_factory.return_value.__aenter__.return_value
                upstream.get.return_value = httpx.Response(200)
                response = self.client.post(
                    '/v1/jobs/start',
                    data={'model': model_id, 'openai_key': 'test-user-key'},
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(self.session.add.call_args.args[0].model, model_id)
                queued_model = self.publisher.publish_job_start.await_args.kwargs['model']
                self.assertEqual(queued_model, model_id)
                expected_model = (
                    'gpt-5.2-2025-12-11' if model_id == 'codex-gpt-5.2' else model_id.removeprefix('codex-')
                )
                self.assertEqual(
                    worker._resolve_codex_model(model_key=queued_model, model_map=model_map),
                    expected_model,
                )
                self.assertEqual(self.session.add.call_args.args[0].reasoning_effort, 'medium')
                self.assertEqual(self.publisher.publish_job_start.await_args.kwargs['reasoning_effort'], 'medium')

    def test_every_ui_reasoning_choice_is_saved_and_queued(self) -> None:
        models = json.loads((REPO_ROOT / 'frontend/src/data/models.json').read_text())
        for model in models:
            self.assertEqual(model['reasoningEfforts'], list(job_schema.MODEL_REASONING_EFFORTS[model['id']]))
            for effort in model['reasoningEfforts']:
                with self.subTest(model=model['id'], effort=effort), patch.object(jobs, 'AsyncClient') as factory:
                    factory.return_value.__aenter__.return_value.get.return_value = httpx.Response(200)
                    response = self.client.post(
                        '/v1/jobs/start',
                        data={'model': model['id'], 'reasoning_effort': effort, 'openai_key': 'test-user-key'},
                        files={'file': ('example.zip', upload_zip())},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertEqual(self.session.add.call_args.args[0].reasoning_effort, effort)
                    self.assertEqual(self.publisher.publish_job_start.await_args.kwargs['reasoning_effort'], effort)

    def test_invalid_reasoning_combinations_are_rejected_before_key_validation(self) -> None:
        for model, effort in (
            ('codex-gpt-5.2', 'max'),
            ('codex-gpt-5.3-codex', 'none'),
            ('codex-gpt-6-astra', 'none'),
            ('codex-gpt-6-astra', 'ultra'),
            ('codex-gpt-5.6-sol', 'unknown'),
        ):
            with self.subTest(model=model, effort=effort), patch.object(jobs, 'AsyncClient') as factory:
                response = self.client.post(
                    '/v1/jobs/start',
                    data={'model': model, 'reasoning_effort': effort, 'openai_key': 'test-user-key'},
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 412, response.text)
                self.assertIn('Reasoning level', response.json()['detail'])
                factory.assert_not_called()
        self.session.add.assert_not_called()
        self.publisher.publish_job_start.assert_not_awaited()

    def test_unsupported_model_is_rejected_before_key_validation(self) -> None:
        for model in ('unsupported-model', 'codex-gpt-5.1-codex-max', 'codex-gpt-5.4-mini'):
            with self.subTest(model=model), patch.object(jobs, 'AsyncClient') as client_factory:
                response = self.client.post(
                    '/v1/jobs/start',
                    data={'model': model, 'openai_key': 'test-user-key'},
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 401)
                client_factory.assert_not_called()
        self.session.add.assert_not_called()
        self.publisher.publish_job_start.assert_not_awaited()

    def test_none_reasoning_is_rejected_for_every_model(self) -> None:
        for model in jobs.ALLOWED_MODELS:
            with self.subTest(model=model), patch.object(jobs, 'AsyncClient') as client_factory:
                response = self.client.post(
                    '/v1/jobs/start',
                    data={'model': model, 'reasoning_effort': 'none', 'openai_key': 'test-user-key'},
                    files={'file': ('example.zip', upload_zip())},
                )
                self.assertEqual(response.status_code, 412)
                client_factory.assert_not_called()
        self.session.add.assert_not_called()
        self.publisher.publish_job_start.assert_not_awaited()

    def test_static_proxy_token_rejected_without_upstream_request(self) -> None:
        with patch.object(proxy.httpx, 'AsyncClient') as client_factory:
            response = self.proxy_client.post('/v1/responses', headers={'Authorization': 'Bearer STATIC'})
        self.assertEqual(response.status_code, 501)
        self.assertEqual(response.json()['detail'], 'Static key not configured on proxy')
        client_factory.assert_not_called()

    def test_encrypted_user_key_still_forwarded(self) -> None:
        requests = []

        def upstream(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, stream=httpx.ByteStream(b'{"ok":true}'))

        client = httpx.AsyncClient(transport=httpx.MockTransport(upstream))
        token = aes.encrypt_token('test-user-key', key=aes.derive_key(TEST_ENV['OAI_PROXY_AES_KEY']))
        with patch.object(proxy.httpx, 'AsyncClient', return_value=client):
            response = self.proxy_client.post(
                '/v1/responses',
                headers={'Authorization': f'Bearer {token}'},
                json={'model': 'test-model'},
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ok': True})
        self.assertEqual(len(requests), 1)
        self.assertEqual(str(requests[0].url), 'https://api.openai.com/v1/responses')
        self.assertEqual(requests[0].headers['authorization'], 'Bearer test-user-key')

    def test_shared_access_requires_explicit_opt_in(self) -> None:
        os.environ['OAI_SHARED_KEY_ENABLED'] = 'true'
        backend_settings = api_config.Settings(_env_file=None)
        proxy_settings = proxy_config.Settings(_env_file=None)
        self.assertTrue(backend_settings.BACKEND_USE_PROXY_STATIC_KEY)
        self.assertEqual(backend_settings.BACKEND_STATIC_OAI_KEY.get_secret_value(), TEST_ENV['BACKEND_STATIC_OAI_KEY'])
        with patch.object(integration, 'settings', backend_settings):
            self.assertTrue(self.client.get('/v1/integration/frontend').json()['key_predefined'])
        with patch.object(proxy, 'settings', proxy_settings):
            self.assertEqual(proxy._resolve_openai_key('STATIC'), TEST_ENV['OAI_PROXY_STATIC_KEY'])
