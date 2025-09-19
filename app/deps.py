"""Legacy router dependencies wired to the new service layer."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.infra.unit_of_work import SqlAlchemyUnitOfWork
from app.services.gym_detail import GymDetailService
from app.services.gym_search import GymSearchService


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


def _uow_factory() -> SqlAlchemyUnitOfWork:
    return SqlAlchemyUnitOfWork(SessionLocal)


def get_search_service_v1() -> GymSearchService:
    return GymSearchService(_uow_factory)


def get_gym_detail_service_v1() -> GymDetailService:
    return GymDetailService(_uow_factory)
