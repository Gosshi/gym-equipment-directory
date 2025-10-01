from textwrap import dedent

from scripts.ingest.parse import map_municipal_koto_equipments
from scripts.ingest.sites import municipal_koto


def test_parse_detail_extracts_fields() -> None:
    html = dedent(
        """
        <html><head><title>有明スポーツセンター｜江東区</title></head>
        <body>
          <h1>有明スポーツセンター</h1>
          <address>東京都江東区有明2-3-5</address>
          <ul class="equipments">
            <li>トレーニング室（マシン・ダンベル・スミスマシン）</li>
            <li>有酸素マシン（エアロバイク）</li>
          </ul>
        </body></html>
        """
    ).strip()

    data = municipal_koto.parse_detail(html)

    assert "有明スポーツセンター" in str(data["name"])
    assert "東京都江東区" in str(data["address"])
    equipments_raw = data["equipments_raw"]
    assert isinstance(equipments_raw, list)
    assert any("スミス" in item or "ダンベル" in item for item in equipments_raw)


def test_map_municipal_koto_equipments_normalizes_keywords() -> None:
    equipments = [
        "トレーニング室（スミスマシン）",
        " ベンチプレス台 ",
        "ダンベルセット",
        "ラットプルダウンマシン",
        "最新型レッグプレス",
        "エアロバイクエリア",
        "未知設備",
        "スミスマシン追加",
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
