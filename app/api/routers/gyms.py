"""/gyms routers that delegate to services via DI."""

from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.api.deps import (
    get_equipment_slugs_from_query,
    get_gym_detail_api_service,
    get_gym_search_api_service,
)
from app.schemas.common import ErrorResponse
from app.schemas.gym_detail import GymDetailResponse
from app.schemas.gym_search import GymSearchQuery, GymSearchResponse
from app.services.gym_detail import GymDetailService

router = APIRouter(prefix="/gyms", tags=["gyms"])


_DESC = (
    "都道府県/市区町村スラッグ、設備スラッグ（CSV）でフィルタします。\n"
    "- sort=freshness: gyms.last_verified_at_cached DESC, id ASC\n"
    "- sort=richness: GymEquipment をスコア合算し降順\n"
    " （1.0 + min(count,5)*0.1 + min(max_weight_kg/60,1.0)*0.1）\n"
    " - sort=score: freshness(0.6)とrichness(0.4)を合算した最終スコア降順\n"
    "- equipment_match=all の場合、指定スラッグを**すべて**含むジムのみ返します\n"
    "- sort=gym_name: name ASC, id ASC（Keyset）\n"
    "- sort=created_at: created_at DESC, id ASC（Keyset）\n"
)


# (routerは薄く保つため、DBロジック系のヘルパーはサービス層へ移動しました)


@router.get(
    "/search",
    response_model=GymSearchResponse,
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
    search_svc: Callable[..., GymSearchResponse] = Depends(get_gym_search_api_service),
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
            required_slugs=required_slugs,
            equipment_match=q.equipment_match,
            sort=q.sort,
            per_page=q.per_page,
            page_token=q.page_token,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid page_token")


@router.get(
    "/{slug}",
    response_model=GymDetailResponse,
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
