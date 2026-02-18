import os
import uuid
from contextlib import suppress
from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from httpx import AsyncClient
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.const import ALLOWED_MODELS
from api.core.deps import OptionalTokenDep, TokenDep, get_db
from api.core.impl import auth_backend
from api.core.rabbitmq import RabbitMQPublisher, get_rabbitmq_publisher
from api.models.job import Job, JobStatus
from api.schemas.job import JobHistoryItem, JobStatusResponse, PatchJobForm, StartJobForm, StartJobResponse
from api.secrets.impl import secret_storage
from api.util.aes_gcm import derive_key, encrypt_token
from api.util.secrets_bundle import build_secret_bundle


router = APIRouter(prefix='/jobs', tags=['jobs'])


JobFormDep = Annotated[StartJobForm, Depends(StartJobForm.as_form)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db)]
PublisherDep = Annotated[RabbitMQPublisher, Depends(get_rabbitmq_publisher)]


async def _queue_position(session: AsyncSession, job: Job) -> int | None:
    if job.status != JobStatus.queued or job.created_at is None:
        return None
    stmt = (
        select(func.count())
        .select_from(Job)
        .where(
            Job.status == JobStatus.queued,
            or_(
                Job.created_at < job.created_at,
                and_(Job.created_at == job.created_at, Job.id < job.id),
            ),
        )
    )
    count = await session.scalar(stmt)
    return int(count or 0) + 1


async def _require_no_active_job(*, session: AsyncSession, user_id: str) -> None:
    if not auth_backend:
        return

    existing_job_id = await session.scalar(
        select(Job.id)
        .where(
            Job.user_id == user_id,
            Job.status.in_([JobStatus.queued, JobStatus.running]),
        )
        .limit(1)
    )
    if existing_job_id is not None:
        raise HTTPException(
            status_code=409,
            detail='You already have a queued or running job',
        )


def _require_allowed_model(model: str) -> None:
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=401, detail='Model is not allowed')


def _resolve_openai_key(form: StartJobForm) -> str | None:
    # Determine which OpenAI key mode to use:
    # 1. BACKEND_USE_PROXY_STATIC_KEY: Use "STATIC" marker, real key stays in oai_proxy only
    # 2. BACKEND_STATIC_OAI_KEY: Backend knows the key (legacy mode)
    # 3. User-provided key
    static_key = settings.BACKEND_STATIC_OAI_KEY.get_secret_value() if settings.BACKEND_STATIC_OAI_KEY else None
    return static_key or form.openai_key


async def _maybe_validate_user_key(*, form: StartJobForm, openai_key: str | None) -> None:
    # Validate user-provided keys (skip if using static keys)
    if settings.BACKEND_USE_PROXY_STATIC_KEY:
        return
    if settings.BACKEND_STATIC_OAI_KEY is not None:
        return
    if not form.openai_key:
        return
    if not openai_key:
        return

    async with AsyncClient() as client:
        response = await client.get(
            'https://api.openai.com/v1/models',
            headers={
                'Authorization': f'Bearer {openai_key}',
            },
        )
        if response.status_code != HTTPStatus.OK:
            raise HTTPException(status_code=401, detail='Invalid API key')


def _encode_openai_token(*, openai_key: str, use_proxy_static: bool, use_proxy_tokens: bool) -> tuple[str, str]:
    """Return (openai_token, key_mode) for the worker bundle."""
    if use_proxy_static:
        # Marker token (not a real credential). The proxy substitutes its static key.
        return 'STATIC', 'proxy_static'

    if use_proxy_tokens:
        if settings.OAI_PROXY_AES_KEY is None:
            raise HTTPException(status_code=500, detail='OAI_PROXY_AES_KEY must be set for proxy mode')
        return (
            encrypt_token(
                openai_key,
                key=derive_key(settings.OAI_PROXY_AES_KEY.get_secret_value()),
            ),
            'proxy',
        )

    return openai_key, 'direct'


@router.post('/start')
async def start_job(
    form: JobFormDep,
    session: DbSessionDep,
    publisher: PublisherDep,
    token: TokenDep,
) -> StartJobResponse:
    await _require_no_active_job(session=session, user_id=token.user_id)
    _require_allowed_model(form.model)

    use_proxy_static = settings.BACKEND_USE_PROXY_STATIC_KEY
    use_proxy_tokens = settings.BACKEND_OAI_KEY_MODE == 'proxy'
    openai_key = _resolve_openai_key(form)

    if not use_proxy_static and not openai_key:
        raise HTTPException(status_code=412, detail='openai_key is required')

    await _maybe_validate_user_key(form=form, openai_key=openai_key)

    job_id = uuid.uuid4()
    secret_ref = os.urandom(32).hex()
    result_token = os.urandom(32).hex()

    openai_token, key_mode = _encode_openai_token(
        openai_key=openai_key or '',
        use_proxy_static=use_proxy_static,
        use_proxy_tokens=use_proxy_tokens,
    )

    try:
        bundle = build_secret_bundle(upload=form.file, openai_token=openai_token, key_mode=key_mode)
        await secret_storage.save_secret(secret_ref, bundle)

        job = Job(
            id=job_id,
            status=JobStatus.queued,
            user_id=token.user_id,
            secret_ref=secret_ref,
            result_token=result_token,
            model=form.model,
            file_name=(form.file.filename or 'files.zip')[:128],
        )
        session.add(job)

        await session.commit()
        try:
            await publisher.publish_job_start(
                job_id=str(job_id),
                secret_ref=secret_ref,
                model=form.model,
                result_token=result_token,
            )
        except Exception as err:
            with suppress(Exception):
                await secret_storage.delete_secret(secret_ref)
            await session.delete(job)
            await session.commit()
            raise HTTPException(
                status_code=502,
                detail='Failed to enqueue job',
            ) from err

        return StartJobResponse(job_id=job_id, status=job.status)
    finally:
        await form.file.close()


@router.get('/history')
async def get_job_history(
    session: DbSessionDep,
    token: TokenDep,
) -> list[JobHistoryItem]:
    if not auth_backend:
        raise HTTPException(status_code=404, detail='Not found')

    stmt = select(Job).where(Job.user_id == token.user_id).order_by(Job.created_at.desc(), Job.id.desc())
    jobs = await session.scalars(stmt)
    return [JobHistoryItem.model_validate(job) for job in jobs.all()]


@router.get('/{job_id}')
async def get_job(
    job_id: uuid.UUID,
    session: DbSessionDep,
    token: OptionalTokenDep,
) -> JobStatusResponse:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail='Job not found')
    if not job.public and ((not token) or (auth_backend and job.user_id != token.user_id)):
        raise HTTPException(status_code=404, detail='Job not found')
    response = JobStatusResponse.model_validate(job)
    response.queue_position = await _queue_position(session, job)
    return response


@router.patch('/{job_id}')
async def patch_job(
    job_id: uuid.UUID,
    session: DbSessionDep,
    token: TokenDep,
    form: PatchJobForm,
) -> JobStatusResponse:
    # Does not really matter for instances with no authorization
    if not auth_backend:
        raise HTTPException(status_code=404, detail='Not found')

    job = await session.get(Job, job_id)
    if not job or job.user_id != token.user_id:
        raise HTTPException(status_code=404, detail='Job not found')

    job.public = form.public
    await session.commit()
    await session.refresh(job)
    response = JobStatusResponse.model_validate(job)
    response.queue_position = await _queue_position(session, job)
    return response
