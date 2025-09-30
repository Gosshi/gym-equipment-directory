"""add scraped_pages and gym_candidates tables

Revision ID: 1a3f2c4b5d67
Revises: e1f2a3b4c5d6
Create Date: 2025-09-13 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "1a3f2c4b5d67"
down_revision: str | None = "e1f2a3b4c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

candidate_status_enum = sa.Enum(
    "new",
    "reviewing",
    "approved",
    "rejected",
    name="candidate_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    candidate_status_enum.create(bind, checkfirst=False)

    op.create_table(
        "scraped_pages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("content_hash", sa.CHAR(length=64), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("source_id", "url", name="uq_scraped_pages_source_url"),
    )
    op.create_index(
        "ix_scraped_pages_fetched_at_desc",
        "scraped_pages",
        [sa.text("fetched_at DESC")],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_scraped_pages_content_hash",
        "scraped_pages",
        ["content_hash"],
        postgresql_using="btree",
    )

    op.create_table(
        "gym_candidates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_page_id",
            sa.BigInteger(),
            sa.ForeignKey("scraped_pages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name_raw", sa.Text(), nullable=False),
        sa.Column("address_raw", sa.Text(), nullable=True),
        sa.Column("pref_slug", sa.String(length=64), nullable=True),
        sa.Column("city_slug", sa.String(length=64), nullable=True),
        sa.Column("latitude", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("longitude", postgresql.DOUBLE_PRECISION(), nullable=True),
        sa.Column("parsed_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "status",
            candidate_status_enum,
            nullable=False,
            server_default=sa.text("'new'::candidate_status"),
        ),
        sa.Column(
            "duplicate_of_id",
            sa.BigInteger(),
            sa.ForeignKey("gym_candidates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_gym_candidates_status", "gym_candidates", ["status"], postgresql_using="btree"
    )
    op.create_index(
        "ix_gym_candidates_pref_city",
        "gym_candidates",
        ["pref_slug", "city_slug"],
        postgresql_using="btree",
    )
    op.create_index(
        "ix_gym_candidates_parsed_json",
        "gym_candidates",
        ["parsed_json"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_gym_candidates_parsed_json", table_name="gym_candidates")
    op.drop_index("ix_gym_candidates_pref_city", table_name="gym_candidates")
    op.drop_index("ix_gym_candidates_status", table_name="gym_candidates")
    op.drop_table("gym_candidates")

    op.drop_index("ix_scraped_pages_content_hash", table_name="scraped_pages")
    op.drop_index("ix_scraped_pages_fetched_at_desc", table_name="scraped_pages")
    op.drop_table("scraped_pages")

    candidate_status_enum.drop(op.get_bind(), checkfirst=False)
