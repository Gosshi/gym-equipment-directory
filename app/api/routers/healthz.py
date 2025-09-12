# app/api/routers/healthz.py
from fastapi import APIRouter

from app.schemas.common import OkResponse

router = APIRouter(prefix="/healthz", tags=["health"])


@router.get(
    "",
    response_model=OkResponse,
    summary="Liveness probe",
    description="単純に200(OK)を返すだけのエンドポイント（DBアクセスなし）",
)
async def healthz():
    return {"ok": True}
