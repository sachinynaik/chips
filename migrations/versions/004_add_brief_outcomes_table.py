"""Add cortex_brief_outcomes table for feedback loop.

Revision ID: 004
Revises: 003
Create Date: 2026-05-26
"""
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cortex_brief_outcomes (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brief_id    UUID NOT NULL,
            tenant_id   UUID NULL,
            outcome     TEXT NOT NULL
                        CHECK (outcome IN ('accepted', 'rejected', 'ignored')),
            note        TEXT NULL,
            created_at  TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS brief_outcomes_brief ON cortex_brief_outcomes (brief_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS brief_outcomes_tenant ON cortex_brief_outcomes (tenant_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cortex_brief_outcomes")
