from scripts.ingest.normalize_municipal_sumida import normalize_municipal_sumida_payload
from scripts.ingest.parse_municipal_sumida import parse_municipal_sumida_page


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
    return normalize_municipal_sumida_payload(parsed_json, page_url=url)


def test_sumida_intro_page_extracts_equipment() -> None:
    html = """
    <html>
      <head><title>墨田区総合体育館 トレーニングルーム</title></head>
      <body>
        <main id="contents">
          <h1>墨田区総合体育館 トレーニングルーム</h1>
          <div class="summary">所在地：〒131-0044 東京都墨田区文花2-3-5</div>
          <section class="machines">
            <table>
              <tr><th>機器名</th><th>台数</th></tr>
              <tr><td>トレッドミル</td><td>10台</td></tr>
              <tr><td>BRAVO PRO ケーブルマシン</td><td>1台</td></tr>
              <tr><td>アークトレーナー/ステッパー</td><td>3台</td></tr>
            </table>
          </section>
        </main>
      </body>
    </html>
    """.strip()
    url = "https://www.city.sumida.lg.jp/sisetu_info/sports/sumidasportcenter.html"

    parsed = parse_municipal_sumida_page(html, url, page_type="intro")
    normalized = _normalize(parsed, url)

    assert parsed.facility_name == "墨田区総合体育館 トレーニングルーム"
    assert parsed.address == "〒131-0044 東京都墨田区文花2-3-5"
    assert {entry["slug"] for entry in parsed.equipments} == {
        "treadmill",
        "functional-trainer",
        "arc-trainer-stepper",
    }
    counts = {entry["slug"]: entry["count"] for entry in parsed.equipments}
    assert counts["treadmill"] == 10
    assert counts["functional-trainer"] == 1
    assert parsed.meta["create_gym"] is True
    assert "treadmill" in normalized.parsed_json["equipments_slugs"]
    assert normalized.parsed_json["meta"]["create_gym"] is True


def test_sumida_article_without_address_does_not_create() -> None:
    html = """
    <html>
      <head><title>墨田区総合体育館 利用上の注意</title></head>
      <body>
        <main id="contents">
          <h1>墨田区総合体育館 利用上の注意</h1>
          <p>トレーニングルームの利用上の注意です。</p>
          <ul>
            <li>ラットプルダウン</li>
            <li>チェストプレス</li>
            <li>スミスマシン</li>
          </ul>
        </main>
      </body>
    </html>
    """.strip()
    url = "https://www.city.sumida.lg.jp/sisetu_info/sports/sumidasportcenter/notice.html"

    parsed = parse_municipal_sumida_page(html, url, page_type="article")
    normalized = _normalize(parsed, url)

    assert parsed.address is None
    assert parsed.meta["create_gym"] is False
    assert normalized.parsed_json["meta"]["create_gym"] is False
