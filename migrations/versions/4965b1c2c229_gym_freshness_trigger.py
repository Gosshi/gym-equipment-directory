"""gym freshness trigger

Revision ID: 4965b1c2c229
Revises: 5c002a33eee9
Create Date: 2025-09-04 23:40:02.256087

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4965b1c2c229"
down_revision: Union[str, None] = "5c002a33eee9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.execute("""
    -- 必須列（無ければ作成）
    ALTER TABLE gyms        ADD COLUMN IF NOT EXISTS last_verified_at         TIMESTAMPTZ;
    ALTER TABLE gyms        ADD COLUMN IF NOT EXISTS last_verified_at_cached  TIMESTAMPTZ;
    ALTER TABLE equipments  ADD COLUMN IF NOT EXISTS last_verified_at         TIMESTAMPTZ;

    -- 汎用：指定 gym の cached を再計算（多対多対応）
    CREATE OR REPLACE FUNCTION REFRESH_GYM_FRESHNESS(p_gym_id BIGINT)
    RETURNS VOID
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_equipment_max TIMESTAMPTZ;
        v_gym_ts        TIMESTAMPTZ;
        v_new_cached    TIMESTAMPTZ;
    BEGIN
        SELECT MAX(e.last_verified_at) INTO v_equipment_max
        FROM gym_equipments ge
        JOIN equipments e ON e.id = ge.equipment_id
        WHERE ge.gym_id = p_gym_id;

        SELECT g.last_verified_at INTO v_gym_ts
        FROM gyms g
        WHERE g.id = p_gym_id
        FOR UPDATE;

        v_new_cached := GREATEST(
            COALESCE(v_gym_ts,        '-infinity'::timestamptz),
            COALESCE(v_equipment_max, '-infinity'::timestamptz)
        );

        UPDATE gyms
        SET last_verified_at_cached = v_new_cached
        WHERE id = p_gym_id;
    END;
    $$;

    -- トリガ用ラッパー：equipments の INS/UPD 用（紐づく全 gym を更新）
    CREATE OR REPLACE FUNCTION trg_refresh_on_equipment_insupd()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_eid BIGINT := COALESCE(NEW.id, OLD.id);
        v_gid BIGINT;
    BEGIN
        FOR v_gid IN
            SELECT ge.gym_id FROM gym_equipments ge WHERE ge.equipment_id = v_eid
        LOOP
            PERFORM REFRESH_GYM_FRESHNESS(v_gid);
        END LOOP;
        RETURN NULL;
    END;
    $$;

    -- トリガ用ラッパー：equipments の DEL 用（DEL でも上と同様に全 gym を更新）
    CREATE OR REPLACE FUNCTION trg_refresh_on_equipment_del()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    DECLARE
        v_eid BIGINT := COALESCE(NEW.id, OLD.id);
        v_gid BIGINT;
    BEGIN
        FOR v_gid IN
            SELECT ge.gym_id FROM gym_equipments ge WHERE ge.equipment_id = v_eid
        LOOP
            PERFORM REFRESH_GYM_FRESHNESS(v_gid);
        END LOOP;
        RETURN NULL;
    END;
    $$;

    -- トリガ用ラッパー：gym_equipments の INS 用（1 gym を更新）
    CREATE OR REPLACE FUNCTION trg_refresh_on_link_ins()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        PERFORM REFRESH_GYM_FRESHNESS(NEW.gym_id);
        RETURN NULL;
    END;
    $$;

    -- トリガ用ラッパー：gym_equipments の DEL 用（1 gym を更新）
    CREATE OR REPLACE FUNCTION trg_refresh_on_link_del()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        PERFORM REFRESH_GYM_FRESHNESS(OLD.gym_id);
        RETURN NULL;
    END;
    $$;

    -- トリガ用ラッパー：gyms の last_verified_at 変更時
    CREATE OR REPLACE FUNCTION trg_refresh_on_gym_ts()
    RETURNS TRIGGER
    LANGUAGE plpgsql
    AS $$
    BEGIN
        IF (OLD.last_verified_at IS DISTINCT FROM NEW.last_verified_at) THEN
            PERFORM REFRESH_GYM_FRESHNESS(NEW.id);
        END IF;
        RETURN NULL;
    END;
    $$;

    -- 既存トリガ削除（念のため）
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_insupd ON equipments;
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_del    ON equipments;
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_on_gym ON gyms;
    DROP TRIGGER IF EXISTS trg_refresh_on_link_ins          ON gym_equipments;
    DROP TRIGGER IF EXISTS trg_refresh_on_link_del          ON gym_equipments;

    -- 再作成（PG12+: EXECUTE FUNCTION）
    CREATE TRIGGER trg_refresh_gym_freshness_insupd
    AFTER INSERT OR UPDATE ON equipments
    FOR EACH ROW
    EXECUTE FUNCTION trg_refresh_on_equipment_insupd();

    CREATE TRIGGER trg_refresh_gym_freshness_del
    AFTER DELETE ON equipments
    FOR EACH ROW
    EXECUTE FUNCTION trg_refresh_on_equipment_del();

    CREATE TRIGGER trg_refresh_gym_freshness_on_gym
    AFTER UPDATE OF last_verified_at ON gyms
    FOR EACH ROW
    EXECUTE FUNCTION trg_refresh_on_gym_ts();

    CREATE TRIGGER trg_refresh_on_link_ins
    AFTER INSERT ON gym_equipments
    FOR EACH ROW
    EXECUTE FUNCTION trg_refresh_on_link_ins();

    CREATE TRIGGER trg_refresh_on_link_del
    AFTER DELETE ON gym_equipments
    FOR EACH ROW
    EXECUTE FUNCTION trg_refresh_on_link_del();
    """)

    # -- バックフィル（多対多対応）
    op.execute("""
    WITH eq_max AS (
    SELECT ge.gym_id, MAX(e.last_verified_at) AS eq_latest
        FROM gym_equipments ge
        JOIN equipments e ON e.id = ge.equipment_id
    GROUP BY ge.gym_id
    ),
    agg AS (
    SELECT g.id AS gym_id,
            GREATEST(
            COALESCE(g.last_verified_at, '-infinity'::timestamptz),
            COALESCE(eq_max.eq_latest,    '-infinity'::timestamptz)
            ) AS new_cached
        FROM gyms g
        LEFT JOIN eq_max ON eq_max.gym_id = g.id
    )
    UPDATE gyms g
    SET last_verified_at_cached = agg.new_cached
    FROM agg
    WHERE g.id = agg.gym_id;
    """)


def downgrade():
    op.execute("""
    DROP INDEX IF EXISTS idx_gyms_last_verified_at_cached_desc;
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_insupd ON equipments;
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_del ON equipments;
    DROP TRIGGER IF EXISTS trg_refresh_gym_freshness_on_gym ON gyms;
    DROP FUNCTION IF EXISTS REFRESH_GYM_FRESHNESS(BIGINT);
    """)
