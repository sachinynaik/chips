"""Add attribution columns to cortex_briefs and idempotency to cortex_brief_outcomes.

Attribution columns (data_sources, ranked_signals) let the learning loop reconstruct
retrieval context and source availability without re-running the brief.

idempotency_key on cortex_brief_outcomes makes feedback recording safe to retry.
A partial unique index ensures duplicate (brief_id, idempotency_key) pairs are rejected
while still allowing multiple un-keyed rows.

Revision ID: 005
Revises: 004
Create Date: 2026-05-26
"""
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Attribution: source availability states at build time
    op.execute(
        "ALTER TABLE cortex_briefs ADD COLUMN IF NOT EXISTS data_sources JSONB DEFAULT '{}'::jsonb"
    )
    # Attribution: ranked signal scores for learning loop
    op.execute(
        "ALTER TABLE cortex_briefs ADD COLUMN IF NOT EXISTS ranked_signals JSONB DEFAULT '[]'::jsonb"
    )

    # Feedback idempotency: nullable key; non-null keys must be unique per brief
    op.execute(
        "ALTER TABLE cortex_brief_outcomes ADD COLUMN IF NOT EXISTS idempotency_key TEXT NULL"
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS brief_outcomes_idempotency
            ON cortex_brief_outcomes (brief_id, idempotency_key)
            WHERE idempotency_key IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS brief_outcomes_idempotency")
    op.execute(
        "ALTER TABLE cortex_brief_outcomes DROP COLUMN IF EXISTS idempotency_key"
    )
    op.execute("ALTER TABLE cortex_briefs DROP COLUMN IF EXISTS ranked_signals")
    op.execute("ALTER TABLE cortex_briefs DROP COLUMN IF EXISTS data_sources")
