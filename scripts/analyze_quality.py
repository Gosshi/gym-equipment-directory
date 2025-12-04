import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.db import SessionLocal, configure_engine
from app.models.gym_candidate import GymCandidate
from app.models.scraped_page import ScrapedPage
from app.models.source import Source


@dataclass
class QualityIssues:
    missing_name: int = 0
    missing_address: int = 0
    short_address: int = 0  # < 5 chars
    long_address: int = 0  # > 50 chars
    suspicious_address: int = 0  # contains TEL, FAX, http, etc.
    total_candidates: int = 0
    details: list[str] = field(default_factory=list)


async def analyze_quality():
    async with SessionLocal() as session:
        # Fetch all candidates with source info
        stmt = (
            select(GymCandidate, Source)
            .join(ScrapedPage, GymCandidate.source_page_id == ScrapedPage.id)
            .join(Source, ScrapedPage.source_id == Source.id)
            .options(joinedload(GymCandidate.source_page))
            .order_by(GymCandidate.id)
        )
        result = await session.execute(stmt)
        rows = result.all()

        print(f"Analyzing {len(rows)} candidates...")

        stats = defaultdict(QualityIssues)

        # Duplicate detection
        seen_names = defaultdict(list)
        seen_addresses = defaultdict(list)

        for cand, source in rows:
            source_title = source.title if source else "Unknown"
            s = stats[source_title]
            s.total_candidates += 1

            # Name Check
            if not cand.name_raw:
                s.missing_name += 1
                url = cand.source_page.url if cand.source_page else "N/A"
                s.details.append(f"[Missing Name] ID={cand.id} URL={url}")
            else:
                seen_names[cand.name_raw].append((cand.id, source_title))

            # Address Check
            addr = cand.address_raw
            if not addr:
                s.missing_address += 1
                s.details.append(f"[Missing Address] ID={cand.id} Name={cand.name_raw}")
            else:
                seen_addresses[addr].append((cand.id, source_title))

                if len(addr) < 5:
                    s.short_address += 1
                    s.details.append(f"[Short Address] ID={cand.id} Addr='{addr}'")

                if len(addr) > 50:
                    s.long_address += 1
                    s.details.append(f"[Long Address] ID={cand.id} Addr='{addr}'")

                suspicious_keywords = ["TEL", "FAX", "http", "電話", "ホームページ"]
                if any(k in addr for k in suspicious_keywords):
                    s.suspicious_address += 1
                    s.details.append(f"[Suspicious Address] ID={cand.id} Addr='{addr}'")

        # Report
        print("\n=== Quality Analysis Report ===\n")

        for source, s in sorted(stats.items()):
            print(f"Source: {source} (Total: {s.total_candidates})")
            if s.missing_name:
                print(f"  - Missing Name: {s.missing_name}")
            if s.missing_address:
                print(f"  - Missing Address: {s.missing_address}")
            if s.short_address:
                print(f"  - Short Address (<5): {s.short_address}")
            if s.long_address:
                print(f"  - Long Address (>50): {s.long_address}")
            if s.suspicious_address:
                print(f"  - Suspicious Address: {s.suspicious_address}")
            if s.details:
                print("  - Issues Sample:")
                for d in s.details[:5]:  # Show top 5
                    print(f"    {d}")
            print("")

        print("\n=== Potential Duplicates (Global) ===\n")

        dup_name_count = 0
        for name, ids in seen_names.items():
            if len(ids) > 1:
                dup_name_count += 1
                # print(f"Name '{name}': {ids}")

        dup_addr_count = 0
        for addr, ids in seen_addresses.items():
            if len(ids) > 1:
                dup_addr_count += 1
                # print(f"Address '{addr}': {ids}")

        print(f"Total Duplicate Names: {dup_name_count}")
        print(f"Total Duplicate Addresses: {dup_addr_count}")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(analyze_quality())
