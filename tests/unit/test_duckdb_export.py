from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import duckdb

from chips.analytics.duckdb_export import export_brief_history


def test_export_brief_history_writes_rows(tmp_path):
    db_path = tmp_path / f"brief_history_{uuid4().hex}.duckdb"
    rows = [
        {
            "brief_id": "b1",
            "tenant_id": "t1",
            "scope": "checkout",
            "task_kind": "bugfix",
            "generated_at": datetime(2026, 5, 31, tzinfo=timezone.utc),
            "latency_ms": 120,
            "outcome": "accepted",
            "hard_constraints": ["MUST NOT: break checkout"],
            "data_sources": {"runtime": {"status": "available"}},
            "ranked_signals": [{"item_id": "mem:1", "score": 0.9}],
            "compression_trace": {"kept_item_ids": ["mem:1"]},
        },
        {
            "brief_id": "b2",
            "tenant_id": "t1",
            "scope": "auth",
            "task_kind": "analysis",
            "generated_at": datetime(2026, 5, 31, 1, tzinfo=timezone.utc),
            "latency_ms": 95,
            "outcome": "rejected",
        },
    ]

    exported = export_brief_history(rows, db_path)

    assert exported == 2

    conn = duckdb.connect(str(db_path))
    try:
        assert conn.execute("SELECT COUNT(*) FROM brief_history").fetchone()[0] == 2
        assert (
            conn.execute(
                "SELECT hard_constraints FROM brief_history WHERE brief_id = 'b1'"
            ).fetchone()[0]
            == '["MUST NOT: break checkout"]'
        )
    finally:
        conn.close()
        db_path.unlink(missing_ok=True)
