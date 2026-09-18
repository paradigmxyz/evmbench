"""Persist the user-selected reasoning effort for each job."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = 'a17c42d89e30'
down_revision: str | None = '8fb963fca070'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('reasoning_effort', sa.String(16), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'reasoning_effort')
