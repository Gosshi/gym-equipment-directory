from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.services.gym_detail import get_gym_detail_v1
from app.services.gym_search import search_gyms as _search_gyms_v1


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


class SearchServiceV1:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def search(
        self,
        *,
        pref: str | None,
        city: str | None,
        equipments: list[str] | None,
        equipment_match: str,
        sort: str,
        page_token: str | None,
        page: int,
        per_page: int,
    ):
        return await _search_gyms_v1(
            self._session,
            pref=pref,
            city=city,
            equipments=equipments,
            equipment_match=equipment_match,
            sort=sort,
            page_token=page_token,
            page=page,
            per_page=per_page,
        )


class GymDetailServiceV1:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, slug: str):
        return await get_gym_detail_v1(self._session, slug)


def get_search_service_v1(db: AsyncSession = Depends(get_db)) -> SearchServiceV1:
    return SearchServiceV1(db)


def get_gym_detail_service_v1(db: AsyncSession = Depends(get_db)) -> GymDetailServiceV1:
    return GymDetailServiceV1(db)
