"""add step_index to run_steps

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-03 14:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("run_steps", sa.Column("step_index", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("run_steps") as batch_op:
        batch_op.drop_column("step_index")
