from __future__ import annotations

import os

from sqlalchemy import create_engine, text


def _database_url() -> str:
    url = os.environ["DATABASE_URL"]
    return url.replace("+asyncpg", "")


def main() -> None:
    engine = create_engine(_database_url(), future=True, pool_pre_ping=True)

    stmts = [
        text(
            """
            insert into equipments (slug, name, category)
            values ('sample-barbell', 'サンプルバーベル', 'free_weight')
            on conflict do nothing
            """
        ),
        text(
            """
            insert into gyms (slug, name, pref, city, address)
            values (
                'sample-gym',
                'サンプル・ジム',
                'tokyo',
                'shinjuku',
                '東京都新宿区サンプル1-1-1'
            )
            on conflict do nothing
            """
        ),
    ]

    with engine.begin() as conn:
        for stmt in stmts:
            conn.execute(stmt)

    print("seed_minimal: done")


if __name__ == "__main__":
    main()
