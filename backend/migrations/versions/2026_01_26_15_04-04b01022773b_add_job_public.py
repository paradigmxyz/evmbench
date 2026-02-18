"""add job_public

Revision ID: 04b01022773b
Revises: 2a46da4c84ea
Create Date: 2026-01-26 15:04:06.896595+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '04b01022773b'
down_revision: str | None = '2a46da4c84ea'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('public', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    op.drop_column('jobs', 'public')
