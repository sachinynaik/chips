"""Add tenant_id to tables that were missing it.

Revision ID: 003
Revises: 002
Create Date: 2026-05-23
"""
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in (
        "cortex_git_commits",
        "cortex_cochange_pairs",
        "cortex_file_signals",
        "cortex_briefs",
    ):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS tenant_id UUID NULL")
        op.execute(f"CREATE INDEX IF NOT EXISTS {table}_tenant ON {table} (tenant_id)")


def downgrade() -> None:
    for table in (
        "cortex_git_commits",
        "cortex_cochange_pairs",
        "cortex_file_signals",
        "cortex_briefs",
    ):
        op.execute(f"DROP INDEX IF EXISTS {table}_tenant")
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS tenant_id")
