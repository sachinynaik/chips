"""Add cochange entropy to file signals.

Revision ID: 010
Revises: 009
Create Date: 2026-06-18
"""
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE cortex_file_signals ADD COLUMN IF NOT EXISTS cochange_entropy FLOAT DEFAULT 0"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE cortex_file_signals DROP COLUMN IF EXISTS cochange_entropy"
    )
