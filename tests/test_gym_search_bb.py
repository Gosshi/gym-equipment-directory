import pytest


@pytest.mark.anyio
async def test_search_bb_strict_filter(app_client):
    """
    g1: lat=35.7, lng=139.98
    g2: lat=35.72, lng=139.95
    """
    # 1. BB that captures only g1 (East)
    resp = await app_client.get(
        "/gyms/search",
        params={
            "min_lat": 35.69,
            "max_lat": 35.71,
            "min_lng": 139.97,
            "max_lng": 139.99,
            "page_size": 10,
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    slugs = {it["slug"] for it in items}
    assert slugs == {"dummy-funabashi-east"}


@pytest.mark.anyio
async def test_search_bb_wide_filter(app_client):
    # 2. BB that captures both
    resp = await app_client.get(
        "/gyms/search",
        params={
            "min_lat": 35.60,
            "max_lat": 35.80,
            "min_lng": 139.90,
            "max_lng": 140.00,
            "page_size": 10,
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    slugs = {it["slug"] for it in items}
    assert slugs == {"dummy-funabashi-east", "dummy-funabashi-west"}


@pytest.mark.anyio
async def test_search_bb_out_of_range(app_client):
    # 3. BB that matches nothing
    resp = await app_client.get(
        "/gyms/search",
        params={
            "min_lat": 36.00,
            "max_lat": 36.10,
            "min_lng": 139.90,
            "max_lng": 140.00,
            "page_size": 10,
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 0


@pytest.mark.anyio
async def test_search_bb_partial_params(app_client):
    # 4. Partial BB (e.g., only min_lat)
    # Searching gym > 35.71 (should match West at 35.72, exclude East at 35.7)
    resp = await app_client.get(
        "/gyms/search",
        params={
            "min_lat": 35.71,
            "page_size": 10,
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    slugs = {it["slug"] for it in items}
    assert slugs == {"dummy-funabashi-west"}
