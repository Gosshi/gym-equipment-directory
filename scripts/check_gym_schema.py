import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def check_schema():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set")
        return

    engine = create_async_engine(database_url)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'gyms'"
            )
        )
        rows = result.fetchall()
        print("Columns in 'gyms' table:")
        for row in rows:
            print(f"- {row[0]} ({row[1]})")


if __name__ == "__main__":
    asyncio.run(check_schema())
