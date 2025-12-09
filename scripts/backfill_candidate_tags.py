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

        # Determine batch size
        BATCH_SIZE = 50

        # Use server-side cursor to iterate
        result = await session.stream(stmt.execution_options(yield_per=BATCH_SIZE))

        updated_count = 0
        batch_updates = 0

        async for cand, page, source_model in result:
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

                # Check rejection (Noise Filtering)
                if result.meta and result.meta.get("create_gym") is False:
                    reason = result.meta.get("reason", "parser_rejection")
                    logger.warning(
                        f"Candidate {cand.id} ({cand.name_raw}) rejected by parser: {reason}"
                    )
                    # Use 'rejected' status if available, or just log for now?
                    # Assuming 'new' -> 'rejected' is valid transition.
                    # We need to make sure we don't overwrite approved ones.
                    if cand.status.value == "new":
                        # Ideally we should set explicit enum
                        # The local model def uses SQLEnum.
                        logger.info(f"  -> Suggest deleting/rejecting candidate {cand.id}")
                        pass

                # Update Name (Generic Fix)
                if result.facility_name and result.facility_name != cand.name_raw:
                    logger.info(
                        f"Updating name for {cand.id}: "
                        f"'{cand.name_raw}' -> '{result.facility_name}'"
                    )
                    cand.name_raw = result.facility_name
                    updated_count += 1

                # Update Address (Bonus)
                if result.address and not cand.address_raw:
                    logger.info(f"Filling missing address for {cand.id}: {result.address}")
                    cand.address_raw = result.address
                    updated_count += 1
                    batch_updates += 1

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
                        batch_updates += 1
            except Exception as e:
                logger.error(f"Failed to parse candidate {cand.id}: {e}")

            # Periodic Commit
            if batch_updates >= 10:
                await session.commit()
                batch_updates = 0

        # Final commit
        if batch_updates > 0:
            logger.info(f"Committing final {batch_updates} updates...")
            await session.commit()

        logger.info(f"Backfill complete. Total updates: {updated_count}")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(backfill_tags())
