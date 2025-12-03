"""Repository abstractions for the service layer."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from app.models.gym import Gym


@dataclass
class GymEquipmentBasicRow:
    gym_id: int
    equipment_slug: str
    equipment_name: str
    category: str | None
    count: int | None
    max_weight_kg: float | None


@dataclass
class GymEquipmentSummaryRow:
    gym_id: int
    slug: str
    name: str
    category: str | None
    count: int | None
    max_weight_kg: float | None
    availability: str | None
    verification_status: str | None
    last_verified_at: datetime | None
    source: str | None


@dataclass
class GymImageRow:
    gym_id: int
    url: str
    alt: str | None
    source: str | None
    verified: bool
    created_at: datetime | None


@dataclass
class EquipmentMasterRow:
    id: int
    slug: str
    name: str
    category: str | None


class GymReadRepository(Protocol):
    """Read-only repository boundary for gym related queries."""

    async def list_by_pref_city(self, *, pref: str | None, city: str | None) -> list[Gym]: ...

    async def created_at_map(self, gym_ids: Sequence[int]) -> dict[int, datetime | None]: ...

    async def fetch_equipment_basic(self, gym_id: int) -> list[GymEquipmentBasicRow]: ...

    async def fetch_equipment_summaries(self, gym_id: int) -> list[GymEquipmentSummaryRow]: ...

    async def fetch_equipment_for_gyms(
        self,
        *,
        gym_ids: Sequence[int],
        equipment_slugs: Sequence[str] | None,
    ) -> list[GymEquipmentSummaryRow]: ...

    async def fetch_images(self, gym_id: int) -> list[GymImageRow]: ...

    async def get_by_slug(self, slug: str) -> Gym | None: ...

    async def get_by_slug_from_history(self, slug: str) -> Gym | None: ...

    async def get_by_canonical_id(self, canonical_id: str) -> Gym | None: ...

    async def get_by_id(self, gym_id: int) -> Gym | None: ...

    async def resolve_id_by_slug(self, slug: str) -> int | None: ...

    async def count_gym_equipments(self, gym_id: int) -> int: ...

    async def max_gym_equipments(self) -> int: ...


class EquipmentReadRepository(Protocol):
    """Repository boundary for equipment master lookups."""

    async def search(self, *, q: str | None, limit: int) -> list[EquipmentMasterRow]: ...
