"""In-process job dispatcher for local no-Docker runs.

Drop-in replacement for the RabbitMQ publisher surface (connect / close /
publish_job_start). Instead of publishing to the queue consumed by the
instancer, it runs the worker script (`docker/worker/init.py`) as a child
process of the API and watches it to completion.

This removes the RabbitMQ, instancer and Docker dependencies for local
single-user runs; the worker still fetches its bundle from secretsvc and
reports to resultsvc over HTTP like any other backend.

Requires BACKEND_WEB_WORKERS=1: dispatching state lives inside the API
process.
"""

import asyncio
import contextlib
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger
from sqlalchemy import update

from api.core.config import settings
from api.core.deps import get_database
from api.models.job import Job, JobStatus


_ERROR_LOG_TAIL_CHARS = 4000


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class LocalJobDispatcher:
    """Same interface as RabbitMQPublisher, but dispatches to child processes."""

    _queue: asyncio.Queue[dict] = field(default_factory=asyncio.Queue)
    _consumers: list[asyncio.Task[None]] = field(default_factory=list)
    _workers: set[asyncio.Task[None]] = field(default_factory=set)

    async def connect(self) -> None:
        if self._consumers:
            return
        for index in range(max(1, settings.BACKEND_LOCAL_MAX_CONCURRENT_JOBS)):
            self._consumers.append(asyncio.create_task(self._consumer(index)))

    async def close(self) -> None:
        for task in self._consumers:
            task.cancel()
        if self._consumers:
            await asyncio.gather(*self._consumers, return_exceptions=True)
        if self._workers:
            await asyncio.gather(*self._workers, return_exceptions=True)
        self._consumers = []

    async def publish_job_start(
        self, *, job_id: str, secret_ref: str, model: str, result_token: str, reasoning_effort: str | None = None
    ) -> None:
        await self._queue.put(
            {
                'type': 'job.start',
                'job_id': job_id,
                'secret_ref': secret_ref,
                'model': model,
                'reasoning_effort': reasoning_effort or 'medium',
                'result_token': result_token,
            }
        )
        logger.info(f'local dispatch: queued job {job_id} (model={model})')

    async def _consumer(self, index: int) -> None:
        while True:
            payload = await self._queue.get()
            try:
                # Run in a tracked task so close() can await in-flight workers.
                task = asyncio.create_task(self._run_worker(payload))
                self._workers.add(task)
                task.add_done_callback(self._workers.discard)
                await task
            except asyncio.CancelledError:
                raise
            except Exception as err:  # noqa: BLE001
                logger.opt(exception=err).error(f'local dispatch consumer {index} failed')
            finally:
                self._queue.task_done()

    async def _run_worker(self, payload: dict) -> None:
        job_id = payload['job_id']
        job_uuid = uuid.UUID(job_id)
        workspace = Path(settings.BACKEND_LOCAL_WORKERS_ROOT) / job_id
        agent_dir = workspace / 'agent'
        logs_dir = workspace / 'logs'
        agent_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)

        if not await self._mark_running(job_uuid):
            logger.warning(f'local dispatch: job {job_id} is not queued anymore, skipping')
            return

        env = self._worker_env(payload, agent_dir=agent_dir, logs_dir=logs_dir)
        worker_log_path = logs_dir / 'worker.log'

        logger.info(f'local dispatch: starting worker for job {job_id}')
        try:
            with worker_log_path.open('wb') as worker_log:
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    str(settings.BACKEND_LOCAL_WORKER_SCRIPT),
                    stdout=worker_log,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env,
                )
        except Exception as err:
            await self._mark_failed(
                job_uuid,
                error=f'failed to start local worker: {err}',
            )
            raise

        returncode = await proc.wait()
        if returncode == 0:
            # Success is reported by the worker to resultsvc; only intervene
            # when the job never left the running state.
            await self._fail_if_still_running(job_uuid, f'local worker exited without reporting (code={returncode})')
        else:
            await self._fail_if_still_running(
                job_uuid,
                f'local worker exited with code={returncode}: {self._log_tail(worker_log_path)}',
            )

    def _worker_env(self, payload: dict, *, agent_dir: Path, logs_dir: Path) -> dict[str, str]:
        env = os.environ.copy()
        env.update(
            {
                'JOB_ID': payload['job_id'],
                'AGENT_ID': payload['model'],
                'CODEX_REASONING_EFFORT': payload['reasoning_effort'],
                'SECRETSVC_HOST': settings.BACKEND_LOCAL_SECRETSVC_HOST,
                'SECRETSVC_PORT': str(settings.BACKEND_LOCAL_SECRETSVC_PORT),
                'SECRETSVC_REF': payload['secret_ref'],
                'SECRETSVC_TOKEN': settings.BACKEND_LOCAL_SECRETS_TOKEN_RO.get_secret_value(),
                'RESULTSVC_HOST': settings.BACKEND_LOCAL_RESULTSVC_HOST,
                'RESULTSVC_PORT': str(settings.BACKEND_LOCAL_RESULTSVC_PORT),
                'RESULTSVC_JOB_TOKEN': payload['result_token'],
                'EVM_BENCH_RUNNER_DIR': str(settings.BACKEND_LOCAL_RUNNER_DIR),
                'EVM_BENCH_RUNNER_SCRIPT': settings.BACKEND_LOCAL_RUNNER_SCRIPT,
                'AGENT_DIR': str(agent_dir),
                'AUDIT_DIR': str(agent_dir / 'audit'),
                'SUBMISSION_DIR': str(agent_dir / 'submission'),
                'LOGS_DIR': str(logs_dir),
            }
        )
        # The zcode runner refuses proxy mode; never inherit a stray proxy URL.
        env.pop('OAI_PROXY_BASE_URL', None)
        return env

    async def _mark_running(self, job_id: uuid.UUID) -> bool:
        db = get_database()
        async with db.acquire() as session:
            result = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == JobStatus.queued)
                .values(status=JobStatus.running, started_at=_utcnow())
            )
            await session.commit()
        return bool(result.rowcount)

    async def _fail_if_still_running(self, job_id: uuid.UUID, error: str) -> None:
        db = get_database()
        async with db.acquire() as session:
            result = await session.execute(
                update(Job)
                .where(Job.id == job_id, Job.status == JobStatus.running)
                .values(
                    status=JobStatus.failed,
                    result_error=error[:_ERROR_LOG_TAIL_CHARS],
                    finished_at=_utcnow(),
                    result_received_at=_utcnow(),
                )
            )
            await session.commit()
        if result.rowcount:
            logger.error(f'local dispatch: job {job_id} failed: {error[:200]}')

    async def _mark_failed(self, job_id: uuid.UUID, *, error: str) -> None:
        await self._fail_if_still_running(job_id, error)

    @staticmethod
    def _log_tail(path: Path) -> str:
        with contextlib.suppress(OSError):
            text = path.read_text(encoding='utf-8', errors='replace')
            return text[-_ERROR_LOG_TAIL_CHARS:]
        return '(no worker log)'
