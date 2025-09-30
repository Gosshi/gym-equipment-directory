from __future__ import annotations

from scripts.ingest.sites import site_a


def test_parse_gym_html_extracts_expected_fields() -> None:
    html = """
    <html>
      <head><title>サイトA | ダミージム豊洲</title></head>
      <body>
        <div class="gym-detail">
          <h1 class="gym-name">ダミージム豊洲</h1>
          <div class="address">東京都江東区豊洲1-2-3</div>
          <ul class="equipments">
            <li>スミスマシン</li>
            <li>ラットプルダウン</li>
            <li>ダンベル 40kg</li>
          </ul>
        </div>
      </body>
    </html>
    """

    result = site_a.parse_gym_html(html)

    assert result.name_raw == "ダミージム豊洲"
    assert result.address_raw == "東京都江東区豊洲1-2-3"
    assert result.equipments_raw == ["スミスマシン", "ラットプルダウン", "ダンベル 40kg"]
    assert result.equipments == ["smith-machine", "lat-pulldown", "dumbbell"]


def test_parse_gym_html_uses_title_and_maps_variants() -> None:
    html = """
    <html>
      <head><title>サイトA｜サンプルジム芝浦</title></head>
      <body>
        <div class="gym-detail">
          <div class="address">東京都港区芝浦1-2-3</div>
          <ul class="equipments">
            <li>スミス</li>
            <li>レッグプレスマシン</li>
            <li>バイク</li>
            <li>スミスマシン</li>
          </ul>
        </div>
      </body>
    </html>
    """

    result = site_a.parse_gym_html(html)

    assert result.name_raw == "サンプルジム芝浦"
    assert result.address_raw == "東京都港区芝浦1-2-3"
    assert result.equipments_raw == [
        "スミス",
        "レッグプレスマシン",
        "バイク",
        "スミスマシン",
    ]
    assert result.equipments == ["smith-machine", "leg-press", "bike"]
