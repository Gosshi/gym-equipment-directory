# scripts/seed.py
"""
完全ダミーの初期データ(seed)を投入します。
何度実行しても重複しにくいよう、slug/名称でget-or-createします。
"""

from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import Session
import os
import sys

# パス調整（repo 直下から実行する前提）
sys.path.append(os.path.abspath("."))

from app.db import engine, SessionLocal
from app.models import (
    Gym, Equipment, GymEquipment, Source,
    Availability, VerificationStatus, SourceType
)

def get_or_create_equipment(sess: Session, slug: str, name: str, category: str, desc: str = None):
    eq = sess.execute(select(Equipment).where(Equipment.slug == slug)).scalar_one_or_none()
    if eq:
        return eq
    eq = Equipment(slug=slug, name=name, category=category, description=desc)
    sess.add(eq)
    sess.flush()
    return eq

def get_or_create_gym(sess: Session, slug: str, name: str, pref: str, city: str, address: str, official_url: str = None):
    g = sess.execute(select(Gym).where(Gym.slug == slug)).scalar_one_or_none()
    if g:
        return g
    g = Gym(
        slug=slug, name=name, pref=pref, city=city,
        address=address, official_url=official_url
    )
    sess.add(g)
    sess.flush()
    return g

def link_gym_equipment(sess: Session, gym: Gym, eq: Equipment,
                       availability: Availability, count=None, max_weight_kg=None,
                       verification_status: VerificationStatus = VerificationStatus.unverified,
                       source: Source | None = None, last_verified_at: datetime | None = None, notes: str | None = None):
    ge = sess.execute(
        select(GymEquipment).where(
            (GymEquipment.gym_id == gym.id) & (GymEquipment.equipment_id == eq.id)
        )
    ).scalar_one_or_none()
    if ge:
        # 既存は軽く更新（初回seedなら基本通らない）
        ge.availability = availability
        ge.count = count
        ge.max_weight_kg = max_weight_kg
        ge.verification_status = verification_status
        ge.source_id = source.id if source else None
        ge.last_verified_at = last_verified_at
        ge.notes = notes
        return ge

    ge = GymEquipment(
        gym_id=gym.id,
        equipment_id=eq.id,
        availability=availability,
        count=count,
        max_weight_kg=max_weight_kg,
        verification_status=verification_status,
        source_id=source.id if source else None,
        last_verified_at=last_verified_at,
        notes=notes
    )
    sess.add(ge)
    return ge

def get_or_create_source(sess: Session, stype: SourceType, title: str = None, url: str = None, captured_at: datetime | None = None):
    # ダミーなので厳密一意までは見ないが、同一title/urlなら再利用
    q = select(Source).where(Source.source_type == stype)
    if title:
        q = q.where(Source.title == title)
    if url:
        q = q.where(Source.url == url)
    src = sess.execute(q).scalar_one_or_none()
    if src:
        return src
    src = Source(source_type=stype, title=title, url=url, captured_at=captured_at)
    sess.add(src)
    sess.flush()
    return src

