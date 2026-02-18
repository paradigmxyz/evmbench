from fastapi import APIRouter

from .catch_all import router as catch_all_router


router = APIRouter()
router.include_router(catch_all_router)
