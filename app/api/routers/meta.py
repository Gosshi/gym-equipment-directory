# app/api/routers/meta.py

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_meta_service
from app.schemas.common import ErrorResponse
from app.schemas.meta import CategoryOption, CityOption, EquipmentOption, PrefOption
from app.services.meta import MetaService

# ルータ側は prefix のみ（tags は各EPに付与して重複回避）
router = APIRouter(prefix="/meta")


@router.get(
    "/prefectures",
    tags=["meta"],
    response_model=list[PrefOption],
    summary="都道府県一覧（distinct）",
    description="登録されているジムの都道府県スラッグを重複なしで返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_prefectures(svc: MetaService = Depends(get_meta_service)):
    return await svc.list_pref_options()


@router.get(
    "/prefs",
    tags=["meta"],
    response_model=list[PrefOption],
    summary="都道府県候補を取得（件数付き）",
    description="登録されているジムの都道府県スラッグと件数を返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_prefs(svc: MetaService = Depends(get_meta_service)):
    return await svc.list_pref_options()


@router.get(
    "/cities",
    tags=["meta"],
    response_model=list[CityOption],
    summary="市区町村候補を取得（件数付き）",
    description="指定した都道府県スラッグに属する市区町村スラッグと件数を返します。空/NULLは除外。",
    responses={
        404: {"model": ErrorResponse, "description": "pref not found"},
        422: {"model": ErrorResponse, "description": "validation error"},
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_cities(
    pref: Annotated[
        str,
        Query(
            description="都道府県スラッグ（lower）例: chiba",
            examples=["chiba"],
            min_length=1,
            pattern=r"^[a-z0-9-]+$",
        ),
    ],
    svc: MetaService = Depends(get_meta_service),
):
    return await svc.list_city_options(pref)


@router.get(
    "/equipment-categories",
    tags=["meta"],
    response_model=list[CategoryOption],
    summary="設備カテゴリ一覧（distinct）",
    description="登録されている設備カテゴリ名を重複なしで返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_equipment_categories(svc: MetaService = Depends(get_meta_service)):
    return await svc.list_category_options()


@router.get(
    "/equipments",
    tags=["meta"],
    response_model=list[EquipmentOption],
    summary="設備スラッグ一覧（distinct）",
    description="登録されている設備スラッグと名称・カテゴリを重複なしで返します。空/NULLは除外。",
    responses={
        503: {"model": ErrorResponse, "description": "database unavailable"},
    },
)
async def list_equipments_meta(svc: MetaService = Depends(get_meta_service)):
    return await svc.list_equipments()
