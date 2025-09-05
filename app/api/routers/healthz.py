from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session

router = APIRouter(prefix="/healthz")

@router.get(
    "",
    summary="ヘルスチェック",
    description="アプリ起動およびDB到達性の簡易確認エンドポイント",
)
async def healthz(session: AsyncSession = Depends(get_async_session)):
    try:
        # DB疎通を軽く確認
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "ng"
    return {"status": "ok", "db": db_status}