from datetime import date

from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models.api_usage import ApiUsage


async def record_api_usage(service: str, metric: str, value: int = 1):
    """
    Record API usage to the database.
    Increments the value if a record already exists for today.
    """
    today = date.today()

    async with SessionLocal() as session:
        stmt = (
            insert(ApiUsage)
            .values(service=service, metric=metric, value=value, date=today)
            .on_conflict_do_update(
                index_elements=["service", "metric", "date"],
                set_={"value": ApiUsage.value + value},
            )
        )
        await session.execute(stmt)
        await session.commit()
