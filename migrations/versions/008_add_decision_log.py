"""Add cortex_decision_log (Foundation: the bandit/learning decision+reward log).

One row per brief decision. FOUNDATION scope only: context features, action,
propensity, policy_version (a content hash), evidence used, latency, and a
versioned feature schema. The reward-consuming columns (feedback,
verifier_outcome, downstream_success, composite_reward) exist but stay NULL —
they are populated only in the Activation phase, once the Phase-3 verifier
emits validated reward labels. See docs/02_06_contextual_bandit_design.md,
governed by docs/02_06_execution_ledger.md.

Revision ID: 008
Revises: 007
Create Date: 2026-06-02
"""
from alembic import op

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_decision_log (
            id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            brief_id               UUID NOT NULL,
            tenant_id              TEXT,
            scope                  TEXT,
            feature_schema_version TEXT NOT NULL,
            context_features       JSONB NOT NULL DEFAULT '{}'::jsonb,
            action                 JSONB NOT NULL DEFAULT '{}'::jsonb,
            propensity             DOUBLE PRECISION,
            policy_version         TEXT NOT NULL,
            evidence_used          JSONB NOT NULL DEFAULT '[]'::jsonb,
            latency_ms             INTEGER,
            feedback               JSONB,
            verifier_outcome       JSONB,
            downstream_success     JSONB,
            composite_reward       DOUBLE PRECISION,
            created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_decision_log_lookup "
        "ON cortex_decision_log (tenant_id, scope, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_decision_log_brief "
        "ON cortex_decision_log (brief_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cortex_decision_log_brief")
    op.execute("DROP INDEX IF EXISTS cortex_decision_log_lookup")
    op.execute("DROP TABLE IF EXISTS cortex_decision_log")
