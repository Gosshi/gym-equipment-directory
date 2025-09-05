# app/api/routers/healthz.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.db import get_async_session

router = APIRouter(prefix="/healthz", tags=["health"])

@router.get("", summary="Health check", description="DBにSELECT 1を投げる軽量ヘルスチェック")
async def healthz(session: AsyncSession = Depends(get_async_session)):
    await session.execute(text("SELECT 1"))
    return {"ok": True}
