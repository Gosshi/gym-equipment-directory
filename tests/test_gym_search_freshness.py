from datetime import datetime

import pytest

from app.services.gym_search import search_gyms


class StubGym:
    def __init__(
        self, id_: int, name: str, slug: str, pref: str, city: str, last_verified_at_cached=None
    ):
        self.id = id_
        self.canonical_id = f"00000000-0000-0000-0000-{id_:012d}"
        self.name = name
        self.slug = slug
        self.pref = pref
        self.city = city
        self.last_verified_at_cached = last_verified_at_cached
        self.official_url = None


class StubGymsRepo:
    def __init__(self, gyms):
        self._gyms = gyms

    async def list_by_pref_city(self, pref=None, city=None):
        return self._gyms

    async def fetch_equipment_for_gyms(self, gym_ids, equipment_slugs=None):
        return []

    async def created_at_map(self, gym_ids):
        return {}


class StubUnitOfWork:
    def __init__(self, gyms_repo):
        self.gyms = gyms_repo


@pytest.mark.asyncio
async def test_freshness_sort_keeps_null_entries_and_total_matches():
    gyms = [
        StubGym(
            1,
            name="Fresh Gym",
            slug="fresh-gym",
            pref="tokyo",
            city="minato",
            last_verified_at_cached=datetime(2024, 1, 1, tzinfo=datetime.UTC),
        ),
        StubGym(
            2,
            name="Unknown Freshness Gym",
            slug="unknown-gym",
            pref="tokyo",
            city="minato",
            last_verified_at_cached=None,
        ),
    ]
    uow = StubUnitOfWork(StubGymsRepo(gyms))

    dto = await search_gyms(
        uow,
        pref=None,
        city=None,
        equipments=None,
        equipment_match="all",
        sort="freshness",
        page_token=None,
        page=1,
        per_page=10,
    )

    assert dto.total == 2
    assert [item.slug for item in dto.items] == ["fresh-gym", "unknown-gym"]
    assert dto.has_more is False
    assert dto.has_prev is False
