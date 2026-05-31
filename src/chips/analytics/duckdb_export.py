from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import duckdb

    _DUCKDB_AVAILABLE = True
except ImportError:  # pragma: no cover
    duckdb = None  # type: ignore[assignment]
    _DUCKDB_AVAILABLE = False


def export_brief_history(rows: list[dict[str, Any]], db_path: str | Path) -> int:
    """Export brief-history rows into a local DuckDB table for offline analysis."""
    if not _DUCKDB_AVAILABLE:  # pragma: no cover
        raise RuntimeError("duckdb is not installed")

    conn = duckdb.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brief_history (
                brief_id TEXT,
                tenant_id TEXT,
                scope TEXT,
                task_kind TEXT,
                generated_at TIMESTAMP,
                latency_ms BIGINT,
                outcome TEXT,
                hard_constraints TEXT,
                data_sources TEXT,
                ranked_signals TEXT,
                compression_trace TEXT
            )
            """
        )
        conn.execute("DELETE FROM brief_history")
        for row in rows:
            conn.execute(
                """
                INSERT INTO brief_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("brief_id"),
                    row.get("tenant_id"),
                    row.get("scope"),
                    row.get("task_kind"),
                    row.get("generated_at"),
                    row.get("latency_ms"),
                    row.get("outcome"),
                    json.dumps(row.get("hard_constraints", [])),
                    json.dumps(row.get("data_sources", {})),
                    json.dumps(row.get("ranked_signals", [])),
                    json.dumps(row.get("compression_trace", {})),
                ),
            )
        return len(rows)
    finally:
        conn.close()
