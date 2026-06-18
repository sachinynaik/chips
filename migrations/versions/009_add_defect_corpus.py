"""Add raw defect corpus capture table.

Revision ID: 009
Revises: 008
Create Date: 2026-06-18
"""
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS cortex_defect_corpus (
            sha                  TEXT PRIMARY KEY REFERENCES cortex_git_commits(sha) ON DELETE CASCADE,
            tenant_id            UUID NULL,
            issue_refs           TEXT[]      DEFAULT '{}',
            revert_of_sha        TEXT,
            has_bug_keyword      BOOLEAN NOT NULL DEFAULT FALSE,
            has_defect_keyword   BOOLEAN NOT NULL DEFAULT FALSE,
            has_hotfix_keyword   BOOLEAN NOT NULL DEFAULT FALSE,
            has_incident_keyword BOOLEAN NOT NULL DEFAULT FALSE,
            captured_at          TIMESTAMPTZ DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_defect_corpus_tenant ON cortex_defect_corpus (tenant_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS cortex_defect_corpus_issue_refs ON cortex_defect_corpus USING gin (issue_refs)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cortex_defect_corpus_issue_refs")
    op.execute("DROP INDEX IF EXISTS cortex_defect_corpus_tenant")
    op.execute("DROP TABLE IF EXISTS cortex_defect_corpus")
