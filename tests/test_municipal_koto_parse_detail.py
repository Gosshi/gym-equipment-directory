from __future__ import annotations

from scripts.ingest.normalize_municipal_koto import normalize_municipal_koto_payload
from scripts.ingest.parse_municipal_koto import parse_municipal_koto_page


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
    return normalize_municipal_koto_payload(parsed_json, page_url=url)


def test_parse_trainingmachine_template_extracts_counts() -> None:
    html = """
    <html>
      <body>
        <main id="main">
          <h1>亀戸スポーツセンター</h1>
          <address>東京都江東区亀戸2-4-6</address>
          <h2>トレーニングマシン一覧</h2>
          <table>
            <tr><th>機器名</th><th>台数</th></tr>
            <tr><td>トレッドミル</td><td>×９</td></tr>
            <tr><td>アップライトバイク</td><td>×５</td></tr>
            <tr><td>リカンベントバイク</td><td>×４</td></tr>
            <tr><td>アークトレーナー</td><td>×３</td></tr>
            <tr><td>ラットプルダウン</td><td>×２</td></tr>
          </table>
        </main>
      </body>
    </html>
    """.strip()

    result = parse_municipal_koto_page(
        html,
        "https://www.koto-hsc.or.jp/sports_center3/introduction/trainingmachine.html",
    )
    normalized = _normalize(result, "https://www.koto-hsc.or.jp/sports_center3/introduction/trainingmachine.html")

    assert result.facility_name == "亀戸スポーツセンター"
    assert result.center_no == "3"
    assert len(result.equipments_raw) >= 5
    assert any(entry["count"] >= 2 for entry in result.equipments)
    assert len(normalized.parsed_json["equipments_slugs"]) >= 5
    assert any(slot["count"] >= 2 for slot in normalized.parsed_json["equipments_slotted"])


def test_parse_tr_detail_template_handles_lists() -> None:
    html = """
    <html>
      <body>
        <div id="main">
          <h1>有明スポーツセンター</h1>
          <address>東京都江東区有明2-3-5</address>
          <h2>トレーニング設備</h2>
          <ul>
            <li>ペックデック（上半身強化）</li>
            <li>レッグプレス ×４台</li>
            <li>レッグカール</li>
            <li>レッグエクステンション</li>
            <li>グルートトレーナー</li>
            <li>チェストプレス</li>
          </ul>
        </div>
      </body>
    </html>
    """.strip()

    result = parse_municipal_koto_page(
        html,
        "https://www.koto-hsc.or.jp/sports_center4/introduction/tr_detail.html",
    )
    normalized = _normalize(result, "https://www.koto-hsc.or.jp/sports_center4/introduction/tr_detail.html")

    assert result.facility_name == "有明スポーツセンター"
    assert result.center_no == "4"
    assert len(result.equipments_raw) >= 5
    assert any(entry["count"] >= 1 for entry in result.equipments)
    assert len(normalized.parsed_json["equipments_slugs"]) >= 5
    assert any(slot["slug"] == "leg-press" for slot in normalized.parsed_json["equipments_slotted"])


def test_parse_post_template_extracts_from_paragraphs() -> None:
    html = """
    <html>
      <body>
        <main class="entry-content">
          <h1>深川北スポーツセンター</h1>
          <p>トーソローテーションやショルダープレスなど体幹を鍛えるマシンを紹介します。</p>
          <p>バックエクステンション、アブドミナル・バックエクステンション、クランチャー、ダンベルも揃えています。</p>
        </main>
      </body>
    </html>
    """.strip()

    result = parse_municipal_koto_page(
        html,
        "https://www.koto-hsc.or.jp/sports_center2/introduction/post_18.html",
    )
    normalized = _normalize(result, "https://www.koto-hsc.or.jp/sports_center2/introduction/post_18.html")

    assert result.facility_name == "深川北スポーツセンター"
    assert result.center_no == "2"
    assert len(result.equipments_raw) >= 5
    assert len(normalized.parsed_json["equipments_slugs"]) >= 5
    assert {slot["slug"] for slot in normalized.parsed_json["equipments_slotted"]} & {
        "torso-rotation",
        "shoulder-press",
    }
