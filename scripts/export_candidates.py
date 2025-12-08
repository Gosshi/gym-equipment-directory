import asyncio
import json
from datetime import datetime

from sqlalchemy import select

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source


# JSON serialization helper
def json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


async def export_candidates(output_file: str):
    async with SessionLocal() as session:
        # Fetch candidates with their source page and source info
        stmt = (
            select(GymCandidate, ScrapedPage, Source)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .join(Source, ScrapedPage.source_id == Source.id)
            .order_by(GymCandidate.id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        print(f"Exporting {len(rows)} candidates to {output_file}...")

        with open(output_file, "w", encoding="utf-8") as f:
            for cand, page, source in rows:
                # Construct a dictionary with relevant fields
                data = {
                    "id": cand.id,
                    "name_raw": cand.name_raw,
                    "address_raw": cand.address_raw,
                    "pref_slug": cand.pref_slug,
                    "city_slug": cand.city_slug,
                    "latitude": cand.latitude,
                    "longitude": cand.longitude,
                    "parsed_json": cand.parsed_json,
                    "status": cand.status.value if cand.status else None,
                    "source_url": page.url,
                    "source_title": source.title,
                    "created_at": cand.created_at,
                    "updated_at": cand.updated_at,
                }

                # Write as JSON line
                f.write(json.dumps(data, default=json_serial, ensure_ascii=False) + "\n")

    print("Export complete.")


if __name__ == "__main__":
    import sys

    configure_engine()

    output_path = "gym_candidates_export.jsonl"
    if len(sys.argv) > 1:
        output_path = sys.argv[1]

    asyncio.run(export_candidates(output_path))
