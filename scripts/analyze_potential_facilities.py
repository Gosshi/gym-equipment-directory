import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.getcwd())

from bs4 import BeautifulSoup
from sqlalchemy import text

from app.db import SessionLocal, configure_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

KEYWORDS = {
    "Gym": ["トレーニング室", "トレーニングジム", "フィットネス"],
    "Pool": ["温水プール", "水泳場", "プール"],
    "Tennis": ["テニスコート", "庭球場"],
    "Hall": ["体育館", "競技場", "アリーナ"],
    "MartialArts": ["武道場", "柔道場", "剣道場"],
    "Baseball": ["野球場", "軟式野球場"],
    "Archery": ["弓道場", "アーチェリー"],
}


async def analyze_pages(limit: int = 1000):
    async with SessionLocal() as session:
        # Get total count
        total = (await session.execute(text("SELECT count(*) FROM scraped_pages"))).scalar_one()
        logger.info(f"Total Scraped Pages: {total}")

        # Fetch recent pages raw_html
        logger.info(f"Fetching last {limit} pages...")
        stmt = text("SELECT raw_html FROM scraped_pages ORDER BY fetched_at DESC LIMIT :limit")
        result = await session.execute(stmt, {"limit": limit})
        rows = result.fetchall()

        stats = {k: 0 for k in KEYWORDS.keys()}
        stats["Other"] = 0
        total_analyzed = 0

        logger.info(f"Analyzing {len(rows)} pages...")

        for row in rows:
            raw_html = row[0]
            if not raw_html:
                continue

            total_analyzed += 1
            soup = BeautifulSoup(raw_html, "html.parser")
            # Get title and main content text
            text_content = (soup.title.string if soup.title else "") + " " + soup.get_text()

            matched_types = []
            for category, words in KEYWORDS.items():
                if any(w in text_content for w in words):
                    matched_types.append(category)

            if matched_types:
                for cat in matched_types:
                    stats[cat] += 1
            else:
                stats["Other"] += 1

            if total_analyzed % 100 == 0:
                print(f"Analyzed {total_analyzed}...")

        print("\n--- Potential Facility Types Found ---")
        for cat, count in stats.items():
            print(f"{cat}: {count} ({count / total_analyzed * 100:.1f}%)")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(analyze_pages(limit=1000))
