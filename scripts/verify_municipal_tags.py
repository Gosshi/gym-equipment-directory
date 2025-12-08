import asyncio
import sys
from pathlib import Path

# Fix path to include project root
sys.path.append(str(Path(__file__).parent.parent))

from scripts.ingest.parse_municipal_generic import MunicipalSource, parse_municipal_page


async def verify_tags():
    # Valid Toshima URL
    url = "https://www.city.toshima.lg.jp/501/bunka/sports/sports/2509171407.html"

    print(f"Fetching {url}...")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    import httpx

    async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
        # Fetch facility page
        response = await client.get(url, follow_redirects=True)
        if response.status_code != 200:
            print(f"Failed to fetch facility page: {response.status_code}")
            return

        html = response.text
        print(f"Fetched {len(html)} bytes.")

        # Mock source object
        source = MunicipalSource(
            title="municipal_toshima",
            base_url="https://www.city.toshima.lg.jp",
            intro_patterns=[],
            article_patterns=[],
            list_seeds=[],
            pref_slug="tokyo",
            city_slug="toshima",
            parse_hints={},
        )

        # Run parsing logic
        result = parse_municipal_page(html, url, source=source)

        print(f"\n=== Parsing Result for {result.facility_name} ===")
        print(f"Address: {result.address}")

        print("\n=== Extracted Tags ===")
        if result.tags:
            for tag in result.tags:
                print(f"- {tag}")
        else:
            print("No tags extracted.")

        # Debug: Check body text for keywords
        print("\n=== Debug Info ===")
        print(f"Create Gym: {result.meta.get('create_gym')}")

        # Simple check for keywords in HTML to verifying if they simply exist
        keywords_to_check = ["駐車場", "24時間", "土足"]
        print("\nRaw HTML Keyword Check:")
        for k in keywords_to_check:
            found = k in html
            print(f"  '{k}': {found}")


if __name__ == "__main__":
    asyncio.run(verify_tags())
