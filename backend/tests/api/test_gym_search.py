from __future__ import annotations

from collections import Counter

import pytest
from sqlalchemy import select

from app.models import Gym
from app.utils.geo import haversine_distance_km


@pytest.mark.asyncio
async def test_search_radius_filters(app_client, db_session):
    rows = await db_session.execute(select(Gym.slug, Gym.latitude, Gym.longitude))
    coords = {row.slug: (float(row.latitude), float(row.longitude)) for row in rows}
    base = coords["funabashi-station-gym"]
    near = coords["funabashi-bay-gym"]
    boundary = coords["narashino-center-gym"]

    near_distance = haversine_distance_km(base, near)
    boundary_distance = haversine_distance_km(base, boundary)

    radius_before_boundary = round(boundary_distance - 0.005, 3)
    radius_after_boundary = round(boundary_distance + 0.005, 3)

    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": base[0],
            "lng": base[1],
            "radius_km": round(max(0.1, near_distance - 0.05), 3),
            "sort": "distance",
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert [item["slug"] for item in data["items"]] == ["funabashi-station-gym"]

    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": base[0],
            "lng": base[1],
            "radius_km": round(near_distance + 0.05, 3),
            "sort": "distance",
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert [item["slug"] for item in data["items"]] == [
        "funabashi-station-gym",
        "funabashi-bay-gym",
    ]

    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": base[0],
            "lng": base[1],
            "radius_km": radius_after_boundary,
            "sort": "distance",
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    slugs = [item["slug"] for item in data["items"]]
    assert slugs == [
        "funabashi-station-gym",
        "funabashi-bay-gym",
        "narashino-center-gym",
    ]

    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": base[0],
            "lng": base[1],
            "radius_km": radius_before_boundary,
            "sort": "distance",
            "page_size": 20,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_search_radius_min_max(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": 35.7000,
            "lng": 139.9850,
            "radius_km": 0.1,
            "sort": "distance",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1

    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": 35.7000,
            "lng": 139.9850,
            "radius_km": 50,
            "sort": "distance",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 6


@pytest.mark.asyncio
async def test_search_pref_city_and_equipments(app_client):
    params = {
        "pref": "chiba",
        "city": "funabashi",
        "sort": "gym_name",
    }
    resp = await app_client.get("/gyms/search", params=params)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2

    params_with_all = params | {
        "equipments": "squat-rack,dumbbell",
        "equipment_match": "all",
    }
    resp = await app_client.get("/gyms/search", params=params_with_all)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert [item["slug"] for item in items] == ["funabashi-station-gym"]

    params_with_any = params | {
        "equipments": "squat-rack,dumbbell",
        "equipment_match": "any",
    }
    resp = await app_client.get("/gyms/search", params=params_with_any)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert Counter(item["slug"] for item in items) == Counter(
        ["funabashi-station-gym", "funabashi-bay-gym"]
    )

    resp = await app_client.get(
        "/gyms/search",
        params={
            "pref": "tokyo",
            "city": "funabashi",
            "sort": "gym_name",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_search_equipments_order_independent(app_client):
    base_params = {
        "pref": "chiba",
        "city": "funabashi",
        "sort": "gym_name",
        "equipment_match": "any",
    }
    resp1 = await app_client.get(
        "/gyms/search",
        params=base_params | {"equipments": "squat-rack,dumbbell"},
    )
    resp2 = await app_client.get(
        "/gyms/search",
        params=base_params | {"equipments": "dumbbell,squat-rack"},
    )
    assert resp1.status_code == resp2.status_code == 200
    assert resp1.json() == resp2.json()


@pytest.mark.asyncio
async def test_search_pagination_behaviour(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "gym_name", "page": 1, "page_size": 2},
    )
    first_page = resp.json()
    assert len(first_page["items"]) == 2
    assert first_page["page"] == 1
    assert first_page["has_more"] is True

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "gym_name", "page": 2, "page_size": 2},
    )
    second_page = resp.json()
    assert len(second_page["items"]) == 2
    assert second_page["page"] == 2
    assert second_page["has_prev"] is True

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "gym_name", "page": 4, "page_size": 2},
    )
    empty_page = resp.json()
    assert empty_page["items"] == []
    assert empty_page["has_more"] is False
    assert empty_page["total"] >= 6

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "gym_name", "per_page": 3},
    )
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 3


@pytest.mark.asyncio
async def test_search_sorting_modes(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={
            "lat": 35.7000,
            "lng": 139.9850,
            "radius_km": 50,
            "sort": "distance",
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    distances = [item.get("distance_km") for item in items]
    assert distances == sorted(distances)

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "gym_name"},
    )
    names = [item["name"] for item in resp.json()["items"]]
    assert names == sorted(names)

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "created_at"},
    )
    slugs = [item["slug"] for item in resp.json()["items"]]
    assert slugs[:3] == [
        "sumida-tower-gym",
        "koto-riverside-gym",
        "urayasu-resort-gym",
    ]

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "score"},
    )
    payload = resp.json()
    scores = [item["score"] for item in payload["items"]]
    assert scores == sorted(scores, reverse=True)
    assert all(item["freshness_score"] is not None for item in payload["items"])
    assert all(item["richness_score"] is not None for item in payload["items"])

    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "freshness"},
    )
    freshness_slugs = [item["slug"] for item in resp.json()["items"]]
    assert freshness_slugs[-1] == "sumida-tower-gym"


@pytest.mark.asyncio
async def test_search_invalid_parameters(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={"pref": "Funabashi"},
    )
    assert resp.status_code == 400

    resp = await app_client.get(
        "/gyms/search",
        params={"lat": 95, "lng": 139.8},
    )
    assert resp.status_code == 422

    resp = await app_client.get(
        "/gyms/search",
        params={"lat": 35.7, "lng": 139.8, "radius_km": -1},
    )
    assert resp.status_code == 422

    resp = await app_client.get(
        "/gyms/search",
        params={"page_size": 200},
    )
    assert resp.status_code == 422

    resp = await app_client.get(
        "/gyms/search",
        params={"equipments": ""},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_requires_coordinates_for_distance(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={"sort": "distance"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_search_invalid_page_token(app_client):
    resp = await app_client.get(
        "/gyms/search",
        params={"page_token": "not-a-token"},
    )
    assert resp.status_code == 400
