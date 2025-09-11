# app/api/routers/healthz.py
from fastapi import APIRouter, Depends

from app.api.deps import get_health_service
from app.schemas.common import OkResponse
from app.services.health import HealthService

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get(
    "",
    response_model=OkResponse,
    summary="Health check",
    description="DB に SELECT 1 を投げる軽量ヘルスチェック",
)
async def healthz(svc: HealthService = Depends(get_health_service)):
    return await svc.ok()
