def test_cortex_issue_refs_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_issue_refs'"
    ).fetchone()
    assert row is not None


def test_cortex_issue_refs_required_columns(conn):
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_issue_refs'"
    ).fetchall()
    cols = {r[0] for r in rows}
    required = {
        "ref",
        "repo",
        "issue_number",
        "tenant_id",
        "state",
        "labels",
        "issue_type",
        "title",
        "closed_at",
        "closed_by_pr",
        "fetched_at",
        "fetch_status",
        "raw",
    }
    assert required <= cols, f"Missing columns: {required - cols}"


def test_cortex_issue_refs_fetch_status_constraint(conn):
    try:
        conn.execute(
            "INSERT INTO cortex_issue_refs (ref, repo, fetch_status) "
            "VALUES ('#1', 'org/repo', 'invalid_status')"
        )
        assert False, "Should have raised constraint violation"
    except Exception as e:
        assert "check" in str(e).lower() or "constraint" in str(e).lower()


def test_cortex_issue_refs_primary_key_is_repo_ref(conn):
    rows = conn.execute(
        """
        SELECT a.attname
        FROM pg_index x
        JOIN pg_class c ON c.oid = x.indrelid
        JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum = ANY(x.indkey)
        WHERE c.relname = 'cortex_issue_refs' AND x.indisprimary
        """
    ).fetchall()
    assert {r[0] for r in rows} == {"repo", "ref"}
