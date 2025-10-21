from scripts.ingest.normalize_municipal_edogawa import normalize_municipal_edogawa_payload
from scripts.ingest.parse_municipal_edogawa import parse_municipal_edogawa_page


def _normalize(parsed, url: str):
    parsed_json = {
        "facility_name": parsed.facility_name,
        "address": parsed.address,
        "equipments_raw": parsed.equipments_raw,
        "equipments": parsed.equipments,
        "center_no": parsed.center_no,
        "page_type": parsed.page_type,
        "page_title": parsed.page_title,
        "meta": parsed.meta,
    }
    return normalize_municipal_edogawa_payload(parsed_json, page_url=url)


def test_edogawa_training_page_sets_create_gym() -> None:
    html = """
    <html>
      <head><title>江戸川区総合体育館 トレーニングルーム</title></head>
      <body>
        <div id="wrapper">
          <h1>江戸川区総合体育館 トレーニングルーム</h1>
          <div class="summary">〒132-0021 東京都江戸川区中央1-4-1</div>
          <section class="machine-list">
            <ul>
              <li>ラットプルダウン</li>
              <li>チェストプレス 4台</li>
              <li>リカンベントバイク</li>
              <li>スミスマシン</li>
            </ul>
            <p>各3台</p>
          </section>
        </div>
      </body>
    </html>
    """.strip()
    url = (
        "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/"
        "bunya/sportsshisetsu/sogo_sports_center/index.html"
    )

    parsed = parse_municipal_edogawa_page(html, url, page_type="intro")
    normalized = _normalize(parsed, url)

    assert parsed.facility_name.startswith("江戸川区総合体育館")
    assert parsed.address == "〒132-0021 東京都江戸川区中央1-4-1"
    assert len(parsed.equipments) >= 3
    assert parsed.meta["create_gym"] is True
    assert normalized.parsed_json["meta"]["create_gym"] is True


def test_edogawa_notice_page_skipped() -> None:
    html = """
    <html>
      <head><title>江戸川区総合体育館 利用上の注意</title></head>
      <body>
        <div id="wrapper">
          <h1>江戸川区総合体育館 利用上の注意</h1>
          <p>注意事項のページです。</p>
          <p>スミス、ベンチプレスなどの器具名が含まれます。</p>
        </div>
      </body>
    </html>
    """.strip()
    url = (
        "https://www.city.edogawa.tokyo.jp/e028/kuseijoho/gaiyo/shisetsuguide/"
        "bunya/sportsshisetsu/sogo_sports_center/notice.html"
    )

    parsed = parse_municipal_edogawa_page(html, url, page_type="article")
    normalized = _normalize(parsed, url)

    assert parsed.meta["create_gym"] is False
    assert normalized.parsed_json["meta"]["create_gym"] is False
