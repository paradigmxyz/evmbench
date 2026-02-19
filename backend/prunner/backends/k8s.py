import asyncio
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import ParamSpec, TypeVar

from kubernetes import client, config
from loguru import logger

from prunner.backends.abc import BackendABC
from prunner.core.config import settings
from prunner.core.db import get_running_jobs, mark_job_failed


class Labels(StrEnum):
    MANAGED_BY = 'app.kubernetes.io/managed-by'
    JOB_ID = 'svmbench.osec.io/job-id'


P = ParamSpec('P')
R = TypeVar('R')


class K8sBackend(BackendABC):
    def __init__(self, args: dict[str, str]) -> None:
        super().__init__(args)

        auth_method = args.get('auth_method', 'kubeconfig')
        if auth_method == 'kubeconfig':
            config.load_kube_config()
        elif auth_method == 'incluster':
            config.load_incluster_config()
        else:
            msg = f'Unknown auth_method: {auth_method}'
            raise ValueError(msg)

        max_age_raw = args.get('max_container_age_seconds')
        if not max_age_raw:
            self._max_age_seconds = settings.PRUNNER_MAX_CONTAINER_AGE_SECONDS
        else:
            try:
                self._max_age_seconds = int(max_age_raw)
            except ValueError:
                self._max_age_seconds = settings.PRUNNER_MAX_CONTAINER_AGE_SECONDS

    @staticmethod
    async def _k8s(fn: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> R:
        return await asyncio.to_thread(fn, *args, **kwargs)

    async def run_once(self) -> None:
        now = datetime.now(tz=UTC)
        v1 = client.CoreV1Api()
        batch_v1 = client.BatchV1Api()

        seen_jobs = {}
        namespaces = await self._k8s(v1.list_namespace, label_selector=f'{Labels.MANAGED_BY}=svmbench')
        for namespace in namespaces.items:
            created_at = namespace.metadata.creation_timestamp
            job_id = namespace.metadata.labels.get(Labels.JOB_ID)
            seen_jobs[job_id] = True

            if now - created_at > timedelta(seconds=self._max_age_seconds):
                logger.info(f'Removing namespace {namespace.metadata.name}')
                await self._k8s(v1.delete_namespace, namespace.metadata.name)
                await mark_job_failed(job_id, reason='job ran out of time', log_action='timeout')
                continue

            jobs = await self._k8s(batch_v1.list_namespaced_job, namespace.metadata.name)

            # the job hasn't spawned yet
            if len(jobs.items) == 0:
                # or the job was lost for some reason...?
                if now - created_at > timedelta(seconds=30):
                    logger.info(f'Removing namespace {namespace.metadata.name}')
                    await self._k8s(v1.delete_namespace, namespace.metadata.name)
                    await mark_job_failed(job_id, reason='lost', log_action='lost')
                continue

            # TODO(trixter-osec): if the pod itself is in a bad state (image pull backoff, failed to spawn),
            #  it will not be caught (all of these are retryable, but may not be fixed by a retry...?)

            # it's still running, or we just scheduled it, and it's still in pending state
            if any(x.status.active is not None for x in jobs.items) or any(
                not (x.status.succeeded or x.status.failed) for x in jobs.items
            ):
                continue

            if any(x.status.failed is not None for x in jobs.items):
                await mark_job_failed(job_id, reason='crashed', log_action='crash')

            logger.info(f'Removing namespace {namespace.metadata.name}')
            await self._k8s(v1.delete_namespace, namespace.metadata.name)

        cutoff = datetime.now(tz=UTC) - timedelta(minutes=5)
        for job_id, started_at in await get_running_jobs():
            if started_at is None or started_at > cutoff:
                continue
            if job_id in seen_jobs:
                continue
            await mark_job_failed(job_id, reason='lost', log_action='lost')

    async def close(self) -> None:
        pass
