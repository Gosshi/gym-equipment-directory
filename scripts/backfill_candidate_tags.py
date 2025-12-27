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
        # 1. Fetch ALL Candidate IDs first (lightweight)
        stmt_ids = select(GymCandidate.id).order_by(GymCandidate.id)
        result_ids = await session.execute(stmt_ids)
        all_ids = result_ids.scalars().all()

        total_candidates = len(all_ids)
        logger.info(f"Found {total_candidates} candidates to process.")

        BATCH_SIZE = 50
        updated_count = 0

        # 2. Process in batches
        for i in range(0, total_candidates, BATCH_SIZE):
            batch_ids = all_ids[i : i + BATCH_SIZE]

            # Fetch full objects for this batch
            stmt_batch = (
                select(GymCandidate, ScrapedPage, Source)
                .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
                .join(Source, ScrapedPage.source_id == Source.id)
                .where(GymCandidate.id.in_(batch_ids))
            )
            result_batch = await session.execute(stmt_batch)
            rows = result_batch.all()

            batch_updates = 0

            for cand, page, source_model in rows:
                if not page or not page.raw_html:
                    continue

                # Identify the source registry object
                target_source: MunicipalSource | None = None
                if source_model.title in SOURCES:
                    target_source = SOURCES[source_model.title]

                if not target_source:
                    for s in SOURCES.values():
                        if s.title == source_model.title:
                            target_source = s
                            break

                if not target_source:
                    logger.debug(
                        f"Skipping candidate {cand.id}: Source '{source_model.title}' not found."
                    )
                    continue

                try:
                    result = await parse_municipal_page(
                        page.raw_html, page.url, source=target_source
                    )

                    # Check rejection (Noise Filtering)
                    if result.meta and result.meta.get("create_gym") is False:
                        reason = result.meta.get("reason", "parser_rejection")
                        logger.warning(
                            f"Candidate {cand.id} ({cand.name_raw}) rejected by parser: {reason}"
                        )
                        # Log but don't delete automatically yet
                        # or use rejected status if implemented
                        # For now, just logging to identify bad entries
                        pass

                    # Update Name
                    if result.facility_name and result.facility_name != cand.name_raw:
                        logger.info(
                            f"Updating name for {cand.id}: "
                            f"'{cand.name_raw}' -> '{result.facility_name}'"
                        )
                        cand.name_raw = result.facility_name
                        batch_updates += 1
                        updated_count += 1

                    # Update Address (Fix existing wrong addresses)
                    if result.address and result.address != cand.address_raw:
                        logger.info(
                            f"Updating address for {cand.id}:"
                            f"'{cand.address_raw}' -> '{result.address}'"
                        )
                        cand.address_raw = result.address
                        batch_updates += 1
                        updated_count += 1

                    # Update Tags
                    if result.tags:
                        current_parsed = dict(cand.parsed_json) if cand.parsed_json else {}
                        current_tags = current_parsed.get("tags", [])
                        if set(current_tags) != set(result.tags):
                            logger.info(
                                f"Updating tags for {cand.id} ({cand.name_raw}): "
                                f"{current_tags} -> {result.tags}"
                            )
                            current_parsed["tags"] = result.tags
                            cand.parsed_json = current_parsed
                            batch_updates += 1
                            updated_count += 1

                except Exception as e:
                    logger.error(f"Failed to parse candidate {cand.id}: {e}")

            # Commit per batch
            if batch_updates > 0:
                await session.commit()

            # Clear session identity map to free memory
            session.expire_all()

        logger.info(f"Backfill complete. Total updates: {updated_count}")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(backfill_tags())
