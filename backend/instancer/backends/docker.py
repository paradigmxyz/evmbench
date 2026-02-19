import os
from contextlib import suppress
from datetime import UTC, datetime
from enum import StrEnum
from functools import cache

from aiodocker import Docker

from instancer.backends.abc import BackendABC, StartWorkerOptions, StartWorkerResult
from instancer.core.config import settings


# NOTE: workaround for not having an async context during import-time
@cache
def get_docker() -> Docker:
    return Docker()


class Labels(StrEnum):
    MANAGED_BY = 'io.osec.managed_by'
    JOB_ID = 'io.osec.job_id'
    STARTED_AT = 'io.osec.started_at'
    KIND = 'io.osec.kind'


def ts() -> int:
    return int(datetime.now(tz=UTC).timestamp())


class DockerBackend(BackendABC):
    def __init__(self, args: dict[str, str]) -> None:
        super().__init__(args)
        self._secretsvc_name = args.get('secretsvc_name', 'secretsvc')
        self._shared_network = args.get('shared_network', 'shared_network')

    async def start_worker(self, options: StartWorkerOptions) -> StartWorkerResult:
        docker = get_docker()
        env: dict[str, str] = {
            'SECRETSVC_HOST': settings.INSTANCER_SECRETSVC_HOST,
            'SECRETSVC_PORT': str(settings.INSTANCER_SECRETSVC_PORT),
            'SECRETSVC_REF': options.secret_ref,
            'SECRETSVC_TOKEN': settings.INSTANCER_SECRETS_TOKEN_RO.get_secret_value(),
            'RESULTSVC_HOST': settings.INSTANCER_RESULTSVC_HOST,
            'RESULTSVC_PORT': str(settings.INSTANCER_RESULTSVC_PORT),
            'RESULTSVC_JOB_TOKEN': options.result_token,
            'JOB_ID': options.job_id,
            'AGENT_ID': options.model,
        }
        if settings.INSTANCER_OAI_PROXY_BASE_URL:
            env['OAI_PROXY_BASE_URL'] = settings.INSTANCER_OAI_PROXY_BASE_URL

        container = await docker.containers.create(
            config={
                'Hostname': 'hi',
                'Image': settings.INSTANCER_WORKER_IMAGE,
                'Env': [f'{k}={v}' for k, v in env.items()],
                'Labels': {
                    Labels.MANAGED_BY: settings.INSTANCER_MANAGER_NAME,
                    Labels.JOB_ID: options.job_id,
                    Labels.STARTED_AT: str(ts()),
                },
                'HostConfig': {
                    'RestartPolicy': {
                        'Name': 'no',
                    },
                    'ReadOnlyRootFs': False,
                    'SecurityOpt': ['no-new-privileges'],
                    'Memory': 1 * 1024 * 1024 * 1024,  # 1gb should be fine surely?
                    'MemorySwap': 1 * 1024 * 1024 * 1024,
                    'NanoCpus': int(1_000_000_000 * 0.3),  # since we're limiting to cpu_count() * 3
                    'PidsLimit': 1024,
                    'CapAdd': [],
                    'CapDrop': ['ALL'],
                    'Ulimits': [
                        {'Name': 'nofile', 'Soft': 131_072, 'Hard': 131_072},
                    ],
                },
                'NetworkingConfig': {
                    'EndpointsConfig': {
                        self._shared_network: {},
                    }
                },
            },
            name=f'svmbench-worker-{options.job_id}',
        )

        try:
            await container.start()
        except Exception:
            with suppress(BaseException):
                await container.delete(force=True)
            raise

        return StartWorkerResult(worker_id=container.id)

    async def running_workers(self) -> int:
        docker = get_docker()
        containers = await docker.containers.list(
            all=False,
            filters={
                'label': [f'{Labels.MANAGED_BY}={settings.INSTANCER_MANAGER_NAME}'],
            },
        )
        return len(containers)

    def default_max_concurrency(self) -> int | None:
        return max(1, os.cpu_count() or 1) * 3
