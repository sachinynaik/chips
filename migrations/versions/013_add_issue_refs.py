"""Add issue-metadata capture table for defect-label verification.

Raw capture only (files-are-truth: local copy of the API payload). The defect
label remains a query joining cortex_defect_corpus x cortex_issue_refs — tiers
are computed at query time, never stored. See
docs/design_docs/05_07/chips-defect-corpus-harvest-spec.md (Gap B).

Revision ID: 013
Revises: 012
Create Date: 2026-07-05
"""
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cortex_issue_refs (
            ref             TEXT NOT NULL,
            repo            TEXT NOT NULL,
            issue_number    INT,
            tenant_id       UUID NULL,
            state           TEXT,
            labels          TEXT[]      DEFAULT '{}',
            issue_type      TEXT,
            title           TEXT,
            closed_at       TIMESTAMPTZ,
            closed_by_pr    INT,
            fetched_at      TIMESTAMPTZ DEFAULT now(),
            fetch_status    TEXT NOT NULL
                CHECK (fetch_status IN ('ok','not_found','rate_limited','failed','skipped')),
            raw             JSONB,
            PRIMARY KEY (repo, ref)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_issue_refs_status ON cortex_issue_refs (fetch_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_issue_refs_labels ON cortex_issue_refs USING gin (labels)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cortex_issue_refs_labels")
    op.execute("DROP INDEX IF EXISTS cortex_issue_refs_status")
    op.execute("DROP TABLE IF EXISTS cortex_issue_refs")
