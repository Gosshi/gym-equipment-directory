import asyncio
import os

from dotenv import load_dotenv
from sqlalchemy import Column, Float, Integer, String, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()


class Gym(Base):
    __tablename__ = "gyms"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    status = Column(String)  # Checking this field
    latitude = Column(Float)
    longitude = Column(Float)
    pref = Column(String)
    city = Column(String)


async def check_gym_status():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set")
        return

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Gym).where(Gym.id.in_([65, 66]))
        result = await session.execute(stmt)
        gyms = result.scalars().all()

        print(f"Found {len(gyms)} gyms.")
        for g in gyms:
            print(
                f"ID: {g.id}, Name: {g.name}, Status: {g.status}, "
                f"Lat: {g.latitude}, Lng: {g.longitude}"
            )


if __name__ == "__main__":
    asyncio.run(check_gym_status())
