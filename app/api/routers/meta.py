from typing import List, Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_async_session
from app.models import Gym

router = APIRouter(prefix="/meta", tags=["meta"])

@router.get("/prefs", summary="都道府県の一覧（件数付き）", response_model=List[Dict])
async def list_prefs(session: AsyncSession = Depends(get_async_session)):
    stmt = select(Gym.prefecture, func.count(Gym.id)).group_by(Gym.prefecture).order_by(Gym.prefecture.asc())
    rows = await session.execute(stmt)
    return [{"pref": r[0], "count": r[1]} for r in rows]

@router.get("/cities", summary="市区町村の一覧（件数付き）", response_model=List[Dict])
async def list_cities(
    pref: str = Query(..., description="都道府県スラッグ"),
    session: AsyncSession = Depends(get_async_session),
):
    stmt = (
        select(Gym.city, func.count(Gym.id))
        .where(Gym.prefecture == pref)
        .group_by(Gym.city)
        .order_by(Gym.city.asc())
    )
    rows = await session.execute(stmt)
    return [{"city": r[0], "count": r[1]} for r in rows]
