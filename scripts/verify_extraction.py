import asyncio
import json
import sys
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from scripts.ingest.utils import get_or_create_source


async def verify_extraction(source_name: str, limit: int = 5):
    async with SessionLocal() as session:
        source = await get_or_create_source(session, title=source_name)

        candidate_count = await session.scalar(
            select(func.count())
            .select_from(GymCandidate)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .where(ScrapedPage.source_id == source.id)
        )
        print(f"Found {candidate_count} candidates for {source_name}")

        stmt = (
            select(GymCandidate)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .where(ScrapedPage.source_id == source.id)
            .order_by(GymCandidate.id.desc())
            .limit(limit)
            .options(joinedload(GymCandidate.source_page))
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        print(f"Found {len(candidates)} new candidates for {source_name}")

        def _serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return str(obj)

        for cand in candidates:
            raw_body_snippet = (
                cand.source_page.raw_html[:200] + "..." if cand.source_page.raw_html else None
            )
            data = {
                "id": cand.id,
                "name": cand.name_raw,
                "address": cand.address_raw,
                "url": cand.source_page.url,
                "equipment": cand.parsed_json.get("equipment") if cand.parsed_json else None,
                "raw_body": raw_body_snippet,
            }
            print(json.dumps(data, indent=2, ensure_ascii=False, default=_serialize))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_extraction.py <source_name> [limit]")
        sys.exit(1)

    source_name = sys.argv[1]
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    configure_engine()
    asyncio.run(verify_extraction(source_name, limit))
