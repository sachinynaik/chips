def test_cortex_defect_corpus_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_defect_corpus'"
    ).fetchone()
    assert row is not None


def test_cortex_defect_corpus_required_columns(conn):
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_defect_corpus'"
    ).fetchall()
    cols = {r[0] for r in rows}
    required = {
        "sha",
        "tenant_id",
        "issue_refs",
        "revert_of_sha",
        "has_bug_keyword",
        "has_defect_keyword",
        "has_hotfix_keyword",
        "has_incident_keyword",
        "captured_at",
    }
    assert required <= cols, f"Missing columns: {required - cols}"
