"""/gyms routers that delegate to services via DI."""

from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_async_session,
    get_equipment_slugs_from_query,
    get_gym_detail_api_service,
    get_gym_nearby_service,
    get_gym_search_api_service,
)
from app.dto import GymDetailDTO, GymSearchPageDTO
from app.schemas.common import ErrorResponse
from app.schemas.gym_nearby import GymNearbyResponse
from app.schemas.gym_search import GymSearchQuery
from app.schemas.report import ReportCreateRequest
from app.services.gym_detail import GymDetailService
from app.services.reports import ReportService

router = APIRouter(prefix="/gyms", tags=["gyms"])


_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）、緯度経度+半径でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順\n"
    " （1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1.0)*0.1）\n"
    " - sort=score: freshness(0.6)とrichness(0.4)を合算した最終スコア降順\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
    "- sort=gym_name: name ASC, id ASC（Keyset）\n"
    "- sort=created_at: created_at DESC, id ASC（Keyset）\n"
    "- sort=distance: 指定座標からのHaversine距離 ASC, id ASC（lat/lng 必須）\n"
)


# (routerは薄く保つため、DBロジック系のヘルパーはサービス層へ移動しました)


@router.get(
    "/search",
    response_model=GymSearchPageDTO,
    summary="ジム検索（設備フィルタ + Keysetページング）",
    description=_DESC,
    responses={
        422: {"model": ErrorResponse, "description": "validation error"},
        404: {"model": ErrorResponse, "description": "Not Found"},
    },
)
async def search_gyms(
    request: Request,
    q: GymSearchQuery = Depends(GymSearchQuery.as_query),
    search_svc: Callable[..., GymSearchPageDTO] = Depends(get_gym_search_api_service),
):
    # 1) 設備スラッグを吸収（CSV/配列/単数の各形式に対応）
    required_slugs: list[str] = get_equipment_slugs_from_query(request, q.equipments)
    if q.equipments and not required_slugs:
        required_slugs = [s.strip() for s in q.equipments.split(",") if s.strip()]

    # 2) サービス呼び出し（DBアクセス・トークン処理はサービス側）
    try:
        return await search_svc(
            pref=q.pref,
            city=q.city,
            lat=q.lat,
            lng=q.lng,
            radius_km=q.radius_km,
            required_slugs=required_slugs,
            equipment_match=q.equipment_match,
            sort=q.sort,
            page=q.page,
            page_size=q.page_size,
            page_token=q.page_token,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid page_token")


@router.get(
    "/nearby",
    response_model=GymNearbyResponse,
    summary="ジム近傍検索（Haversine + Keyset）",
    description=(
        "指定した座標から半径 `radius_km` 以内のジムを、\n"
        "Haversine距離の昇順・id昇順で返します。ページングは距離+idのKeysetです。"
    ),
    responses={
        422: {"model": ErrorResponse, "description": "validation error"},
    },
)
async def gyms_nearby(
    lat: float = Query(..., ge=-90.0, le=90.0, description="緯度（-90〜90）"),
    lng: float = Query(..., ge=-180.0, le=180.0, description="経度（-180〜180）"),
    radius_km: float = Query(5.0, ge=0.0, le=50.0, description="検索半径（km）"),
    page: int = Query(1, ge=1, description="ページ番号（1始まり）"),
    page_size: int | None = Query(None, ge=1, le=100, description="1ページ件数（1..100）"),
    per_page: int | None = Query(None, ge=1, le=100, description="1ページ件数（互換用, 1..100）"),
    limit: int | None = Query(None, ge=1, le=100, description="limit（互換用, 1..100）"),
    page_token: str | None = Query(None, description="Keyset継続トークン（互換用）"),
    svc=Depends(get_gym_nearby_service),
):
    resolved_page_size = next(
        (value for value in (page_size, per_page, limit) if value is not None),
        None,
    )
    try:
        return await svc(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            page=page,
            page_size=resolved_page_size,
            page_token=page_token,
        )
    except ValueError:
        raise HTTPException(status_code=422, detail="invalid page_token")


@router.get(
    "/{slug}",
    response_model=GymDetailDTO,
    summary="ジム詳細を取得",
    description=(
        "ジム詳細を返却します。`include=score` を指定すると freshness/richness/score を同梱します。"
    ),
    responses={
        404: {"model": ErrorResponse, "description": "ジムが見つかりません"},
        422: {"model": ErrorResponse, "description": "validation error"},
    },
)
async def get_gym_detail(
    slug: str,
    include: str | None = Query(default=None, description="例: include=score"),
    svc: GymDetailService = Depends(get_gym_detail_api_service),
):
    if include not in (None, "score"):
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    # サービスに委譲。見つからない場合は router 側で 404 を返す。
    detail = await svc.get_opt(slug, include)
    if detail is None:
        raise HTTPException(status_code=404, detail="gym not found")
    return detail


@router.get(
    "/by-id/{canonical_id}",
    response_model=GymDetailDTO,
    summary="ジム詳細を canonical_id で取得",
    description=(
        "canonical UUID を用いてジムの詳細を返却します。"
        "`include=score` を指定すると freshness/richness/score を同梱します。"
    ),
    responses={
        404: {"model": ErrorResponse, "description": "ジムが見つかりません"},
        422: {"model": ErrorResponse, "description": "validation error"},
    },
)
async def get_gym_detail_by_id(
    canonical_id: str,
    include: str | None = Query(default=None, description="例: include=score"),
    svc: GymDetailService = Depends(get_gym_detail_api_service),
):
    if include not in (None, "score"):
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    try:
        canonical_uuid = UUID(canonical_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Unprocessable Entity")

    detail = await svc.get_by_canonical_id_opt(str(canonical_uuid), include)
    if detail is None:
        raise HTTPException(status_code=404, detail="gym not found")
    return detail


@router.post(
    "/{slug}/report",
    status_code=201,
    summary="誤り報告を送信",
)
async def report_gym(
    slug: str,
    payload: ReportCreateRequest,
    session: AsyncSession = Depends(get_async_session),
):
    svc = ReportService(session)
    try:
        r = await svc.create_for_gym_slug(slug, payload)
        return r
    except ValueError:
        raise HTTPException(status_code=404, detail="gym not found")
