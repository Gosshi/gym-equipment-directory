"""
本番DBに入ってしまった seed_minimal_gyms.json のダミーデータを削除するスクリプト。
マスターデータ（equipments）は残し、架空の gyms と sources だけを消します。
"""

import logging
import os

from sqlalchemy import create_engine, text

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ダミーデータの識別子（seed_minimal_gyms.jsonに基づく）
DUMMY_GYM_SLUGS = [
    "shibuya-station-fit",
    "ebisu-garden-fit",
    "shinjuku-midtown-strength",
    "ikebukuro-park-conditioning",
    "kichijoji-loop-gym",
    "nakameguro-river-works",
    "meguro-hill-training",
    "yoyogi-coast-active",
    "akihabara-tech-fit",
    "kanda-station-conditioning",
    "yokohama-bay-front",
    "kawasaki-river-park",
    "sagamihara-green-station",
    "kamakura-seaside-gym",
    "oomiya-central-fit",
    "kawaguchi-bridge-gym",
    "tokorozawa-forest-active",
    "chiba-port-conditioning",
    "funabashi-station-power",
    "kashiwa-node-training",
]

DUMMY_SOURCE_TITLES = ["Metro Fit 公式サイト", "Canal Strength 特集記事", "首都圏ユーザー投稿"]


def cleanup():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("DATABASE_URL environment variable is not set.")
        return

    # 同期ドライバに変換 (asyncpg -> psycopg2)
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")

    engine = create_engine(db_url)

    with engine.begin() as conn:
        # 1. GymEquipments の削除（Gymに関連付いているもの）
        logger.info("Deleting dummy gym_equipments...")
        conn.execute(
            text("""
            DELETE FROM gym_equipments 
            WHERE gym_id IN (SELECT id FROM gyms WHERE slug IN :slugs)
        """),
            {"slugs": tuple(DUMMY_GYM_SLUGS)},
        )

        # 2. Gyms の削除
        logger.info("Deleting dummy gyms...")
        result_gyms = conn.execute(
            text("""
            DELETE FROM gyms WHERE slug IN :slugs
        """),
            {"slugs": tuple(DUMMY_GYM_SLUGS)},
        )
        logger.info(f"Deleted {result_gyms.rowcount} gyms.")

        # 3. Sources の削除
        logger.info("Deleting dummy sources...")
        result_sources = conn.execute(
            text("""
            DELETE FROM sources WHERE title IN :titles
        """),
            {"titles": tuple(DUMMY_SOURCE_TITLES)},
        )
        logger.info(f"Deleted {result_sources.rowcount} sources.")

    logger.info("Cleanup completed successfully.")


if __name__ == "__main__":
    cleanup()
