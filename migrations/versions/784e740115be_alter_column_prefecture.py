"""alter column prefecture

Revision ID: 784e740115be
Revises: 3b6b1231bf9a
Create Date: 2025-09-06 10:35:26.087635

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '784e740115be'
down_revision: Union[str, None] = '3b6b1231bf9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # 既存: gyms.prefecture -> gyms.pref
    with op.batch_alter_table("gyms") as b:
        b.alter_column("prefecture", new_column_name="pref")

def downgrade():
    with op.batch_alter_table("gyms") as b:
        b.alter_column("pref", new_column_name="prefecture")
