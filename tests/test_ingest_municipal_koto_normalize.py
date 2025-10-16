from __future__ import annotations

from scripts.ingest.normalize import _assign_pref_city_for_municipal_koto
from scripts.ingest.normalize_municipal_koto import merge_payloads, normalize_payload
from scripts.ingest.parse_municipal_koto import parse_municipal_koto_page


def test_name_cleanup_and_norm() -> None:
    name = "施設案内｜亀戸スポーツセンター\x00｜江東区"
    html = f"<html><head><title>{name}</title></head><body><h1>{name}</h1></body></html>"
    parsed = parse_municipal_koto_page(
        html,
        "https://www.koto-hsc.or.jp/sports_center3/introduction/",
    )
    assert parsed.name == "亀戸スポーツセンター"


def test_normalize_payload_generates_slugs() -> None:
    payload = {
        "equipments_raw": ["トレッドミル×9", "アップライトバイク×5", "ラットプルダウン"],
        "equipments_parsed": [
            {"name": "トレッドミル", "count": 9},
            {"name": "アップライトバイク", "count": "5"},
            {"name": "ラットプルダウン"},
        ],
    }

    normalized = normalize_payload(payload)

    assert normalized["equipments_slugs"] == [
        "treadmill",
        "upright-bike",
        "lat-pulldown",
    ]
    assert normalized["equipments_slotted"] == [
        {"slug": "treadmill", "count": 9},
        {"slug": "upright-bike", "count": 5},
    ]


def test_merge_payloads_prefers_max_count_and_sources() -> None:
    base = normalize_payload(
        {
            "equipments_raw": ["トレッドミル×5"],
            "equipments_parsed": [{"name": "トレッドミル", "count": 5}],
            "sources": [{"label": "official", "url": "https://example.com/a"}],
            "center_no": "3",
        }
    )
    incoming = normalize_payload(
        {
            "equipments_raw": ["トレッドミル×8", "ダンベル"],
            "equipments_parsed": [
                {"name": "トレッドミル", "count": 8},
                {"name": "ダンベル"},
            ],
            "sources": [{"label": "official", "url": "https://example.com/b"}],
            "center_no": "3",
        }
    )

    merged = merge_payloads(base, incoming)

    assert merged["equipments_slotted"] == [{"slug": "treadmill", "count": 8}]
    assert merged["equipments_slugs"] == [
        "treadmill",
        "dumbbell-1-10kg",
    ]
    assert len(merged.get("sources", [])) == 2
    assert merged["center_no"] == "3"
    assert any(
        entry["name"] == "ダンベル" and "count" not in entry
        for entry in merged["equipments_parsed"]
    )


def test_pref_city_assign() -> None:
    assert _assign_pref_city_for_municipal_koto("東京都江東区有明2-3-5", None) == (
        "tokyo",
        "koto",
    )
    assert _assign_pref_city_for_municipal_koto("", "深川スポーツセンター") == ("tokyo", "koto")
    assert _assign_pref_city_for_municipal_koto(None, None) == (None, None)
