"""/gyms routers that delegate to services via DI."""

from collections.abc import Callable

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
        400: {
            "description": "Invalid page_token",
            "content": {"application/json": {"example": {"detail": "invalid page_token"}}},
        }
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
            per_page=q.per_page,
            page_token=q.page_token,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid page_token")


@router.get(
    "/nearby",
    response_model=GymNearbyResponse,
    summary="ジム近傍検索（Haversine + Keyset）",
    description=(
        "指定した座標から半径 `radius_km` 以内のジムを、\n"
        "Haversine距離の昇順・id昇順で返します。ページングは距離+idのKeysetです。"
    ),
)
async def gyms_nearby(
    lat: float = Query(..., description="緯度"),
    lng: float = Query(..., description="経度"),
    radius_km: float = Query(5.0, ge=0.0, description="検索半径（km）"),
    per_page: int = Query(10, ge=1, le=50, description="1ページ件数"),
    page_token: str | None = Query(None, description="Keyset継続トークン"),
    svc=Depends(get_gym_nearby_service),
):
    try:
        return await svc(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            per_page=per_page,
            page_token=page_token,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid page_token")


@router.get(
    "/{slug}",
    response_model=GymDetailDTO,
    summary="ジム詳細を取得",
    description=(
        "ジム詳細を返却します。`include=score` を指定すると freshness/richness/score を同梱します。"
    ),
    responses={404: {"model": ErrorResponse, "description": "ジムが見つかりません"}},
)
async def get_gym_detail(
    slug: str,
    include: str | None = Query(default=None, description="例: include=score"),
    svc: GymDetailService = Depends(get_gym_detail_api_service),
):
    # サービスに委譲。見つからない場合は router 側で 404 を返す。
    detail = await svc.get_opt(slug, include)
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
