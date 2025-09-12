from __future__ import annotations

from datetime import datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym import Gym


async def _add_gym(
    session: AsyncSession,
    *,
    slug: str,
    name: str,
    lat: float,
    lng: float,
    pref: str = "tokyo",
    city: str = "chiyoda",
):
    g = Gym(
        slug=slug,
        name=name,
        pref=pref,
        city=city,
        latitude=lat,
        longitude=lng,
        last_verified_at_cached=datetime.utcnow(),
    )
    session.add(g)
    await session.commit()
    await session.refresh(g)
    return g


@pytest.mark.asyncio
async def test_nearby_radius_filter(session: AsyncSession, app_client: AsyncClient):
    # Base point
    lat0, lng0 = 35.0, 139.0

    # Distances: ~0 km, ~1.11 km, ~5.55 km
    g1 = await _add_gym(session, slug="nearby-g1", name="G1", lat=35.0, lng=139.0)
    g2 = await _add_gym(session, slug="nearby-g2", name="G2", lat=35.01, lng=139.0)
    _ = await _add_gym(session, slug="nearby-g3", name="G3", lat=35.05, lng=139.0)
    # Close seeding session early to avoid teardown ordering issues
    await session.close()

    r = await app_client.get(
        "/gyms/nearby",
        params={"lat": lat0, "lng": lng0, "radius_km": 5, "per_page": 10},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    ids = [it["id"] for it in j["items"]]
    assert g1.id in ids and g2.id in ids
    # g3 is outside radius 5km
    assert all(it["slug"] != "nearby-g3" for it in j["items"])


@pytest.mark.asyncio
async def test_nearby_paging_no_duplicates(session: AsyncSession, app_client: AsyncClient):
    lat0, lng0 = 35.0, 139.0
    slugs = []
    # Create 5 gyms at growing distance (~0.111 km steps)
    for i in range(5):
        s = f"nearby-pg-{i}"
        slugs.append(s)
        await _add_gym(session, slug=s, name=s.upper(), lat=35.0 + i * 0.001, lng=139.0)
    await session.close()

    r1 = await app_client.get(
        "/gyms/nearby", params={"lat": lat0, "lng": lng0, "radius_km": 10, "per_page": 2}
    )
    assert r1.status_code == 200
    j1 = r1.json()
    assert j1["has_next"] is True
    ids1 = [it["id"] for it in j1["items"]]

    r2 = await app_client.get(
        "/gyms/nearby",
        params={
            "lat": lat0,
            "lng": lng0,
            "radius_km": 10,
            "per_page": 2,
            "page_token": j1["page_token"],
        },
    )
    assert r2.status_code == 200
    j2 = r2.json()
    ids2 = [it["id"] for it in j2["items"]]
    # Ensure no duplicates across pages
    assert set(ids1).isdisjoint(set(ids2))

    r3 = await app_client.get(
        "/gyms/nearby",
        params={
            "lat": lat0,
            "lng": lng0,
            "radius_km": 10,
            "per_page": 2,
            "page_token": j2["page_token"],
        },
    )
    assert r3.status_code == 200
    j3 = r3.json()
    ids3 = [it["id"] for it in j3["items"]]
    # All unique across 3 pages covering 5 records (2+2+1)
    assert len(set(ids1 + ids2 + ids3)) == len(ids1 + ids2 + ids3)


@pytest.mark.asyncio
async def test_nearby_without_page_token_starts_from_top(
    session: AsyncSession, app_client: AsyncClient
):
    lat0, lng0 = 36.0, 139.0
    # Ensure two gyms near base
    g_close = await _add_gym(session, slug="nearby-top-1", name="Top1", lat=36.0, lng=139.0)
    await _add_gym(session, slug="nearby-top-2", name="Top2", lat=36.02, lng=139.0)
    await session.close()

    r = await app_client.get(
        "/gyms/nearby", params={"lat": lat0, "lng": lng0, "radius_km": 10, "per_page": 10}
    )
    assert r.status_code == 200
    j = r.json()
    assert len(j["items"]) >= 2
    # First should be the closest (distance then id)
    assert j["items"][0]["slug"] == g_close.slug
