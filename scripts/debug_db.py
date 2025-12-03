import asyncio

from sqlalchemy import func, select

from app.db import SessionLocal, configure_engine
from app.models.scraped_page import ScrapedPage
from app.models.source import Source


async def debug_db():
    async with SessionLocal() as session:
        sources = [
            "municipal_shinagawa",
            "municipal_meguro",
            "municipal_ota",
            "municipal_setagaya",
            "municipal_shibuya",
            "municipal_nakano",
            "municipal_suginami",
            "municipal_toshima",
            "municipal_kita",
            "municipal_itabashi",
            "municipal_nerima",
        ]
        for title in sources:
            source = await session.scalar(select(Source).where(Source.title == title))
            if source:
                count = await session.scalar(
                    select(func.count()).where(ScrapedPage.source_id == source.id)
                )
                print(f"Source: {title}, ID: {source.id}, Pages: {count}")
            else:
                print(f"Source: {title} NOT FOUND")


if __name__ == "__main__":
    configure_engine()
    asyncio.run(debug_db())
