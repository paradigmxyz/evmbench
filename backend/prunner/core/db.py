from datetime import UTC, datetime
from uuid import UUID

from loguru import logger
from sqlalchemy import select, update

from api.core.database import DatabaseManager
from api.models.job import Job, JobStatus
from prunner.core.config import settings


db = DatabaseManager(
    database_url=str(settings.DATABASE_DSN.get_secret_value()),
    pool_size=settings.PRUNNER_DATABASE_POOL_SIZE,
    max_overflow=settings.PRUNNER_DATABASE_MAX_OVERFLOW,
)


async def mark_job_failed(job_id: str, *, reason: str, log_action: str) -> None:
    try:
        job_uuid = UUID(job_id)
    except ValueError:
        logger.warning('Invalid job_id label job_id={}', job_id)
        return

    stmt = (
        update(Job)
        .where(Job.id == job_uuid, Job.status.in_((JobStatus.queued, JobStatus.running)))
        .values(status=JobStatus.failed, finished_at=datetime.now(tz=UTC), result_error=reason)
    )
    async with db.acquire() as session:
        result = await session.execute(stmt)
    if getattr(result, 'rowcount', 0):
        logger.info('Marked job failed due to {} job_id={}', log_action, job_id)


async def get_running_jobs() -> list[tuple[str, datetime | None]]:
    async with db.acquire() as session:
        result = await session.execute(select(Job.id, Job.started_at).where(Job.status == JobStatus.running))
    return [(str(job_id), started_at) for job_id, started_at in result.all()]
