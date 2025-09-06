# app/api/routers/meta.py
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.models import Gym
from app.schemas.meta import PrefCount, CityCount

router = APIRouter(prefix="/meta", tags=["meta"])

@router.get(
    "/prefs",
    response_model=List[PrefCount],
    summary="都道府県候補を取得（件数付き）",
    description="登録されているジムの都道府県スラッグと件数を返します。空/NULLは除外。",
)
async def list_prefs(session: AsyncSession = Depends(get_async_session)):
    stmt = (
        select(
            Gym.pref.label("pref"),
            func.count().label("count"),
        )
        .where(Gym.pref.isnot(None), Gym.pref != "")
        .group_by(Gym.pref)
        .order_by(func.count().desc(), Gym.pref.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [{"pref": r.pref, "count": int(r.count)} for r in rows]


@router.get(
    "/cities",
    response_model=List[CityCount],
    summary="市区町村候補を取得（件数付き）",
    description="指定した都道府県スラッグに属する市区町村スラッグと件数を返します。空/NULLは除外。",
)
async def list_cities(
    pref: Annotated[str, Query(description="都道府県スラッグ（lower）例: chiba", example="chiba")],
    session: AsyncSession = Depends(get_async_session),
):
    pref_norm = pref.lower()
    stmt = (
        select(
            Gym.city.label("city"),
            func.count().label("count"),
        )
        .where(
            Gym.pref == pref_norm,
            Gym.city.isnot(None),
            Gym.city != "",
        )
        .group_by(Gym.city)
        .order_by(func.count().desc(), Gym.city.asc())
    )
    rows = (await session.execute(stmt)).all()
    return [{"city": r.city, "count": int(r.count)} for r in rows]
