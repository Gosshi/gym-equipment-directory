# app/api/routers/healthz.py
from fastapi import APIRouter, Depends

from app.api.deps import get_health_service
from app.services.health import HealthService

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get("", summary="Health check", description="DBにSELECT 1を投げる軽量ヘルスチェック")
async def healthz(svc: HealthService = Depends(get_health_service)):
    return await svc.ok()
