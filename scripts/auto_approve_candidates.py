import argparse
import asyncio
import logging
import math
import os
import re
import sys
import unicodedata
import uuid
from difflib import SequenceMatcher

# Add current directory to sys.path to ensure module imports work
sys.path.append(os.getcwd())

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, configure_engine
from app.models.gym import Gym
from app.models.gym_candidate import CandidateStatus, GymCandidate

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_distance(
    lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None
) -> float | None:
    """Calculate Haversine distance in kilometers between two points."""
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def normalize_address(text: str | None) -> str:
    """Normalize Japanese address for fuzzy matching."""
    if not text:
        return ""

    # NFKC Normalization (Full-width to Half-width)
    normalized = unicodedata.normalize("NFKC", text)

    # Remove whitespace
    normalized = normalized.replace(" ", "").replace("　", "")

    # Kanji numbers to standard numbers (Simplified)
    # Mapping common ones found in addresses
    kanji_map = str.maketrans("一二三四五六七八九〇", "1234567890")
    normalized = normalized.translate(kanji_map)

    # Common variations normalization
    normalized = normalized.replace("F", "階").replace("f", "階")

    # Standardize separators
    # Convert '丁目', '番', '号', '番地' to '-'
    normalized = re.sub(r"丁目|番地|番|号", "-", normalized)

    # Remove trailing hyphens
    normalized = normalized.strip("-")

    return normalized


def is_name_similar(name1: str, name2: str, threshold: float = 0.8) -> bool:
    """Check if two facility names are similar."""
    if not name1 or not name2:
        return False

    # Normalize names
    n1 = unicodedata.normalize("NFKC", name1).replace(" ", "")
    n2 = unicodedata.normalize("NFKC", name2).replace(" ", "")

    # Check containment (High confidence if one is substring of another for long names)
    if len(n1) > 5 and n1 in n2:
        return True
    if len(n2) > 5 and n2 in n1:
        return True

    ratio = SequenceMatcher(None, n1, n2).ratio()
    return ratio >= threshold


# Trusted domains that are safe to auto-approve
TRUSTED_DOMAINS = {
    "city.chuo.lg.jp",
    "city.koto.lg.jp",
    "city.minato.tokyo.jp",
    "city.shinjuku.lg.jp",
    "city.bunkyo.lg.jp",
    "city.taito.lg.jp",
    "city.sumida.lg.jp",
    "city.shinagawa.tokyo.jp",
    "city.meguro.tokyo.jp",
    "city.ota.tokyo.jp",
    "city.setagaya.lg.jp",
    "city.shibuya.tokyo.jp",
    "city.nakano.tokyo.jp",
    "city.suginami.tokyo.jp",
    "city.toshima.lg.jp",
    "city.kita.tokyo.jp",
    "city.arakawa.tokyo.jp",
    "city.itabashi.tokyo.jp",
    "city.nerima.tokyo.jp",
    "city.adachi.tokyo.jp",
    "city.katsushika.lg.jp",
    "city.edogawa.tokyo.jp",
    "konami.com",
    "central.co.jp",
    "renaissance.co.jp",
    "tipness.co.jp",
    "megalos.co.jp",
    "jexer.jp",
    "goldgym.jp",
    "joyfit.jp",
    "anytimefitness.co.jp",
    "choco-zap.jp",
    "fastgym24.jp",
    "curves.co.jp",
}


def is_trusted_source(url: str | None) -> bool:
    if not url:
        return False
    try:
        from urllib.parse import urlparse

        domain = urlparse(url).netloc
        # Allow exact match or subdomain
        for trusted in TRUSTED_DOMAINS:
            if domain == trusted or domain.endswith("." + trusted):
                return True
        return False
    except Exception:
        return False


def is_valid_address(address: str | None) -> bool:
    if not address:
        return False
    # Must contain at least one digit (for chome/banchi)
    if not any(char.isdigit() for char in address):
        return False
    # Must not be too short
    if len(address) < 5:
        return False
    return True


