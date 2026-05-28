"""Add cortex_constraints (dynamic policy layer) and brief audit/RL-readiness columns.

cortex_constraints is the durable anti-regression / policy store injected into
hard_constraints at build time. dedup_hash + a partial unique index on active rows
make manual add idempotent and race-safe. cortex_briefs gains weights_used /
verification_reward (RL-readiness logging — populated by the verifier later; null
until then). hard_constraints already exists on cortex_briefs (migration 001) and is
the audit of which constraints a brief injected.

Revision ID: 007
Revises: 006
Create Date: 2026-05-27
"""
from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_constraints (
            id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id     TEXT,
            scope_pattern TEXT NOT NULL,
            kind          TEXT NOT NULL,
            constraint_text TEXT NOT NULL,
            reason        TEXT,
            source_kind   TEXT,
            source_ref    TEXT,
            target        JSONB NOT NULL DEFAULT '{}'::jsonb,
            status        TEXT NOT NULL DEFAULT 'active',
            superseded_by UUID,
            dedup_hash    TEXT NOT NULL,
            created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT cortex_constraints_kind_chk
                CHECK (kind IN ('forbidden', 'invariant', 'known_issue')),
            CONSTRAINT cortex_constraints_status_chk
                CHECK (status IN ('active', 'superseded', 'expired'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_constraints_lookup "
        "ON cortex_constraints (tenant_id, status, scope_pattern)"
    )
    # Race-safe dedup: only one active row per dedup identity. dedup_hash already
    # folds tenant_id (None -> ''), so a single-column index is tenant-safe and
    # avoids NULLS-DISTINCT concerns. Retiring frees the identity for re-add.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS cortex_constraints_active_dedup "
        "ON cortex_constraints (dedup_hash) WHERE status = 'active'"
    )

    # Brief RL-readiness logging (hard_constraints audit column already exists since 001)
    op.execute(
        "ALTER TABLE cortex_briefs ADD COLUMN IF NOT EXISTS weights_used JSONB DEFAULT '{}'::jsonb"
    )
    op.execute(
        "ALTER TABLE cortex_briefs ADD COLUMN IF NOT EXISTS verification_reward DOUBLE PRECISION"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cortex_briefs DROP COLUMN IF EXISTS verification_reward")
    op.execute("ALTER TABLE cortex_briefs DROP COLUMN IF EXISTS weights_used")
    op.execute("DROP INDEX IF EXISTS cortex_constraints_active_dedup")
    op.execute("DROP INDEX IF EXISTS cortex_constraints_lookup")
    op.execute("DROP TABLE IF EXISTS cortex_constraints")
