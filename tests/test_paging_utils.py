import pytest

from app.utils.paging import build_next_offset_token, parse_offset_token


def test_parse_offset_token_accepts_matching_hash():
    token = build_next_offset_token(0, 10, 30, sort_key="score")
    assert token == "10:score"

    offset = parse_offset_token(token, page=1, per_page=10, expected_sort_key="score-desc")
    assert offset == 10


def test_parse_offset_token_rejects_sort_mismatch():
    token = build_next_offset_token(0, 20, 50, sort_key="freshness")

    with pytest.raises(ValueError):
        parse_offset_token(token, page=1, per_page=20, expected_sort_key="richness")


def test_parse_offset_token_handles_empty_or_negative():
    with pytest.raises(ValueError):
        parse_offset_token("", page=1, per_page=10)

    with pytest.raises(ValueError):
        parse_offset_token("-10", page=1, per_page=10)
