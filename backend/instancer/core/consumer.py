import asyncio
from collections.abc import Awaitable, Callable

import aio_pika
import orjson
from aio_pika.abc import AbstractIncomingMessage, Arguments
from loguru import logger

from instancer.backends.abc import StartWorkerOptions
from instancer.core.config import settings
from instancer.core.impl import workers_backend
from instancer.core.job_status import run_job_status_update


def _job_dlq_name() -> str:
    if settings.RABBITMQ_QUEUE_DLQ:
        return settings.RABBITMQ_QUEUE_DLQ
    if settings.INSTANCER_JOB_DLQ:
        return settings.INSTANCER_JOB_DLQ
    return f'{settings.rabbitmq_queue_name}.dlq'


def _configured_max_concurrent_jobs() -> int | None:
    limit = settings.INSTANCER_MAX_CONCURRENT_JOBS
    if limit is None or limit <= 0:
        return None
    return limit


def _effective_max_concurrent_jobs() -> int | None:
    limit = _configured_max_concurrent_jobs()
    if limit is not None:
        return limit
    limit = workers_backend.default_max_concurrency()
    if limit is None or limit <= 0:
        return None
    return limit


def _job_queue_arguments() -> Arguments:
    if _configured_max_concurrent_jobs() is not None:
        return {}
    ttl_seconds = settings.RABBITMQ_QUEUE_TTL_SECONDS
    if ttl_seconds is None:
        ttl_seconds = settings.INSTANCER_JOB_TTL_SECONDS
    ttl_seconds = max(0, ttl_seconds)
    if ttl_seconds <= 0:
        return {}
    return {
        'x-message-ttl': ttl_seconds * 1000,
        'x-dead-letter-exchange': '',
        'x-dead-letter-routing-key': _job_dlq_name(),
    }


async def _wait_for_capacity(limit: int) -> None:
    poll_seconds = max(1, settings.INSTANCER_CAPACITY_POLL_SECONDS)
    while True:
        running = await workers_backend.running_workers()
        if running < limit:
            return
        logger.info(f'At capacity (running={running}, limit={limit}); waiting...')
        await asyncio.sleep(poll_seconds)


def _decode_payload(message: AbstractIncomingMessage) -> dict | None:
    try:
        payload = orjson.loads(message.body)
    except orjson.JSONDecodeError:
        logger.warning('Invalid message payload (not JSON).')
        return None
    if not isinstance(payload, dict):
        logger.warning(f'Invalid message payload type={type(payload).__name__}')
        return None
    return payload


def _is_expired_message(message: AbstractIncomingMessage) -> bool:
    headers = message.headers or {}
    deaths = headers.get('x-death')
    if not isinstance(deaths, list):
        return False
    return any(isinstance(death, dict) and death.get('reason') == 'expired' for death in deaths)


async def handle_job_start_message(message: AbstractIncomingMessage) -> None:
    payload = _decode_payload(message)
    if payload is None:
        await message.reject(requeue=False)
        return

    if payload.get('type') != 'job.start':
        logger.warning(f'Ignoring message with type={payload.get("type")}')
        await message.reject(requeue=False)
        return

    job_id = payload.get('job_id')
    secret_ref = payload.get('secret_ref')
    model = payload.get('model')
    result_token = payload.get('result_token')
    if (
        not isinstance(job_id, str)
        or not isinstance(secret_ref, str)
        or not isinstance(model, str)
        or not isinstance(result_token, str)
    ):
        logger.warning(f'Missing job_id/secret_ref/model/result_token in payload={payload}')
        await message.reject(requeue=False)
        return

    logger.info(f'Received job_id={job_id}')
    try:
        limit = _effective_max_concurrent_jobs()
        if limit is not None:
            await _wait_for_capacity(limit)
        start_result = await workers_backend.start_worker(
            StartWorkerOptions(
                job_id=job_id,
                secret_ref=secret_ref,
                model=model,
                result_token=result_token,
            )
        )
        if start_result.error:
            logger.error(f'Unable to start worker: {start_result.error}')
            await message.nack(requeue=True)
            return

        await run_job_status_update({'job_id': job_id, 'status': 'running'})
    except Exception as err:  # noqa: BLE001
        logger.opt(exception=err).warning(f'Unable to start worker for job_id={job_id}')
        await message.nack(requeue=True)
        return

    await message.ack()


async def handle_job_expired_message(message: AbstractIncomingMessage) -> None:
    payload = _decode_payload(message)
    if payload is None:
        await message.reject(requeue=False)
        return

    job_id = payload.get('job_id')
    if not isinstance(job_id, str):
        logger.warning(f'Missing job_id in payload={payload}')
        await message.reject(requeue=False)
        return

    if not _is_expired_message(message):
        logger.warning(f'Ignoring non-expired message in DLQ payload={payload}')
        await message.ack()
        return

    try:
        await run_job_status_update({'job_id': job_id, 'status': 'failed'})
    except Exception as err:  # noqa: BLE001
        logger.opt(exception=err).warning(f'Unable to mark expired job_id={job_id} as failed')
        await message.nack(requeue=True)
        return

    await message.ack()


async def _consume_queue(
    queue: aio_pika.abc.AbstractQueue,
    handler: Callable[[AbstractIncomingMessage], Awaitable[None]],
) -> None:
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            await handler(message)


async def consume() -> None:
    logger.info('Connecting...')
    connection = await aio_pika.connect_robust(settings.RABBITMQ_DSN.get_secret_value())
    logger.info('Connected! Waiting for messages')
    async with connection:
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=1)
        queue_arguments = _job_queue_arguments()
        dlq_queue = None
        if queue_arguments:
            dlq_queue = await channel.declare_queue(_job_dlq_name(), durable=True)

        queue = await channel.declare_queue(
            settings.rabbitmq_queue_name,
            durable=True,
            arguments=queue_arguments or None,
        )

        tasks = [asyncio.create_task(_consume_queue(queue, handle_job_start_message))]
        if dlq_queue is not None:
            tasks.append(asyncio.create_task(_consume_queue(dlq_queue, handle_job_expired_message)))

        await asyncio.gather(*tasks)
