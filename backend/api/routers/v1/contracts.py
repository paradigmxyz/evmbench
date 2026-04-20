from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.core.config import settings
from api.core.const import ALLOWED_MODELS
from api.core.contract_analysis import analyze_contract
from api.core.deps import TokenDep
from api.schemas.contract_analysis import ContractAnalysisRequest, ContractAnalysisResponse


router = APIRouter(prefix='/contracts', tags=['contracts'])


RequestDep = Annotated[ContractAnalysisRequest, Depends(ContractAnalysisRequest.as_json)]


@router.post('/analyze')
async def analyze_contract_route(
    payload: RequestDep,
    _token: TokenDep,
) -> ContractAnalysisResponse:
    model = payload.model or settings.BACKEND_CONTRACT_ANALYSIS_MODEL
    if model not in ALLOWED_MODELS:
        raise HTTPException(status_code=401, detail='Model is not allowed')

    return await analyze_contract(source_code=payload.source_code, model=model)
