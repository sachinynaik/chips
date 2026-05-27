"""Add learning score snapshot table and compression trace to cortex_briefs.

Revision ID: 006
Revises: 005
Create Date: 2026-05-26
"""
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE cortex_briefs ADD COLUMN IF NOT EXISTS compression_trace JSONB DEFAULT '{}'::jsonb"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_memory_feedback_scores (
            memory_id UUID NOT NULL,
            tenant_id TEXT NOT NULL DEFAULT '',
            confidence_adjustment DOUBLE PRECISION NOT NULL,
            accepted_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            ignored_count INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (memory_id, tenant_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cortex_memory_feedback_scores")
    op.execute("ALTER TABLE cortex_briefs DROP COLUMN IF EXISTS compression_trace")
