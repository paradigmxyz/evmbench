from fastapi import APIRouter

from api.core.config import settings
from api.core.impl import auth_backend
from api.core.model_catalog import DEFAULT_MODEL_KEY, frontend_model_options
from api.schemas.integration import FrontendConfig


router = APIRouter(prefix='/integration', tags=['integration'])


@router.get('/frontend')
async def frontend_config() -> FrontendConfig:
    return FrontendConfig(
        auth_enabled=bool(auth_backend),
        key_predefined=settings.BACKEND_STATIC_OAI_KEY is not None or settings.BACKEND_USE_PROXY_STATIC_KEY,
        default_model=DEFAULT_MODEL_KEY,
        models=frontend_model_options(),
    )
