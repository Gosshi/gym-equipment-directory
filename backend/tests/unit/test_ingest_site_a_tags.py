from scripts.ingest.sites.site_a import SiteAParsedGym, parse_gym_html


def test_parse_gym_html_with_tags():
    html = """
    <html>
      <head><title>サイトA | Test Gym</title></head>
      <body>
        <div class="gym-detail">
          <h1 class="gym-name">Test Gym</h1>
          <div class="address">Tokyo</div>
          <ul class="equipments">
               <li>Smith Machine</li>
          </ul>
          <ul class="tags">
               <li>駐車場あり</li>
               <li>Wi-Fi</li>
          </ul>
        </div>
      </body>
    </html>
    """
    parsed = parse_gym_html(html)
    assert isinstance(parsed, SiteAParsedGym)
    assert parsed.name_raw == "Test Gym"
    assert "parking" in parsed.tags
    assert "wifi" in parsed.tags
    assert len(parsed.tags) == 2


def test_parse_gym_html_no_tags():
    html = """
    <html>
      <body>
        <div class="gym-detail">
          <h1 class="gym-name">Test Gym</h1>
        </div>
      </body>
    </html>
    """
    parsed = parse_gym_html(html)
    assert parsed.tags == []
