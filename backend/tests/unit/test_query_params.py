"""Unit tests for pagination and sort normalization helpers."""

from __future__ import annotations

import pytest

from app.utils.paging import build_next_offset_token, parse_offset_token
from app.utils.sort import resolve_sort_key

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("token", "page", "per_page", "expected"),
    [
        (None, 1, 20, 0),
        (None, 3, 15, 30),
        ("5", 1, 20, 5),
    ],
)
def test_parse_offset_token_handles_none_and_numeric(
    token: str | None,
    page: int,
    per_page: int,
    expected: int,
) -> None:
    assert parse_offset_token(token, page=page, per_page=per_page) == expected


@pytest.mark.parametrize("token", ["", "abc", "1.5"])
def test_parse_offset_token_rejects_invalid_strings(token: str) -> None:
    with pytest.raises(ValueError):
        parse_offset_token(token, page=1, per_page=20)


@pytest.mark.parametrize(
    ("offset", "per_page", "total", "expected"),
    [
        (0, 10, 25, "10"),
        (15, 10, 30, "25"),
        (20, 10, 30, None),
        (30, 10, 30, None),
    ],
)
def test_build_next_offset_token_detects_end_of_results(
    offset: int,
    per_page: int,
    total: int,
    expected: str | None,
) -> None:
    assert build_next_offset_token(offset, per_page, total) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (None, "freshness"),
        ("", "freshness"),
        ("recent", "freshness"),
        ("UPDATED", "freshness"),
        ("richness", "richness"),
        ("score", "richness"),
        ("RANK", "richness"),
        ("gym_name", "gym_name"),
        ("Name", "gym_name"),
        ("created", "created_at"),
        ("distance", "freshness"),
        ("unknown", "freshness"),
    ],
)
def test_resolve_sort_key_normalizes_aliases(raw: str | None, expected: str) -> None:
    assert resolve_sort_key(raw) == expected
