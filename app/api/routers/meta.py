# app/api/routers/meta.py
from typing import List
from typing_extensions import Annotated

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.db import get_async_session
from app.models import Gym
from app.schemas.meta import PrefCount, CityCount
from app.schemas.common import ErrorResponse

# ルータ側は prefix のみ（tags は各EPに付与して重複回避）
router = APIRouter(prefix="/meta")


@router.get(
    "/prefs",
    tags=["meta"],
    response_model=List[PrefCount],
    summary="都道府県候補を取得（件数付き）",
    description="登録されているジムの都道府県スラッグと件数を返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_prefs(session: AsyncSession = Depends(get_async_session)):
    try:
        # NULLは WHERE で弾く必要なし: (pref != '') は NULL を自然に除外する（PostgreSQL）
        stmt = (
            select(
                Gym.pref.label("pref"),
                func.count().label("count"),
            )
            .where(Gym.pref != "")
            .group_by(Gym.pref)
            .order_by(func.count().desc(), Gym.pref.asc())
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [{"pref": r["pref"], "count": int(r["count"])} for r in rows]
    except SQLAlchemyError:
        # ログ仕込みたければここでlogger.exception(...)
        raise HTTPException(status_code=503, detail="database unavailable")


@router.get(
    "/cities",
    tags=["meta"],
    response_model=List[CityCount],
    summary="市区町村候補を取得（件数付き）",
    description="指定した都道府県スラッグに属する市区町村スラッグと件数を返します。空/NULLは除外。",
    responses={
        404: {"model": ErrorResponse, "description": "pref not found"},
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_cities(
    pref: Annotated[
        str, Query(description="都道府県スラッグ（lower）例: chiba", examples=["chiba"])
    ],
    session: AsyncSession = Depends(get_async_session),
):
    try:
        pref_norm = pref.lower()

        # まずprefの存在チェック（0件なら 404）
        exists_count = await session.scalar(
            select(func.count()).select_from(Gym).where(Gym.pref == pref_norm)
        )
        if not exists_count:
            raise HTTPException(status_code=404, detail="pref not found")

        # 市区町村の集計（空文字を除外）
        stmt = (
            select(
                Gym.city.label("city"),
                func.count().label("count"),
            )
            .where(Gym.pref == pref_norm, Gym.city != "")
            .group_by(Gym.city)
            .order_by(func.count().desc(), Gym.city.asc())
        )
        rows = (await session.execute(stmt)).mappings().all()
        return [{"city": r["city"], "count": int(r["count"])} for r in rows]
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="database unavailable")
