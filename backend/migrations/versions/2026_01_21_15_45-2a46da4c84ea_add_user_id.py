"""add user_id

Revision ID: 2a46da4c84ea
Revises: d29c31a0ef97
Create Date: 2026-01-21 15:45:50.389071+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '2a46da4c84ea'
down_revision: str | None = 'd29c31a0ef97'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('user_id', sa.String(length=128), nullable=False))


def downgrade() -> None:
    op.drop_column('jobs', 'user_id')
