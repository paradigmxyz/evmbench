from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import and_, or_, select, update

from api.models.job import Job, JobStatus
from prunner.core.db import db


# NOTE(es3n1n): Best (and at the same time low) effort cleanup;
# Ideally we'll need to implement:
# * an outbox with a separate producer on the backend
# * track the state in outbox instead of yolo publishing to rabbitmq
# * compare states


async def mark_gap_queued_jobs(*, max_age_seconds: int) -> None:
    if max_age_seconds <= 0:
        return

    async with db.acquire() as session:
        newest_non_queued = await session.execute(
            select(Job.created_at, Job.id)
            .where(Job.status != JobStatus.queued, Job.created_at.is_not(None))
            .order_by(Job.created_at.desc(), Job.id.desc())
            .limit(1)
        )
        newest_non_queued_row = newest_non_queued.first()
        if newest_non_queued_row is None:
            return
        newest_non_queued_created_at, newest_non_queued_id = newest_non_queued_row

        now = datetime.now(tz=UTC)
        cutoff = now - timedelta(seconds=max_age_seconds)
        stmt = (
            update(Job)
            .where(
                Job.status == JobStatus.queued,
                Job.created_at.is_not(None),
                or_(
                    Job.created_at < newest_non_queued_created_at,
                    and_(  # tiebreaker
                        Job.created_at == newest_non_queued_created_at,
                        Job.id < newest_non_queued_id,
                    ),
                ),
                Job.created_at < cutoff,
            )
            .values(
                status=JobStatus.failed,
                finished_at=now,
                result_error='found in gap',
            )
        )
        result = await session.execute(stmt)

    if getattr(result, 'rowcount', 0):
        logger.info(
            'Marked queued jobs as failed due to gap (max_age_seconds={})',
            max_age_seconds,
        )
