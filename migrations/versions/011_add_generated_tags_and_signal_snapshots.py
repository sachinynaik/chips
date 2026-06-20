"""add generated tags and file signal snapshots

Revision ID: 011
Revises: 010_add_cochange_entropy_to_file_signals
Create Date: 2026-06-20
"""

from __future__ import annotations

from alembic import op


revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE cortex_file_signals
        ADD COLUMN IF NOT EXISTS generated_kind TEXT
        CHECK (generated_kind IN ('generated', 'scaffolded') OR generated_kind IS NULL)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS cortex_file_signal_snapshots (
            basis_sha                TEXT REFERENCES cortex_git_commits(sha) ON DELETE SET NULL,
            file_path                TEXT NOT NULL,
            churn_score              FLOAT DEFAULT 0,
            cochange_entropy         FLOAT DEFAULT 0,
            generated_kind           TEXT
                                      CHECK (generated_kind IN ('generated', 'scaffolded') OR generated_kind IS NULL),
            fragility                FLOAT DEFAULT 0,
            fragility_complete       BOOLEAN NOT NULL DEFAULT FALSE,
            fragility_inputs_present TEXT[] NOT NULL DEFAULT '{}',
            fragility_inputs_missing TEXT[] NOT NULL DEFAULT '{}',
            captured_at              TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS cortex_file_signal_snapshots_file_path_captured_at
        ON cortex_file_signal_snapshots (file_path, captured_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS cortex_file_signal_snapshots_file_path_captured_at")
    op.execute("DROP TABLE IF EXISTS cortex_file_signal_snapshots")
    op.execute("ALTER TABLE cortex_file_signals DROP COLUMN IF EXISTS generated_kind")
