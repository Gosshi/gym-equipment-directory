import asyncio
import logging

from sqlalchemy import select

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source
from scripts.ingest.parse_municipal_generic import parse_municipal_page
from scripts.ingest.sources_registry import SOURCES, MunicipalSource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill_tags():
    logger.info("Starting backfill of tags for GymCandidates...")

    async with SessionLocal() as session:
        # Fetch all candidates with their scraped page and source
        stmt = (
            select(GymCandidate, ScrapedPage, Source)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .join(Source, ScrapedPage.source_id == Source.id)
            .order_by(GymCandidate.id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        updated_count = 0

        for cand, page, source_model in rows:
            if not page or not page.raw_html:
                continue

            # Identify the source registry object
            # Note: Source.title in DB usually matches SOURCES key, e.g. "municipal_edogawa"
            # But sometimes it might be "江戸川区".
            # We need to map `page.source.id` (int) -> Source -> string key to find in SOURCES.
            # Assuming source.title maps to SOURCES key.

            # Simple heuristic: Look for matching source by checking URL or title
            target_source: MunicipalSource | None = None

            # Try exact match on title
            if source_model.title in SOURCES:
                target_source = SOURCES[source_model.title]

            if not target_source:
                # Try finding by title match in registry values
                for s in SOURCES.values():
                    if s.title == source_model.title:
                        target_source = s
                        break

            if not target_source:
                logger.debug(
                    f"Skipping candidate {cand.id}: Source '{source_model.title}' not found."
                )
                continue

            # Parse again
            try:
                # Parse with the correct logic
                result = parse_municipal_page(page.raw_html, page.url, source=target_source)

                # Check for tags
                if result.tags:
                    current_parsed = dict(cand.parsed_json) if cand.parsed_json else {}
                    current_tags = current_parsed.get("tags", [])

                    # If tags differ, update
                    if set(current_tags) != set(result.tags):
                        logger.info(
                            f"Updating cand {cand.id} ({cand.name_raw}): "
                            f"{current_tags} -> {result.tags}"
                        )
                        current_parsed["tags"] = result.tags
                        cand.parsed_json = current_parsed
                        updated_count += 1
            except Exception as e:
                logger.error(f"Failed to parse candidate {cand.id}: {e}")

        if updated_count > 0:
            logger.info(f"Committing {updated_count} updates...")
            await session.commit()
        else:
            logger.info("No updates needed.")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(backfill_tags())
