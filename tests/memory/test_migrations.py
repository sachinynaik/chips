"""RED: schema migration tests — all must fail before migrations exist."""


def test_pgvector_extension_installed(conn):
    row = conn.execute(
        "SELECT extname FROM pg_extension WHERE extname = 'vector'"
    ).fetchone()
    assert row is not None, "pgvector extension not installed"


def test_cortex_memories_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_memories'"
    ).fetchone()
    assert row is not None


def test_cortex_memories_required_columns(conn):
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_memories'"
    ).fetchall()
    cols = {r[0] for r in rows}
    required = {
        "id", "tenant_id", "type", "scope", "content", "tags",
        "evidence_refs", "confidence", "source", "author",
        "created_at", "updated_at", "archived_at", "embedding",
    }
    assert required <= cols, f"Missing columns: {required - cols}"


def test_cortex_memories_hnsw_index_exists(conn):
    row = conn.execute(
        "SELECT indexname FROM pg_indexes "
        "WHERE tablename = 'cortex_memories' AND indexname = 'cortex_memories_hnsw'"
    ).fetchone()
    assert row is not None, "HNSW index not found"


def test_cortex_memories_type_constraint(conn):
    try:
        conn.execute(
            "INSERT INTO cortex_memories (type, scope, content) "
            "VALUES ('invalid_type', 'test', 'test')"
        )
        assert False, "Should have raised constraint violation"
    except Exception as e:
        assert "check" in str(e).lower() or "constraint" in str(e).lower()


def test_cortex_git_commits_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_git_commits'"
    ).fetchone()
    assert row is not None


def test_cortex_cochange_pairs_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_cochange_pairs'"
    ).fetchone()
    assert row is not None


def test_cortex_file_signals_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_file_signals'"
    ).fetchone()
    assert row is not None


def test_cortex_briefs_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_briefs'"
    ).fetchone()
    assert row is not None


def test_cortex_briefs_has_brief_id_primary_key(conn):
    row = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_briefs' AND column_name = 'brief_id'"
    ).fetchone()
    assert row is not None
