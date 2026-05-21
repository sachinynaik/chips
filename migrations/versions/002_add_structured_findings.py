"""Add structured_findings column to cortex_memories."""
from alembic import op

revision = "002"
down_revision = "001"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE cortex_memories ADD COLUMN IF NOT EXISTS "
        "structured_findings JSONB NOT NULL DEFAULT '{}'"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cortex_memories DROP COLUMN IF EXISTS structured_findings")
