try:
    from uvloop import run  # type: ignore[unresolved-import]
except ImportError:
    from asyncio import run
from asyncio import sleep

from loguru import logger

from prunner.core.cleanup import mark_gap_queued_jobs
from prunner.core.config import settings
from prunner.core.impl import prunner_backend


async def amain() -> None:
    logger.info(
        'Starting prunner (backend={}, args={})',
        settings.PRUNNER_BACKEND,
        settings.PRUNNER_BACKEND_ARGUMENTS,
    )
    try:
        while True:
            try:
                await prunner_backend.run_once()
            except Exception as exc:  # noqa: BLE001
                logger.opt(exception=exc).error('Prunner tick failed')
            try:
                await mark_gap_queued_jobs(
                    max_age_seconds=settings.PRUNNER_MAX_CONTAINER_AGE_SECONDS * 3,
                )
            except Exception as exc:  # noqa: BLE001
                logger.opt(exception=exc).error('Prunner gap cleanup failed')
            await sleep(settings.PRUNNER_POLL_SECONDS)
    finally:
        await prunner_backend.close()


def main() -> None:
    run(amain())


if __name__ == '__main__':
    main()
