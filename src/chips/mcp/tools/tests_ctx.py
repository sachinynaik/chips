from __future__ import annotations

import psycopg


def get_test_context(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 20,
) -> dict:
    """Return test file signals and co-change pairs, optionally filtered by scope."""
    scope_pattern = f"%{scope}%" if scope else None

    # Query 1: test files sorted by churn (hottest first)
    if scope_pattern:
        file_rows = conn.execute(
            """
            SELECT file_path, churn_score, failure_count
            FROM cortex_file_signals
            WHERE file_path ILIKE '%test%' AND file_path ILIKE %s
            ORDER BY churn_score DESC
            LIMIT %s
            """,
            (scope_pattern, limit),
        ).fetchall()
    else:
        file_rows = conn.execute(
            """
            SELECT file_path, churn_score, failure_count
            FROM cortex_file_signals
            WHERE file_path ILIKE '%test%'
            ORDER BY churn_score DESC
            LIMIT %s
            """,
            (limit,),
        ).fetchall()

    # Query 2: co-change pairs involving test files
    if scope_pattern:
        cochange_rows = conn.execute(
            """
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE (file_a ILIKE '%test%' OR file_b ILIKE '%test%')
              AND (file_a ILIKE %s OR file_b ILIKE %s)
            ORDER BY frequency DESC
            LIMIT 10
            """,
            (scope_pattern, scope_pattern),
        ).fetchall()
    else:
        cochange_rows = conn.execute(
            """
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE file_a ILIKE '%test%' OR file_b ILIKE '%test%'
            ORDER BY frequency DESC
            LIMIT 10
            """,
            (),
        ).fetchall()

    return {
        "test_files": [
            {
                "file_path": file_path,
                "churn_score": churn_score,
                "failure_count": failure_count,
            }
            for file_path, churn_score, failure_count in file_rows
        ],
        "cochange_pairs": [
            {"file_a": a, "file_b": b, "frequency": freq}
            for a, b, freq in cochange_rows
        ],
        "scope": scope,
        "status": "ok",
    }
