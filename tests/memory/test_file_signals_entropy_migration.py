def test_cortex_file_signals_has_cochange_entropy_column(conn):
    row = conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = 'cortex_file_signals' AND column_name = 'cochange_entropy'"
    ).fetchone()
    assert row is not None
