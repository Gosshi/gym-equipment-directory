"""Unit tests for geo-related helpers and pagination tokens."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.services import gym_nearby, gym_search_api
from app.services.gym_search_api import GymSortKey

pytestmark = pytest.mark.unit


def test_nearby_token_roundtrip_preserves_values() -> None:
    token = gym_nearby._encode_page_token_for_nearby(12.3456789, 42)

    distance, last_id = gym_nearby._validate_and_decode_page_token(token)

    assert distance == pytest.approx(12.345679, abs=1e-6)
    assert last_id == 42


@pytest.mark.parametrize(
    "token",
    [
        "not-a-token",
        gym_nearby._b64e({"sort": "nearby"}),
        gym_nearby._b64e({"sort": "nearby", "k": [1, 2, 3]}),
        gym_nearby._b64e({"sort": "something-else", "k": [1, 2]}),
        gym_nearby._b64e({"sort": "nearby", "k": ["not-a-number", 5]}),
    ],
)
def test_nearby_token_validation_rejects_invalid_payloads(token: str) -> None:
    with pytest.raises(ValueError):
        gym_nearby._validate_and_decode_page_token(token)


def test_iso_helper_filters_invalid_dates() -> None:
    assert gym_nearby._iso(None) is None
    assert gym_nearby._iso(datetime(1960, 1, 1)) is None

    dt = datetime(2024, 5, 1, 12, 30, 45)
    assert gym_nearby._iso(dt) == dt.isoformat()


def test_distance_token_roundtrip_uses_six_decimal_precision() -> None:
    token = gym_search_api._encode_page_token_for_distance(987.6543219, 7)

    distance, last_id = gym_search_api._validate_and_decode_page_token(token, GymSortKey.distance)

    assert distance == pytest.approx(987.654322, abs=1e-6)
    assert last_id == 7


def test_distance_token_validation_checks_sort_match() -> None:
    token = gym_search_api._encode_page_token_for_distance(1.0, 9)

    with pytest.raises(ValueError):
        gym_search_api._validate_and_decode_page_token(token, GymSortKey.richness)


def test_distance_token_validation_detects_wrong_shape() -> None:
    token = gym_search_api._b64e({"sort": GymSortKey.distance.value, "k": [1, 2, 3]})

    with pytest.raises(ValueError):
        gym_search_api._validate_and_decode_page_token(token, GymSortKey.distance)


def test_last_verified_formatter_returns_iso_strings() -> None:
    assert gym_search_api._lv(None) is None
    assert gym_search_api._lv(datetime(1965, 1, 1)) is None

    dt = datetime(2023, 11, 3, 9, 15, 0)
    assert gym_search_api._lv(dt) == dt.isoformat()
