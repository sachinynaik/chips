"""Add durable review queue for rejected hypothesis constraint candidates.

ConstraintCandidate payloads are not active constraints. They are durable review
artifacts that preserve rejected-hypothesis write-back until a human either
promotes them via add_constraint or dismisses them.

Revision ID: 012
Revises: 011
Create Date: 2026-06-21
"""
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_constraint_candidates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id TEXT,
            scope TEXT,
            claim TEXT NOT NULL,
            mechanism TEXT NOT NULL,
            cited_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
            source_brief_id UUID NOT NULL,
            source_hypothesis_id TEXT NOT NULL,
            proposed_kind TEXT NOT NULL,
            proposed_target JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'pending',
            promoted_constraint_id UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            reviewed_at TIMESTAMPTZ,
            CONSTRAINT cortex_constraint_candidates_kind_chk
                CHECK (proposed_kind IN ('forbidden', 'invariant', 'known_issue')),
            CONSTRAINT cortex_constraint_candidates_status_chk
                CHECK (status IN ('pending', 'promoted', 'dismissed'))
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS cortex_constraint_candidates_source_unique "
        "ON cortex_constraint_candidates (source_brief_id, source_hypothesis_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_constraint_candidates_lookup "
        "ON cortex_constraint_candidates (tenant_id, status, scope, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cortex_constraint_candidates_lookup")
    op.execute("DROP INDEX IF EXISTS cortex_constraint_candidates_source_unique")
    op.execute("DROP TABLE IF EXISTS cortex_constraint_candidates")
