from fastapi import APIRouter

from .auth import router as auth_router
from .integration import router as integration_router
from .jobs import router as jobs_router


router = APIRouter(prefix='/v1')
router.include_router(jobs_router)
router.include_router(integration_router)
router.include_router(auth_router)
