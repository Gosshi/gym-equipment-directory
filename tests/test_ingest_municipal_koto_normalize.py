from __future__ import annotations

from scripts.ingest.normalize import _assign_pref_city_for_municipal_koto
from scripts.ingest.sites import municipal_koto as site


def test_name_cleanup_and_norm() -> None:
    name = "施設案内｜亀戸スポーツセンター\x00｜江東区"
    html = f"<html><head><title>{name}</title></head><body><h1>{name}</h1></body></html>"
    data = site.parse_detail(html)
    assert data["name"] == "亀戸スポーツセンター"


def test_pref_city_assign() -> None:
    assert _assign_pref_city_for_municipal_koto("東京都江東区有明2-3-5", None) == (
        "tokyo",
        "koto",
    )
    assert _assign_pref_city_for_municipal_koto("", "深川スポーツセンター") == ("tokyo", "koto")
    assert _assign_pref_city_for_municipal_koto(None, None) == (None, None)
