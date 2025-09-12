import pytest


@pytest.mark.anyio
async def test_search_gym_name_schema_and_zeros(app_client):
    # sort=gym_name では score 群は 0.0 のダミー値
    resp = await app_client.get(
        "/gyms/search",
        params={
            "pref": "chiba",
            "city": "funabashi",
            "sort": "gym_name",
            "per_page": 10,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_next"] is False
    assert body["page_token"] is None
    items = body["items"]
    # seed により 2 ジムが該当
    slugs = {it["slug"] for it in items}
    assert slugs == {"dummy-funabashi-east", "dummy-funabashi-west"}
    # スコアは 0.0（スキーマのキーが揃っていることも確認）
    for it in items:
        assert it["score"] == 0.0
        assert it["freshness_score"] == 0.0
        assert it["richness_score"] == 0.0
        for k in ["id", "name", "city", "pref", "last_verified_at"]:
            assert k in it


@pytest.mark.anyio
async def test_search_score_has_scores(app_client):
    # sort=score では score 群が 0..1 の範囲で計算される
    resp = await app_client.get(
        "/gyms/search",
        params={
            "pref": "chiba",
            "city": "funabashi",
            "sort": "score",
            "per_page": 10,
        },
    )
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert {it["slug"] for it in items} == {
        "dummy-funabashi-east",
        "dummy-funabashi-west",
    }
    for it in items:
        for k in ["score", "freshness_score", "richness_score"]:
            v = it[k]
            assert isinstance(v, int | float)
            assert 0.0 <= float(v) <= 1.0


@pytest.mark.anyio
async def test_search_filter_required_slugs_all_any(app_client):
    # seed: east は seed-bench-press と seed-lat-pulldown の両方、west は bench のみ
    base = {
        "pref": "chiba",
        "city": "funabashi",
        "sort": "gym_name",
        "per_page": 10,
    }

    # all: seed-lat-pulldown を持つのは east のみ
    resp_all = await app_client.get(
        "/gyms/search",
        params={**base, "equipments": "seed-lat-pulldown", "equipment_match": "all"},
    )
    assert resp_all.status_code == 200
    items_all = resp_all.json()["items"]
    assert [it["slug"] for it in items_all] == ["dummy-funabashi-east"]

    # any: bench か lat のどちらか → east, west の両方
    resp_any = await app_client.get(
        "/gyms/search",
        params={
            **base,
            "equipments": "seed-bench-press,seed-lat-pulldown",
            "equipment_match": "any",
        },
    )
    assert resp_any.status_code == 200
    slugs_any = {it["slug"] for it in resp_any.json()["items"]}
    assert slugs_any == {"dummy-funabashi-east", "dummy-funabashi-west"}
