from scripts.ingest.parse import map_municipal_koto_equipments
from scripts.ingest.sites import municipal_koto


def test_parse_detail_extracts_expected_fields() -> None:
    html = """
    <html>
      <body>
        <div class="facility-detail">
          <h1>亀戸スポーツセンター</h1>
          <address>東京都江東区亀戸１－２－３</address>
          <ul class="equipments">
            <li>スミスマシン</li>
            <li> ベンチプレス </li>
            <li>ラットプル</li>
          </ul>
        </div>
      </body>
    </html>
    """

    detail = municipal_koto.parse_detail(html)

    assert detail.name == "亀戸スポーツセンター"
    assert detail.address == "東京都江東区亀戸1-2-3"
    assert detail.equipments_raw == ["スミスマシン", "ベンチプレス", "ラットプル"]


def test_map_municipal_koto_equipments_matches_known_slugs() -> None:
    equipments = [
        "スミス",
        "ベンチプレス台",
        "ダンベルセット",
        "ラットプルダウン",
        "レッグプレスマシン",
        "フィットネスバイク",
        "未知設備",
        "スミス",  # duplicate should be ignored
    ]

    mapped = map_municipal_koto_equipments(equipments)

    assert mapped == [
        "smith-machine",
        "bench-press",
        "dumbbell",
        "lat-pulldown",
        "leg-press",
        "upright-bike",
    ]
