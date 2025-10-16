from __future__ import annotations

from scripts.ingest.normalize_municipal_koto import normalize_payload
from scripts.ingest.parse_municipal_koto import parse_municipal_koto_page


def _parse_and_normalize(html: str, url: str):
    parsed = parse_municipal_koto_page(html, url)
    payload = normalize_payload(parsed.to_payload())
    return parsed, payload


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

    result, payload = _parse_and_normalize(
        html,
        "https://www.koto-hsc.or.jp/sports_center3/introduction/trainingmachine.html",
    )

    assert result.name == "亀戸スポーツセンター"
    assert result.center_no == "3"
    assert len(result.equipments_raw) >= 5
    assert any(entry.count is not None for entry in result.equipments_parsed)
    assert len(payload["equipments_slugs"]) >= 5
    assert any(slot["count"] >= 2 for slot in payload["equipments_slotted"])


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

    result, payload = _parse_and_normalize(
        html,
        "https://www.koto-hsc.or.jp/sports_center4/introduction/tr_detail.html",
    )

    assert result.name == "有明スポーツセンター"
    assert result.center_no == "4"
    assert len(result.equipments_raw) >= 5
    assert any(entry.count is not None for entry in result.equipments_parsed)
    assert len(payload["equipments_slugs"]) >= 5
    assert any(slot["slug"] == "leg-press" for slot in payload["equipments_slotted"])


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

    result, payload = _parse_and_normalize(
        html,
        "https://www.koto-hsc.or.jp/sports_center2/introduction/post_18.html",
    )

    assert result.name == "深川北スポーツセンター"
    assert result.center_no == "2"
    assert len(result.equipments_raw) >= 5
    assert len(payload["equipments_slugs"]) >= 5
    assert {
        slot["slug"] for slot in payload["equipments_slotted"]
    } & {"torso-rotation", "shoulder-press"}
