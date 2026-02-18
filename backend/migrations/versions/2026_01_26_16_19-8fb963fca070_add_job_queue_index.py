"""add job queue index

Revision ID: 8fb963fca070
Revises: 04b01022773b
Create Date: 2026-01-26 16:19:10.783219+00:00

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8fb963fca070'
down_revision: str | None = '04b01022773b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index('ix_jobs_status_created_at_id', 'jobs', ['status', 'created_at', 'id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_status_created_at_id', table_name='jobs')
