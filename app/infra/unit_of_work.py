"""Unit of Work abstraction used by the service layer."""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.repositories.interfaces import EquipmentReadRepository, GymReadRepository
from app.repositories.sqlalchemy import (
    SqlAlchemyEquipmentReadRepository,
    SqlAlchemyGymReadRepository,
)


class UnitOfWork(Protocol, AbstractAsyncContextManager["UnitOfWork"]):
    """Defines the repository boundary exposed to services."""

    gyms: GymReadRepository
    equipments: EquipmentReadRepository

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class SqlAlchemyUnitOfWork(UnitOfWork):
    """Unit of Work backed by SQLAlchemy async sessions."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self.gyms: GymReadRepository
        self.equipments: EquipmentReadRepository

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self.gyms = SqlAlchemyGymReadRepository(session)
        self.equipments = SqlAlchemyEquipmentReadRepository(session)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is None:
            return
        try:
            if exc_type:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()

    async def rollback(self) -> None:
        if self._session is not None:
            await self._session.rollback()

    @property
    def session(self) -> AsyncSession:
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not initialized. Use within context manager.")
        return self._session
