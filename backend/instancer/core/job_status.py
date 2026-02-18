import datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import update

from api.core.database import DatabaseManager
from api.models.job import Job, JobStatus
from instancer.core.config import settings


_db = DatabaseManager(
    database_url=str(settings.DATABASE_DSN.get_secret_value()),
    pool_size=settings.INSTANCER_DATABASE_POOL_SIZE,
    max_overflow=settings.INSTANCER_DATABASE_MAX_OVERFLOW,
)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


async def _apply_status(job_id: UUID, status: str) -> None:
    now = _now()
    if status == 'running':
        stmt = (
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.queued)
            .values(status=JobStatus.running, started_at=now)
        )
    elif status == 'succeeded':
        stmt = (
            update(Job)
            .where(Job.id == job_id, Job.status.in_((JobStatus.queued, JobStatus.running)))
            .values(status=JobStatus.succeeded, finished_at=now)
        )
    elif status == 'failed':
        stmt = (
            update(Job)
            .where(Job.id == job_id, Job.status.in_((JobStatus.queued, JobStatus.running)))
            .values(status=JobStatus.failed, finished_at=now)
        )
    else:
        logger.warning(f'Unknown status={status} for job_id={job_id}')
        return

    async with _db.acquire() as session:
        await session.execute(stmt)


async def run_job_status_update(payload: dict) -> None:
    job_id = payload.get('job_id')
    status = payload.get('status')
    if not isinstance(job_id, str) or not isinstance(status, str):
        logger.warning(f'Invalid payload={payload}')
        return

    try:
        job_uuid = UUID(job_id)
    except ValueError:
        logger.warning(f'Invalid job_id={job_id}')
        return

    logger.info(f'Applying status {status} to {job_uuid}')
    await _apply_status(job_uuid, status)