async def auto_approve_candidates(dry_run: bool = True) -> dict[str, int]:
    logger.info(f"Starting auto-approval (Phase 2: Distance Check) (DRY_RUN={dry_run})...")

    async with SessionLocal() as session:
        # 1. Fetch all 'new' candidates with source_page loaded
        stmt = (
            select(GymCandidate)
            .where(GymCandidate.status == CandidateStatus.new)
            .options(selectinload(GymCandidate.source_page))
            .order_by(GymCandidate.id)
        )
        result = await session.execute(stmt)
        candidates = result.scalars().all()

        stmt_gyms = select(Gym)
        result_gyms = await session.execute(stmt_gyms)
        existing_gyms = result_gyms.scalars().all()

        # Pre-process existing gyms for faster lookup
        gyms_by_url = {g.official_url: g for g in existing_gyms if g.official_url}
        gyms_by_city = {}
        for g in existing_gyms:
            if g.city:
                gyms_by_city.setdefault(g.city, []).append(g)

        approved_count = 0
        merged_count = 0
        skipped_count = 0

        for cand in candidates:
            cand_id_str = f"[ID:{cand.id}] {cand.name_raw}"
            if not cand.name_raw:
                skipped_count += 1
                continue

            parsed = cand.parsed_json or {}
            cand_url = cand.source_page.url if cand.source_page else None
            cand_city = cand.city_slug

            # --- MATCHING LOGIC ---
            matched_gym: Gym | None = None
            match_reason = ""

            # 1. Match by URL (Exact)
            if cand_url and cand_url in gyms_by_url:
                matched_gym = gyms_by_url[cand_url]
                match_reason = "URL"

            # 2. Match by Address (Normalized)
            if not matched_gym and cand.address_raw:
                c_norm_addr = normalize_address(cand.address_raw)
                if c_norm_addr:
                    for g in existing_gyms:
                        if g.address and normalize_address(g.address) == c_norm_addr:
                            matched_gym = g
                            match_reason = "Address (Normalized)"
                            break

            # 3. Match by Distance + Name Fuzzy
            if not matched_gym:
                search_pool = gyms_by_city.get(cand_city, []) if cand_city else existing_gyms

                best_match = None
                best_score = 0.0

                for g in search_pool:
                    # Calculate Distance
                    dist = calculate_distance(
                        cand.latitude, cand.longitude, g.latitude, g.longitude
                    )

                    # Calculate Name Sim
                    sim = SequenceMatcher(None, cand.name_raw, g.name).ratio()

                    is_match = False
                    reason = ""

                    # Logic A: Very close (< 100m) AND Somewhat similar name (> 0.4)
                    if dist is not None and dist < 0.1 and sim > 0.4:
                        is_match = True
                        reason = f"Distance ({dist * 1000:.0f}m) & NameSim ({sim:.2f})"

                    # Logic B: Same City AND High Name Sim (> 0.8) (fallback for no coords)
                    elif dist is None and cand_city == g.city and sim > 0.8:
                        is_match = True
                        reason = f"Same City & NameSim ({sim:.2f})"

                    if is_match and sim > best_score:
                        best_match = g
                        best_score = sim
                        match_reason = reason

                if best_match:
                    matched_gym = best_match

            # --- ACTION ---

            if matched_gym:
                logger.info(f"MATCH: {cand_id_str} -> {matched_gym.name} [{match_reason}]")

                # MERGE TAGS
                current_tags = set((matched_gym.parsed_json or {}).get("tags", []))
                new_tags = set(parsed.get("tags", []))

                if not new_tags.issubset(current_tags):
                    merged_tags = list(current_tags | new_tags)
                    logger.info(f"  -> Merging tags: {new_tags - current_tags}")
                    if not dry_run:
                        g_parsed = dict(matched_gym.parsed_json) if matched_gym.parsed_json else {}
                        g_parsed["tags"] = merged_tags
                        matched_gym.parsed_json = g_parsed

                # Update Candidate Status
                logger.info(f"  -> ACTION: IGNORE (Merged to {matched_gym.name})")
                if not dry_run:
                    cand.status = CandidateStatus.ignored
                merged_count += 1

            else:
                # CREATE NEW GYM?
                # Note: is_gym flag from LLM means "is a valid facility page"
                # It should be True for all categories (gym, pool, court, hall, field, etc.)
                is_valid_facility = parsed.get("is_gym")

                # Also check if category is set - this indicates LLM found a valid facility
                # even if is_gym was not explicitly set to True
                meta = parsed.get("meta", {})
                category = meta.get("category") or cand.category
                # Get categories array (new format) or fallback to single category
                categories = meta.get("categories") or ([category] if category else [])
                valid_categories = {
                    "gym",
                    "pool",
                    "court",
                    "hall",
                    "field",
                    "martial_arts",
                    "archery",
                }
                has_valid_category = any(c in valid_categories for c in categories)

                has_addr = is_valid_address(cand.address_raw)
                is_trusted = is_trusted_source(cand_url)

                # Approve if: (is_gym=True OR valid category) AND has address AND trusted source
                if (is_valid_facility or has_valid_category) and has_addr and is_trusted:
                    logger.info(f"APPROVED: {cand_id_str} (categories: {categories})")
                    if not dry_run:
                        # Create Gym logic
                        new_slug = f"gym-{uuid.uuid4().hex[:8]}"

                        new_gym = Gym(
                            name=cand.name_raw,
                            address=cand.address_raw,
                            pref=cand.pref_slug,  # assuming these match
                            city=cand.city_slug,
                            official_url=cand_url,
                            latitude=cand.latitude,
                            longitude=cand.longitude,
                            parsed_json=parsed,
                            slug=new_slug,
                            canonical_id=uuid.uuid4(),
                            created_at=cand.created_at,  # inherit
                            category=category,  # Legacy: primary category
                            categories=categories,  # New: all categories
                        )
                        session.add(new_gym)
                        await session.flush()  # to get ID
                        cand.status = CandidateStatus.approved

                    approved_count += 1
                else:
                    # Leave as 'new' for manual review
                    reasons = []
                    if not is_valid_facility and not has_valid_category:
                        reasons.append(f"No valid category (got: {category})")
                    if not has_addr:
                        reasons.append("Invalid address")
                    if not is_trusted:
                        reasons.append("Untrusted source")
                    logger.info(f"SKIPPED: {cand_id_str} Reason: {', '.join(reasons)}")
                    skipped_count += 1

        if not dry_run:
            await session.commit()
            logger.info("Changes committed to database.")
        else:
            logger.info("DRY RUN: No changes committed.")

        summary = {
            "merged": merged_count,
            "approved": approved_count,
            "skipped": skipped_count,
        }
        logger.info(f"Summary: {summary}")
        return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--commit", action="store_true", help="Commit changes to DB")
    args = parser.parse_args()

    configure_engine()
    # If --commit is NOT present, it is a dry run (default safe)
    asyncio.run(auto_approve_candidates(dry_run=not args.commit))
