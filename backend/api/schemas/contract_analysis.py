import json
from typing import Annotated

from fastapi import HTTPException, Request
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError, field_validator


class ContractAnalysisRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    source_code: str
    model: Annotated[str | None, StringConstraints(strip_whitespace=True, min_length=1)] = None

    @classmethod
    async def as_json(cls, request: Request) -> 'ContractAnalysisRequest':
        try:
            payload = await request.json()
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=412, detail='Request body must be valid JSON') from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=412, detail='Unable to read request body') from exc

        try:
            return cls.model_validate(payload)
        except ValidationError as exc:
            detail = 'Invalid request'
            for err in exc.errors():
                msg = err.get('msg')
                if not isinstance(msg, str):
                    continue
                detail = msg.removeprefix('Value error, ')
                break
            raise HTTPException(status_code=412, detail=detail) from exc

    @field_validator('source_code', mode='before')
    @classmethod
    def validate_source_code(cls, value: object) -> str:
        if not isinstance(value, str):
            msg = 'source_code must be a string'
            raise ValueError(msg)
        if not value.strip():
            msg = 'source_code must not be empty'
            raise ValueError(msg)
        return value


class ContractEvidence(BaseModel):
    line_start: int
    line_end: int
    description: str


class ContractVulnerability(BaseModel):
    id: str
    title: str
    severity: str
    risk_score: int
    confidence_score: int
    impact_score: int
    exploitability_score: int
    summary: str
    remediation: str
    evidence: list[ContractEvidence]


class ContractAnalysisResponse(BaseModel):
    model: str
    score_version: str
    overall_risk_score: int
    overall_severity: str
    overall_summary: str
    vulnerabilities: list[ContractVulnerability]
