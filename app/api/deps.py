"""API dependency helpers and service providers."""

from typing import List

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_async_session
from app.services.equipments import EquipmentService
from app.services.gym_detail import GymDetailService
from app.services.gym_search_api import GymSearchResponse
from app.services.gym_search_api import search_gyms_api as _search_gyms_api
from app.services.health import HealthService
from app.services.meta import MetaService

__all__ = [
    "get_equipment_slugs_from_query",
    "get_gym_search_api_service",
    "get_gym_detail_api_service",
    "get_equipment_service",
    "get_meta_service",
    "get_health_service",
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


def get_gym_search_api_service(
    session: AsyncSession = Depends(get_async_session),
):
    """Provides a callable service for searching gyms (API schema)."""

    async def _svc(
        *,
        pref: str | None,
        city: str | None,
        required_slugs: list[str],
        equipment_match: str,
        sort: str,
        per_page: int,
        page_token: str | None,
    ) -> GymSearchResponse:
        return await _search_gyms_api(
            session,
            pref=pref,
            city=city,
            required_slugs=required_slugs,
            equipment_match=equipment_match,  # type: ignore[arg-type]
            sort=sort,  # type: ignore[arg-type]
            per_page=per_page,
            page_token=page_token,
        )

    return _svc


def get_gym_detail_api_service(
    session: AsyncSession = Depends(get_async_session),
) -> GymDetailService:
    return GymDetailService(session)


def get_equipment_service(
    session: AsyncSession = Depends(get_async_session),
) -> EquipmentService:
    return EquipmentService(session)


def get_meta_service(session: AsyncSession = Depends(get_async_session)) -> MetaService:
    return MetaService(session)


def get_health_service(
    session: AsyncSession = Depends(get_async_session),
) -> HealthService:
    return HealthService(session)
