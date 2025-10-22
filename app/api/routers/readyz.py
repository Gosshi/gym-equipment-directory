from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.startup import is_migration_completed
from app.db import SessionLocal
from app.schemas.common import OkResponse
from app.services.health import HealthService

router = APIRouter(prefix="/readyz", tags=["health"])


@router.get(
    "",
    response_model=OkResponse,
    summary="Readiness probe",
    description="DB に SELECT 1 を投げて疎通を確認（マイグレーション前は503）",
)
async def readyz():
    if not is_migration_completed():
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "migrations_pending",
                    "message": "Database migrations are still running",
                }
            },
        )

    async with SessionLocal() as session:
        svc = HealthService(session)
        return await svc.ok()
