"""Unit tests for strict search query validation schemas."""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.gym_search import GymSearchQuery

pytestmark = pytest.mark.unit


def test_slug_fields_are_trimmed() -> None:
    query = GymSearchQuery(pref="  tokyo-01  ", city="  funabashi  ")

    assert query.pref == "tokyo-01"
    assert query.city == "funabashi"


@pytest.mark.parametrize(
    ("field", "value", "detail"),
    [
        ("pref", "   ", "empty string is not allowed"),
        ("pref", "Tokyo", "invalid slug"),
        ("city", "kyoto!", "invalid slug"),
    ],
)
def test_slug_fields_reject_invalid_inputs(field: str, value: str, detail: str) -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery(**{field: value})

    assert exc.value.status_code == 400
    assert exc.value.detail == detail


@pytest.mark.parametrize("value", [0, -1, 101])
def test_page_size_must_be_within_bounds(value: int) -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery(page_size=value)

    assert exc.value.status_code == 400
    assert exc.value.detail == "page_size must be between 1 and 100"


def test_page_must_be_positive() -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery(page=0)

    assert exc.value.status_code == 400
    assert exc.value.detail == "page must be >= 1"


def test_equipments_csv_must_not_be_blank() -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery(equipments="   ")

    assert exc.value.status_code == 400
    assert exc.value.detail == "equipments must not be empty"


@pytest.mark.parametrize(
    ("kwargs", "expected_page_size"),
    [
        ({"page_size": 30, "per_page": 40, "limit": 50}, 30),
        ({"page_size": None, "per_page": 25, "limit": 50}, 25),
        ({"page_size": None, "per_page": None, "limit": 10}, 10),
        ({"page_size": None, "per_page": None, "limit": None}, 20),
    ],
)
def test_as_query_resolves_page_size_priority(
    kwargs: dict[str, int | None],
    expected_page_size: int,
) -> None:
    query = GymSearchQuery.as_query(**kwargs)

    assert query.page_size == expected_page_size


def test_as_query_invalid_page_size_propagates_http_exception() -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery.as_query(page_size=0)

    assert exc.value.status_code == 400
    assert exc.value.detail == "page_size must be between 1 and 100"


def test_as_query_blank_equipments_propagates_http_exception() -> None:
    with pytest.raises(HTTPException) as exc:
        GymSearchQuery.as_query(equipments="   ")

    assert exc.value.status_code == 400
    assert exc.value.detail == "equipments must not be empty"


def test_lat_lng_bounds_are_enforced() -> None:
    query = GymSearchQuery.model_validate({"lat": 90.0, "lng": -180.0})

    assert query.lat == pytest.approx(90.0)
    assert query.lng == pytest.approx(-180.0)


def test_latitude_out_of_range_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        GymSearchQuery.model_validate({"lat": 90.0001})
