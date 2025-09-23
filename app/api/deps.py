"""API dependency helpers and service providers."""

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal, get_async_session
from app.dto import GymSearchPageDTO
from app.infra.unit_of_work import SqlAlchemyUnitOfWork
from app.services.equipments import EquipmentService
from app.services.gym_detail import GymDetailService
from app.services.gym_nearby import GymNearbyResponse
from app.services.gym_nearby import search_nearby as _search_nearby
from app.services.gym_search_api import search_gyms_api as _search_gyms_api
from app.services.health import HealthService
from app.services.meta import MetaService
from app.services.suggest import SuggestService

__all__ = [
    "get_equipment_slugs_from_query",
    "get_gym_search_api_service",
    "get_gym_nearby_service",
    "get_gym_detail_api_service",
    "get_equipment_service",
    "get_meta_service",
    "get_health_service",
    "get_suggest_service",
]


def get_equipment_slugs_from_query(request: Request, equipments: str | None = None) -> list[str]:
    """
    クエリパラメータから equipments=CSV, equipment=..., equipment[]=... を吸収してスラッグ一覧を返す
    """
    qp = request.query_params
    slugs: list[str] = []

    # equipment=... の繰り返し
    slugs += qp.getlist("equipment")

    # equipment[]=... の繰り返し
    slugs += qp.getlist("equipment[]")

    # equipments=csv のケース
    if equipments:
        slugs += [s.strip() for s in equipments.split(",") if s.strip()]

    # 空文字除去 & 重複排除（順序保持）
    seen = set()
    out: list[str] = []
    for s in slugs:
        if s and s not in seen:
            seen.add(s)
            out.append(s)

    return out


# --- Service providers for DI ---


def _uow_factory() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(SessionLocal)


def get_gym_search_api_service(
    session: AsyncSession = Depends(get_async_session),
):
    """Provides a callable service for searching gyms (API schema)."""

    async def _svc(
        *,
        pref: str | None,
        city: str | None,
        lat: float | None,
        lng: float | None,
        radius_km: float | None,
        required_slugs: list[str],
        equipment_match: str,
        sort: str,
        page: int,
        page_size: int | None,
        page_token: str | None,
    ) -> GymSearchPageDTO:
        return await _search_gyms_api(
            session,
            pref=pref,
            city=city,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            required_slugs=required_slugs,
            equipment_match=equipment_match,  # type: ignore[arg-type]
            sort=sort,  # type: ignore[arg-type]
            page=page,
            page_size=page_size,
            page_token=page_token,
        )

    return _svc


def get_gym_detail_api_service() -> GymDetailService:
    return GymDetailService(_uow_factory)


def get_gym_nearby_service(
    session: AsyncSession = Depends(get_async_session),
):
    """Provides a callable service for /gyms/nearby."""

    async def _svc(
        *,
        lat: float,
        lng: float,
        radius_km: float,
        page: int,
        page_size: int | None,
        page_token: str | None,
    ) -> GymNearbyResponse:
        return await _search_nearby(
            session,
            lat=lat,
            lng=lng,
            radius_km=radius_km,
            page=page,
            page_size=page_size,
            page_token=page_token,
        )

    return _svc


def get_equipment_service() -> EquipmentService:
    return EquipmentService(_uow_factory)


def get_meta_service(session: AsyncSession = Depends(get_async_session)) -> MetaService:
    return MetaService(session)


def get_health_service(
    session: AsyncSession = Depends(get_async_session),
) -> HealthService:
    return HealthService(session)


def get_suggest_service(
    session: AsyncSession = Depends(get_async_session),
) -> SuggestService:
    return SuggestService(session)
