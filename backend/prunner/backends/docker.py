import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from functools import cache

from aiodocker import Docker
from loguru import logger

from prunner.backends.abc import BackendABC
from prunner.core.config import settings
from prunner.core.db import get_running_jobs, mark_job_failed


STOPPED_STATES = {'exited', 'dead', 'created'}


class Labels(StrEnum):
    MANAGED_BY = 'io.osec.managed_by'
    JOB_ID = 'io.osec.job_id'
    STARTED_AT = 'io.osec.started_at'


# NOTE: workaround for not having an async context during import-time
@cache
def get_docker() -> Docker:
    return Docker()


class DockerBackend(BackendABC):
    def __init__(self, args: dict[str, str]) -> None:
        super().__init__(args)
        self._manager_name = args.get('manager_name', settings.PRUNNER_MANAGER_NAME)
        max_age_raw = args.get('max_container_age_seconds')
        if not max_age_raw:
            self._max_age_seconds = settings.PRUNNER_MAX_CONTAINER_AGE_SECONDS
        else:
            try:
                self._max_age_seconds = int(max_age_raw)
            except ValueError:
                self._max_age_seconds = settings.PRUNNER_MAX_CONTAINER_AGE_SECONDS

    async def close(self) -> None:
        await get_docker().close()

    async def run_once(self) -> None:
        containers = await self._list_managed_containers()
        if not containers:
            return

        stopped_containers, job_containers, timed_out_jobs = self._classify_containers(containers)

        for container_id, job_id in stopped_containers:
            await self._remove_container(container_id, job_id=job_id, reason='stopped')

        for job_id in timed_out_jobs:
            await self._kill_job_containers(job_id, job_containers)
            await mark_job_failed(job_id, reason='job ran out of time', log_action='timeout')

        await self._mark_lost_jobs(job_containers)

    async def _list_managed_containers(self) -> list:
        filters = {
            'label': [f'{Labels.MANAGED_BY}={self._manager_name}'],
        }
        return await get_docker().containers.list(all=True, filters=filters)

    @staticmethod
    async def _remove_container(container_id: str, *, job_id: str | None, reason: str) -> None:
        try:
            container = get_docker().containers.container(container_id)
            await container.delete(force=True)
            logger.info('Removed container id={} reason={} job_id={}', container_id, reason, job_id)
        except Exception as exc:  # noqa: BLE001
            logger.opt(exception=exc).warning(
                'Failed to remove container id={} reason={} job_id={}',
                container_id,
                reason,
                job_id,
            )
            return

        if reason == 'stopped' and job_id:
            await mark_job_failed(job_id, reason='crashed', log_action='crash')

    async def _kill_job_containers(self, job_id: str, job_containers: dict[str, list[str]]) -> None:
        docker = get_docker()
        container_ids = job_containers.get(job_id, [])
        if not container_ids:
            filters = {
                'label': [
                    f'{Labels.MANAGED_BY}={self._manager_name}',
                    f'{Labels.JOB_ID}={job_id}',
                ],
            }
            container_ids = [info.id for info in await docker.containers.list(all=True, filters=filters)]

        for container_id in container_ids:
            try:
                container = docker.containers.container(container_id)
                await container.kill()
            except Exception as exc:  # noqa: BLE001
                logger.opt(exception=exc).warning(
                    'Failed to kill container id={} job_id={}',
                    container_id,
                    job_id,
                )
            await self._remove_container(container_id, job_id=job_id, reason='timeout')

    def _classify_containers(
        self,
        containers: list,
    ) -> tuple[list[tuple[str, str | None]], dict[str, list[str]], set[str]]:
        now = time.time()
        stopped_containers: list[tuple[str, str | None]] = []
        job_containers: dict[str, list[str]] = defaultdict(list)
        timed_out_jobs: set[str] = set()

        for info in containers:
            container_id = info.id
            if not container_id:
                continue

            labels = info['Labels'] or {}
            job_id = labels.get(Labels.JOB_ID)
            if job_id:
                job_containers[job_id].append(container_id)

            state = (info['State'] or '').lower()
            if state in STOPPED_STATES:
                stopped_containers.append((container_id, job_id))
                continue

            if self._max_age_seconds <= 0 or not job_id:
                continue

            started_raw = labels.get(Labels.STARTED_AT)
            if not started_raw:
                continue

            try:
                started_at = int(started_raw)
            except ValueError:
                logger.warning(
                    'Invalid started_at label for container id={} started_at={}',
                    container_id,
                    started_raw,
                )
                continue

            if now - started_at > self._max_age_seconds:
                timed_out_jobs.add(job_id)

        return stopped_containers, job_containers, timed_out_jobs

    async def _mark_lost_jobs(self, job_containers: dict[str, list[str]]) -> None:
        running_jobs = await get_running_jobs()
        cutoff = datetime.now(tz=UTC) - timedelta(minutes=5)
        for job_id, started_at in running_jobs:
            if started_at is None or started_at > cutoff:
                continue
            if job_id in job_containers:
                continue
            if await self._job_has_container(job_id):
                continue
            await mark_job_failed(job_id, reason='lost', log_action='lost')

    async def _job_has_container(self, job_id: str) -> bool:
        docker = get_docker()
        filters = {
            'label': [f'{Labels.JOB_ID}={job_id}'],
        }
        containers = await docker.containers.list(all=True, filters=filters)
        return bool(containers)
