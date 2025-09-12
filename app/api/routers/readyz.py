from fastapi import APIRouter, Depends

from app.api.deps import get_health_service
from app.schemas.common import OkResponse
from app.services.health import HealthService

router = APIRouter(prefix="/readyz", tags=["health"])


@router.get(
    "",
    response_model=OkResponse,
    summary="Readiness probe",
    description="DB に SELECT 1 を投げて疎通を確認（OKなら200）",
)
async def readyz(svc: HealthService = Depends(get_health_service)):
    return await svc.ok()
