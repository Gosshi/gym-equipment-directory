from app.ingest.normalizers.equipment_aliases import EQUIPMENT_ALIASES
from app.ingest.parsers.municipal._base import (
    detect_create_gym,
    extract_address_one_line,
    extract_equipments,
    sanitize_text,
)


def test_sanitize_text_removes_control_characters() -> None:
    raw = "\x00\u200B\u3000トレーニング ルーム\n"
    assert sanitize_text(raw) == "トレーニング ルーム"


def test_extract_address_one_line_prefers_postal_code() -> None:
    html = """
    <html>
      <body>
        <div class="summary">所在地：〒135-0004 東京都江東区森下3-12-17　KOTOビル 2F。</div>
        <div class="summary">東京都江東区の別住所です。</div>
      </body>
    </html>
    """
    selectors = {
        "address_hint": [".summary"],
        "body": ["body"],
    }
    patterns = {"address": [r"〒\s*\d{3}-\d{4}[^。]*", r"東京都[^。]+区[^。]+"]}

    result = extract_address_one_line(html, selectors=selectors, patterns=patterns)
    assert result == "〒135-0004 東京都江東区森下3-12-17 KOTOビル 2F"


def test_extract_equipments_merges_counts_and_aliases() -> None:
    html = """
    <html>
      <body>
        <main>
          <h2>トレーニングマシン</h2>
          <ul>
            <li>ラットプル/ラットプルダウン</li>
            <li>スミスプレス</li>
            <li>アジャスタブルベンチ</li>
          </ul>
          <p>3台</p>
          <p>BRAVO PRO ケーブルマシン 2台</p>
        </main>
      </body>
    </html>
    """
    selectors = {"equipment_blocks": ["main"], "body": ["main"]}

    equipments = extract_equipments(html, selectors=selectors, aliases=EQUIPMENT_ALIASES)
    assert {entry["slug"] for entry in equipments} == {
        "lat-pulldown",
        "smith-machine",
        "adjustable-bench",
        "functional-trainer",
    }
    counts = {entry["slug"]: entry["count"] for entry in equipments}
    assert counts["lat-pulldown"] == 3
    assert counts["smith-machine"] == 3
    assert counts["adjustable-bench"] == 3
    assert counts["functional-trainer"] == 2


def test_detect_create_gym_requires_address_and_keywords() -> None:
    patterns = {
        "url": {
            "intro_top": r"/sports_center[0-9]+/introduction/?$",
            "detail_article": r"/introduction/trainingmachine\\.html$",
        }
    }
    keywords = {"training": ["トレーニングルーム"], "facility": ["スポーツセンター"]}

    assert detect_create_gym(
        "https://example.com/sports_center1/introduction/",
        title="江東区スポーツセンター トレーニングルーム",
        body="パンくず＞トレーニングルーム",
        patterns=patterns,
        keywords=keywords,
        eq_count=5,
        address="東京都江東区亀戸2-1-1",
    ) is True

    assert detect_create_gym(
        "https://example.com/sports_center1/news/notice.html",
        title="江東区スポーツセンター トレーニングルーム",
        body="パンくず＞トレーニングルーム",
        patterns=patterns,
        keywords=keywords,
        eq_count=5,
        address="東京都江東区亀戸2-1-1",
    ) is False

    assert detect_create_gym(
        "https://example.com/sports_center1/introduction/",
        title="江東区スポーツセンター",
        body="施設案内",
        patterns=patterns,
        keywords=keywords,
        eq_count=2,
        address="東京都江東区亀戸2-1-1",
    ) is False
