"""Tests for municipal_edogawa normalization logic."""

from __future__ import annotations

import os

# Enable DB-less mode for these pure unit tests.
os.environ["UNIT_ONLY_NO_DB"] = "1"

from scripts.ingest.normalize_municipal_edogawa import normalize_municipal_edogawa_payload


def test_edogawa_create_gym_true_with_keywords():
    parsed = {
        "facility_name": "江戸川区総合体育館 トレーニングルーム",
        "address": None,
        "equipments_raw": ["トレーニングマシン 10台"],
        "page_title": "江戸川区総合体育館 トレーニングルーム 利用上の注意",
    }
    url = "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/sogotaiikukan/index.html"
    result = normalize_municipal_edogawa_payload(parsed, page_url=url)
    assert result.pref_slug == "tokyo"
    assert result.city_slug == "edogawa"
    assert result.parsed_json["meta"]["create_gym"] is True
    # suffix removed
    assert result.name_raw.endswith("利用上の注意") is False


def test_edogawa_create_gym_false_without_keywords():
    parsed = {
        "facility_name": "江戸川区総合体育館",
        "address": None,
        "equipments_raw": ["卓球台 5台"],
        "page_title": "江戸川区総合体育館 アクセス",
    }
    # URL matches pattern but no keywords
    url = "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/bunya/sportsshisetsu/sogotaiikukan/index.html"
    result = normalize_municipal_edogawa_payload(parsed, page_url=url)
    assert result.parsed_json["meta"]["create_gym"] is False


def test_edogawa_create_gym_false_wrong_url():
    parsed = {
        "facility_name": "江戸川区総合体育館 トレーニングルーム",
        "address": None,
        "equipments_raw": ["トレーニングルーム"],
        "page_title": "江戸川区総合体育館 トレーニングルーム",
    }
    # URL does not match pattern
    url = "https://www.city.edogawa.tokyo.jp/e028/other/page.html"
    result = normalize_municipal_edogawa_payload(parsed, page_url=url)
    assert result.parsed_json["meta"]["create_gym"] is False
