# app/api/routers/meta.py

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_meta_service
from app.schemas.common import ErrorResponse
from app.schemas.meta import CityCount, PrefCount
from app.services.meta import MetaService

# ルータ側は prefix のみ（tags は各EPに付与して重複回避）
router = APIRouter(prefix="/meta")


@router.get(
    "/prefs",
    tags=["meta"],
    response_model=list[PrefCount],
    summary="都道府県候補を取得（件数付き）",
    description="登録されているジムの都道府県スラッグと件数を返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_prefs(svc: MetaService = Depends(get_meta_service)):
    return await svc.list_prefs()


@router.get(
    "/cities",
    tags=["meta"],
    response_model=list[CityCount],
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
    svc: MetaService = Depends(get_meta_service),
):
    return await svc.list_cities(pref)
