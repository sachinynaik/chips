def test_cortex_file_signal_snapshots_table_exists(conn):
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'cortex_file_signal_snapshots'"
    ).fetchone()
    assert row is not None


def test_cortex_file_signal_snapshots_required_columns(conn):
    rows = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_file_signal_snapshots'"
    ).fetchall()
    cols = {r[0] for r in rows}
    required = {
        "basis_sha",
        "file_path",
        "churn_score",
        "cochange_entropy",
        "generated_kind",
        "fragility",
        "fragility_complete",
        "fragility_inputs_present",
        "fragility_inputs_missing",
        "captured_at",
    }
    assert required <= cols, f"Missing columns: {required - cols}"
