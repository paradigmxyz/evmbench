from fastapi import APIRouter

from secretsvc.routers.v1.bundles import router as bundles_router


router = APIRouter(prefix='/v1')
router.include_router(bundles_router)
