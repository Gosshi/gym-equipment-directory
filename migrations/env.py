# migrations/env.py
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.models.base import Base  # ← MetaData をここから

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _get_sqlalchemy_url() -> str:
    # Prefer ALEMBIC_DATABASE_URL, then DATABASE_URL, else alembic.ini
    url = os.getenv("ALEMBIC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        return config.get_main_option("sqlalchemy.url")
    # Alembic requires sync driver; coerce +asyncpg → +psycopg2 for migrations
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "+psycopg2")
    if "+psycopg" in url and "+psycopg2" not in url:
        # normalize psycopg3 URL to psycopg2 if needed
        url = url.replace("+psycopg", "+psycopg2")
    return url


target_metadata = Base.metadata


def run_migrations_offline():
    url = _get_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = _get_sqlalchemy_url()
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
