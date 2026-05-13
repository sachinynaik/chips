"""Initial CHIPS CORTEX schema.

Revision ID: 001
Revises:
Create Date: 2026-05-12
"""
from alembic import op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("""
        CREATE TABLE cortex_memories (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id       UUID NULL,
            type            TEXT NOT NULL
                            CHECK (type IN ('invariant','decision','pitfall','contract','lesson')),
            scope           TEXT NOT NULL,
            content         TEXT NOT NULL,
            tags            TEXT[]      DEFAULT '{}',
            evidence_refs   JSONB       DEFAULT '[]',
            confidence      FLOAT       DEFAULT 0.8
                            CHECK (confidence BETWEEN 0 AND 1),
            source          TEXT,
            author          TEXT,
            created_at      TIMESTAMPTZ DEFAULT now(),
            updated_at      TIMESTAMPTZ DEFAULT now(),
            archived_at     TIMESTAMPTZ NULL,
            embedding       vector(768)
        )
    """)

    op.execute("""
        CREATE INDEX cortex_memories_hnsw
            ON cortex_memories
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
    """)

    op.execute("CREATE INDEX cortex_memories_scope ON cortex_memories (scope)")
    op.execute("CREATE INDEX cortex_memories_type  ON cortex_memories (type)")
    op.execute("CREATE INDEX cortex_memories_tags  ON cortex_memories USING gin (tags)")

    op.execute("""
        CREATE TABLE cortex_git_commits (
            sha             TEXT PRIMARY KEY,
            author          TEXT,
            committed_at    TIMESTAMPTZ,
            message         TEXT,
            files_changed   TEXT[]      DEFAULT '{}',
            summary         TEXT,
            ingested_at     TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE cortex_cochange_pairs (
            file_a          TEXT NOT NULL,
            file_b          TEXT NOT NULL,
            frequency       INT  NOT NULL DEFAULT 1,
            last_seen_at    TIMESTAMPTZ   DEFAULT now(),
            PRIMARY KEY (file_a, file_b)
        )
    """)

    op.execute("""
        CREATE TABLE cortex_file_signals (
            file_path       TEXT PRIMARY KEY,
            churn_score     FLOAT DEFAULT 0,
            failure_count   INT   DEFAULT 0,
            last_changed_at TIMESTAMPTZ,
            updated_at      TIMESTAMPTZ DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE cortex_briefs (
            brief_id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            task                    TEXT NOT NULL,
            scope                   TEXT,
            generated_at            TIMESTAMPTZ DEFAULT now(),
            latency_ms              INT,
            mode                    TEXT CHECK (mode IN ('interactive','background','autocomplete')),
            compiler_inputs         JSONB,
            retrieved_memories      JSONB DEFAULT '[]',
            retrieved_files         JSONB DEFAULT '[]',
            retrieved_symbols       JSONB DEFAULT '[]',
            retrieved_traces        JSONB DEFAULT '[]',
            retrieved_tests         JSONB DEFAULT '[]',
            retrieved_diffs         JSONB DEFAULT '[]',
            compressed_context      TEXT,
            hard_constraints        JSONB DEFAULT '[]',
            soft_context            TEXT,
            agent_edited_files      TEXT[]  DEFAULT '{}',
            retrieval_overlap_score FLOAT,
            test_outcome            TEXT CHECK (
                                        test_outcome IN ('pass','fail','unknown','skipped')
                                    ),
            post_task_outcome       TEXT,
            outcome_recorded_at     TIMESTAMPTZ
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS cortex_briefs")
    op.execute("DROP TABLE IF EXISTS cortex_file_signals")
    op.execute("DROP TABLE IF EXISTS cortex_cochange_pairs")
    op.execute("DROP TABLE IF EXISTS cortex_git_commits")
    op.execute("DROP TABLE IF EXISTS cortex_memories")
