import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from loguru import logger
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.job import Job, JobStatus
from resultsvc.core.deps import get_db


router = APIRouter(prefix='/v1')


class ReportPayload(BaseModel):
    job_id: UUID
    status: Literal['succeeded', 'failed']
    report: str | None = None
    error: str | None = None

    @model_validator(mode='after')
    def _validate_report(self) -> 'ReportPayload':
        if self.status == 'succeeded' and self.report is None:
            msg = 'report is required when status is succeeded'
            raise ValueError(msg)
        if self.status == 'failed' and self.report is None and not self.error:
            msg = 'error or report is required when status is failed'
            raise ValueError(msg)
        return self


class ReportModel(BaseModel):
    @staticmethod
    def _normalize_severity(value: str) -> str:
        v = (value or '').strip().lower()
        if v.startswith('crit'):
            return 'critical'
        if v.startswith('hi'):
            return 'high'
        if v.startswith('med'):
            return 'medium'
        if v.startswith('lo'):
            return 'low'
        if v.startswith('inf'):
            return 'info'
        return v or 'info'

    class Vulnerability(BaseModel):
        class DescriptionItem(BaseModel):
            file: str
            line_start: int
            line_end: int
            desc: str

        title: str
        severity: str
        summary: str = ''
        description: list[DescriptionItem]
        impact: str
        proof_of_concept: str = ''
        remediation: str = ''

        @field_validator('severity', mode='before')
        @classmethod
        def _normalize_severity_field(cls, value: object) -> str:
            if not isinstance(value, str):
                return 'info'
            return ReportModel._normalize_severity(value)

    vulnerabilities: list[Vulnerability]


def _require_auth(job: Job, token: str | None) -> None:
    if not token or not job.result_token or token != job.result_token:
        msg = 'Invalid results token'
        raise HTTPException(status_code=401, detail=msg)


def _load_report(report: str | None) -> dict[str, Any] | None:
    if not report:
        return None

    json_start = report.find('{')
    json_end = report.rfind('}')
    if json_start == -1 or json_end == -1:
        logger.warning(f'Got report without json: {report!r}')
        return None

    try:
        report_data = json.loads(report[json_start : json_end + 1])
    except json.JSONDecodeError:
        logger.warning(f'Got report with invalid json: {report!r}')
        return None

    try:
        report_data = ReportModel.model_validate(report_data, extra='allow').model_dump(mode='json')
    except ValidationError:
        logger.warning(f'Got report with invalid model: {report!r} ({report_data})')
        return None

    logger.info('Successfully loaded report')
    return report_data


@router.post('/results')
async def submit_result(
    payload: ReportPayload,
    session: Annotated[AsyncSession, Depends(get_db)],
    token: Annotated[str | None, Header(alias='X-Results-Token')] = None,
) -> dict[str, str]:
    job = await session.get(Job, payload.job_id)
    if job is None or job.status != JobStatus.running:
        msg = 'Job not found'
        raise HTTPException(status_code=404, detail=msg)

    _require_auth(job, token)
    now = datetime.now(tz=UTC)

    loaded_report = _load_report(payload.report)
    if not loaded_report:
        payload.status = 'failed'
        payload.error = payload.error or 'Invalid report'

    job.status = JobStatus.succeeded if payload.status == 'succeeded' else JobStatus.failed
    job.finished_at = now
    job.result = loaded_report
    job.result_error = payload.error
    job.result_received_at = now
    logger.info(f'Updated job {job.id} status to {job.status}')
    return {'status': 'ok'}