def main():
    # ---- 1) ダミーの設備マスター（20件弱、必要なら追加してOK）
    equipment_seed = [
        ("squat-rack", "スクワットラック", "free_weight"),
        ("bench-press", "ベンチプレス", "free_weight"),
        ("dumbbell", "ダンベル", "free_weight"),
        ("smith-machine", "スミスマシン", "free_weight"),
        ("power-rack", "パワーラック", "free_weight"),
        ("lat-pulldown", "ラットプルダウン", "machine"),
        ("chest-press", "チェストプレス", "machine"),
        ("leg-press", "レッグプレス", "machine"),
        ("leg-curl", "レッグカール", "machine"),
        ("leg-extension", "レッグエクステンション", "machine"),
        ("pec-deck", "ペックデック", "machine"),
        ("treadmill", "トレッドミル", "cardio"),
        ("bike", "エアロバイク", "cardio"),
        ("elliptical", "クロストレーナー", "cardio"),
        ("rowing", "ローイングマシン", "cardio"),
        ("stretch-area", "ストレッチエリア", "other"),
        ("cable-machine", "ケーブルマシン", "machine"),
        ("hack-squat", "ハックスクワット", "machine"),
        ("dip-bar", "ディップバー", "free_weight"),
        ("pullup-bar", "懸垂バー", "free_weight"),
    ]

    # ---- 2) ダミーのジム（5件）
    gym_seed = [
        ("dummy-funabashi-east",     "ダミージム 船橋イースト", "chiba", "funabashi", "千葉県船橋市東町1-1-1", None),
        ("dummy-funabashi-west",     "ダミージム 船橋ウエスト", "chiba", "funabashi", "千葉県船橋市西町1-2-3", None),
        ("dummy-tsudanuma-center",   "ダミージム 津田沼センター", "chiba", "narashino", "千葉県習志野市谷津1-2-3", None),
        ("dummy-hilton-bay",         "ダミーホテルジム ベイ", "chiba", "urayasu", "千葉県浦安市舞浜1-1-1", None),
        ("dummy-makuhari-coast",     "ダミージム 幕張コースト", "chiba", "chiba", "千葉県千葉市美浜区中瀬1-1-1", None),
    ]

    # ---- 3) 設備 × ジム 対応（有/無/不明を混ぜる）
    # 例： (gym_slug, equipment_slug, availability, count, max_weight_kg)
    ge_seed = [
        ("dummy-funabashi-east",   "squat-rack",  Availability.present, 2, None),
        ("dummy-funabashi-east",   "bench-press", Availability.present, 3, None),
        ("dummy-funabashi-east",   "dumbbell",    Availability.present, None, 40),
        ("dummy-funabashi-east",   "treadmill",   Availability.present, 6, None),
        ("dummy-funabashi-east",   "bike",        Availability.unknown, None, None),

        ("dummy-funabashi-west",   "squat-rack",  Availability.absent,  None, None),
        ("dummy-funabashi-west",   "smith-machine", Availability.present, 1, None),
        ("dummy-funabashi-west",   "treadmill",   Availability.present, 4, None),
        ("dummy-funabashi-west",   "dumbbell",    Availability.present, None, 30),

        ("dummy-tsudanuma-center", "power-rack",  Availability.present, 1, None),
        ("dummy-tsudanuma-center", "bench-press", Availability.present, 2, None),
        ("dummy-tsudanuma-center", "elliptical",  Availability.present, 2, None),

        ("dummy-hilton-bay",       "dumbbell",    Availability.present, None, 20),
        ("dummy-hilton-bay",       "treadmill",   Availability.present, 3, None),
        ("dummy-hilton-bay",       "squat-rack",  Availability.absent,  None, None),

        ("dummy-makuhari-coast",   "lat-pulldown",Availability.present, 1, None),
        ("dummy-makuhari-coast",   "leg-press",   Availability.present, 1, None),
        ("dummy-makuhari-coast",   "rowing",      Availability.unknown, None, None),
    ]

    with SessionLocal() as sess:
        # Source（出典）もダミーで1つ用意
        src = get_or_create_source(
            sess,
            stype=SourceType.user_submission,
            title="ダミー投稿（seed）",
            url=None,
            captured_at=datetime.utcnow()
        )

        # equipments
        slug_to_eq = {}
        for slug, name, cat in equipment_seed:
            eq = get_or_create_equipment(sess, slug=slug, name=name, category=cat)
            slug_to_eq[slug] = eq

        # gyms
        slug_to_gym = {}
        for slug, name, pref, city, addr, url in gym_seed:
            g = get_or_create_gym(sess, slug=slug, name=name, pref=pref, city=city, address=addr, official_url=url)
            slug_to_gym[slug] = g

        sess.commit()  # ここでIDが確定

        # gym_equipments
        now = datetime.utcnow()
        for gym_slug, eq_slug, avail, count, max_w in ge_seed:
            g = slug_to_gym[gym_slug]
            e = slug_to_eq[eq_slug]
            link_gym_equipment(
                sess, g, e,
                availability=avail,
                count=count,
                max_weight_kg=max_w,
                verification_status=VerificationStatus.user_verified if avail == Availability.present else VerificationStatus.unverified,
                source=src,
                last_verified_at=now
            )
        sess.commit()

    print("✅ Seed completed.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

# コンテナ起動済みの前提
# docker compose exec api python scripts/seed.py
# => ✅ Seed completed.

