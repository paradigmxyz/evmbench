# ruff: noqa: PT009, PT027, SLF001, S106
import json
import os
import sys
import tempfile
import unittest
from importlib import import_module
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from test_shared_keys import REPO_ROOT, TEST_ENV, worker


INSTANCER_ENV = {**TEST_ENV, 'INSTANCER_SECRETS_TOKEN_RO': 'test-secret-token'}
with patch.dict(os.environ, INSTANCER_ENV, clear=True):
    rabbitmq = import_module('api.core.rabbitmq')
    consumer = import_module('instancer.core.consumer')
    docker_backend = import_module('instancer.backends.docker')
    k8s_backend = import_module('instancer.backends.k8s')
    backend_abc = import_module('instancer.backends.abc')


class ReasoningPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_effort_survives_queue_and_both_worker_launchers(self) -> None:
        for effort in (None, 'low', 'high', 'max'):
            with self.subTest(effort=effort):
                channel = MagicMock()
                channel.default_exchange.publish = AsyncMock()
                publisher = rabbitmq.RabbitMQPublisher(dsn='unused', queue='jobs', _channel=channel)
                await publisher.publish_job_start(
                    job_id='test',
                    secret_ref='ref',
                    model='codex-gpt-5.6-sol',
                    result_token='token',
                    reasoning_effort=effort,
                )
                body = channel.default_exchange.publish.await_args.args[0].body
                # Old queue messages omit the field entirely.
                if effort is None:
                    payload = json.loads(body)
                    del payload['reasoning_effort']
                    body = json.dumps(payload).encode()
                message = MagicMock(body=body, ack=AsyncMock(), reject=AsyncMock(), nack=AsyncMock())
                backend = AsyncMock()
                backend.start_worker.return_value = backend_abc.StartWorkerResult(worker_id='worker')
                with (
                    patch.object(consumer, 'workers_backend', backend),
                    patch.object(consumer, '_effective_max_concurrent_jobs', return_value=None),
                    patch.object(consumer, 'run_job_status_update', new_callable=AsyncMock),
                ):
                    await consumer.handle_job_start_message(message)
                message.ack.assert_awaited_once()
                options = backend.start_worker.await_args.args[0]
                self.assertEqual(options.reasoning_effort, effort or 'medium')

                docker = MagicMock()
                docker.containers.create = AsyncMock(return_value=MagicMock(id='worker', start=AsyncMock()))
                with patch.object(docker_backend, 'get_docker', return_value=docker):
                    await docker_backend.DockerBackend({}).start_worker(options)
                env = dict(item.split('=', 1) for item in docker.containers.create.await_args.kwargs['config']['Env'])
                self.assertEqual(env.get('CODEX_REASONING_EFFORT'), effort or 'medium')

                with patch.object(k8s_backend.config, 'load_kube_config'):
                    k8s = k8s_backend.K8sBackend({})

                async def call_k8s(fn: object, *_args: object) -> MagicMock:
                    if fn.__name__ == 'read_namespace':
                        raise k8s_backend.ApiException(status=404)
                    return MagicMock()

                with patch.object(k8s, '_k8s', new_callable=AsyncMock, side_effect=call_k8s) as api:
                    await k8s.start_worker(options)
                job = api.await_args.args[2]
                env = {item.name: item.value for item in job.spec.template.spec.containers[0].env}
                self.assertEqual(env.get('CODEX_REASONING_EFFORT'), effort or 'medium')

    async def test_queue_rejects_incompatible_or_malformed_effort(self) -> None:
        for effort in ('none', 'ultra', {'high': True}):
            with self.subTest(effort=effort):
                body = json.dumps(
                    {
                        'type': 'job.start',
                        'job_id': 'test',
                        'secret_ref': 'ref',
                        'model': 'codex-gpt-6-astra',
                        'result_token': 'token',
                        'reasoning_effort': effort,
                    }
                ).encode()
                message = MagicMock(body=body, ack=AsyncMock(), reject=AsyncMock())
                with patch.object(consumer, 'workers_backend', new_callable=AsyncMock) as backend:
                    await consumer.handle_job_start_message(message)
                message.reject.assert_awaited_once_with(requeue=False)
                backend.start_worker.assert_not_awaited()


class ReasoningRunnerTests(unittest.TestCase):
    def test_worker_passes_effort_to_codex_and_defaults_to_medium(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            codex = bin_dir / 'codex'
            codex.write_text(
                f'#!{sys.executable}\n'
                'import json, os, sys\n'
                'from pathlib import Path\n'
                'if sys.argv[1] == "login":\n'
                '    sys.stdin.read()\n'
                'else:\n'
                '    Path(os.environ["LOGS_DIR"], "args.json").write_text(json.dumps(sys.argv[1:]))\n'
                '    Path(os.environ["SUBMISSION_DIR"], "audit.md").write_text("{\\"vulnerabilities\\": []}")\n'
            )
            codex.chmod(0o755)
            timeout = bin_dir / 'timeout'
            timeout.write_text('#!/bin/sh\nshift 2\nexec "$@"\n')
            timeout.chmod(0o755)
            runner_dir = REPO_ROOT / 'backend/worker_runner'
            runner = root / 'run_codex_detect.sh'
            runner.write_bytes((runner_dir / 'run_codex_detect.sh').read_bytes())
            runner.chmod(0o755)  # The worker Dockerfile makes the runner executable.
            for name, value in {
                'AGENT_DIR': root,
                'SUBMISSION_DIR': root / 'submission',
                'LOGS_DIR': root / 'logs',
                'DETECT_MD_PATH': runner_dir / 'detect.md',
                'CODEX_RUNNER_SH': runner,
                'MODEL_MAP_PATH': runner_dir / 'model_map.json',
                'MODEL_KEY': 'codex-gpt-5.6-sol',
                'OAI_PROXY_BASE_URL': 'http://test.invalid',
            }.items():
                self.enterContext(patch.object(worker, name, value))

            for effort in (None, 'low', 'high', 'max'):
                for mode in ('direct', 'proxy'):
                    with self.subTest(effort=effort, mode=mode):
                        env = {'PATH': f'{bin_dir}:/usr/bin:/bin'}
                        if effort is not None:
                            env['CODEX_REASONING_EFFORT'] = effort
                        with patch.dict(os.environ, env, clear=True):
                            worker._run_codex_detect(openai_token='fake-key', key_mode=mode)
                        args = json.loads((root / 'logs/args.json').read_text())
                        self.assertEqual(args[args.index('--model') + 1], 'gpt-5.6-sol')
                        expected = effort or 'medium'
                        self.assertEqual(args[args.index('--config') + 1], f'model_reasoning_effort="{expected}"')

            with (
                patch.dict(
                    os.environ, {'PATH': f'{bin_dir}:/usr/bin:/bin', 'CODEX_REASONING_EFFORT': 'none'}, clear=True
                ),
                self.assertRaisesRegex(RuntimeError, 'invalid CODEX_REASONING_EFFORT'),
            ):
                worker._run_codex_detect(openai_token='fake-key', key_mode='direct')
