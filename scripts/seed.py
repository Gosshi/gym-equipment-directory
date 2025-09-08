import asyncio
import os
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.base import Base
from app.models.equipment import Equipment
from app.models.gym import Gym
from app.models.gym_equipment import GymEquipment

DB_URL = os.environ["DATABASE_URL"]
engine = create_async_engine(DB_URL, future=True)
Session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def upsert_equipment(session, slug, name, category):
    eq = await session.scalar(select(Equipment).where(Equipment.slug == slug))
    if not eq:
        eq = Equipment(slug=slug, name=name, category=category)
        session.add(eq)
        await session.flush()
    return eq


async def upsert_gym(session, slug, name, pref, city, last_verified_at=None, created_at=None):
    g = await session.scalar(select(Gym).where(Gym.slug == slug))
    if not g:
        g = Gym(
            slug=slug,
            name=name,
            pref=pref,
            city=city,
            last_verified_at_cached=last_verified_at,
            created_at=created_at or datetime.utcnow(),
        )
        session.add(g)
        await session.flush()
    else:
        # 軽く更新
        g.name = name
        g.pref = pref
        g.city = city
        if last_verified_at is not None:
            g.last_verified_at_cached = last_verified_at
    return g


async def upsert_gym_equipment(session, gym, eq, count=None, max_kg=None):
    ge = await session.scalar(
        select(GymEquipment).where(
            GymEquipment.gym_id == gym.id, GymEquipment.equipment_id == eq.id
        )
    )
    if not ge:
        ge = GymEquipment(
            gym_id=gym.id,
            equipment_id=eq.id,
            count=count,
            max_weight_kg=max_kg,
            last_verified_at=datetime.utcnow(),
        )
        session.add(ge)
    else:
        ge.count = count
        ge.max_weight_kg = max_kg
        ge.last_verified_at = datetime.utcnow()
    return ge


async def main():
    async with engine.begin() as conn:
        # 念のためテーブルが無ければ作る（既にあればNOP）
        await conn.run_sync(Base.metadata.create_all)

    async with Session() as session:
        # まずはクリーンにしたい場合はコメント解除
        # await session.execute(delete(GymEquipment))
        # await session.execute(delete(Gym))
        # await session.execute(delete(Equipment))

        # ---- Equipments ----
        squat = await upsert_equipment(session, "squat-rack", "Squat Rack", "strength")
        dbell = await upsert_equipment(session, "dumbbell", "Dumbbell", "strength")
        bench = await upsert_equipment(session, "bench-press", "Bench Press", "strength")
        cable = await upsert_equipment(session, "cable-machine", "Cable Machine", "strength")

        now = datetime.utcnow()
        # ---- Gyms ----
        g1 = await upsert_gym(
            session,
            "chiba-funabashi-alpha",
            "Alpha Gym",
            "chiba",
            "funabashi",
            last_verified_at=now - timedelta(days=2),
        )
        g2 = await upsert_gym(
            session,
            "chiba-funabashi-beta",
            "Beta Gym",
            "chiba",
            "funabashi",
            last_verified_at=now - timedelta(days=10),
        )
        g3 = await upsert_gym(
            session,
            "tokyo-edogawa-gamma",
            "Gamma Gym",
            "tokyo",
            "edogawa",
            last_verified_at=now - timedelta(days=1),
        )

        # ---- Inventory (richness 用の差分が出るように) ----
        await upsert_gym_equipment(session, g1, squat, count=2, max_kg=140)
        await upsert_gym_equipment(session, g1, dbell, count=1, max_kg=30)

        await upsert_gym_equipment(session, g2, bench, count=1, max_kg=80)

        await upsert_gym_equipment(session, g3, squat, count=1, max_kg=100)
        await upsert_gym_equipment(session, g3, cable, count=None, max_kg=None)

        await session.commit()
        print("✅ Seed inserted/updated.")


asyncio.run(main())
