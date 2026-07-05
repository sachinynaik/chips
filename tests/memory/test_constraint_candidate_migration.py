def test_cortex_constraint_candidates_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_constraint_candidates'"
    ).fetchone()
    assert row is not None


def test_cortex_constraint_candidates_required_columns(conn):
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_constraint_candidates'"
    ).fetchall()
    cols = {r[0] for r in rows}
    required = {
        "id",
        "tenant_id",
        "scope",
        "claim",
        "mechanism",
        "cited_evidence",
        "source_brief_id",
        "source_hypothesis_id",
        "proposed_kind",
        "proposed_target",
        "status",
        "promoted_constraint_id",
        "created_at",
        "reviewed_at",
    }
    assert required <= cols, f"Missing columns: {required - cols}"
