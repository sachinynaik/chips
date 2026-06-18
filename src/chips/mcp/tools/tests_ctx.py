from __future__ import annotations

import psycopg

from chips.compiler.retrieval import _fragility_score


def get_test_context(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 20,
    tenant_id: str | None = None,
) -> dict:
    """Return test file signals and co-change pairs, optionally filtered by scope and tenant."""
    scope_pattern = f"%{scope}%" if scope else None

    file_conditions = ["file_path ILIKE '%test%'"]
    file_params: list = []
    if scope_pattern:
        file_conditions.append("file_path ILIKE %s")
        file_params.append(scope_pattern)
    if tenant_id is not None:
        file_conditions.append("tenant_id = %s")
        file_params.append(tenant_id)
    file_params.append(limit)

    file_rows = conn.execute(
        f"""
        SELECT
            file_path,
            churn_score,
            cochange_entropy,
            (
                SELECT COUNT(DISTINCT g.sha)
                FROM cortex_git_commits g
                JOIN cortex_defect_corpus d ON d.sha = g.sha
                WHERE g.files_changed && ARRAY[cortex_file_signals.file_path]
                  AND (
                    cardinality(d.issue_refs) > 0
                    OR d.revert_of_sha IS NOT NULL
                    OR d.has_hotfix_keyword = TRUE
                    OR d.has_incident_keyword = TRUE
                  )
            ) AS defect_history_count,
            failure_count
        FROM cortex_file_signals
        WHERE {' AND '.join(file_conditions)}
        ORDER BY churn_score DESC
        LIMIT %s
        """,  # type: ignore[arg-type]
        tuple(file_params),
    ).fetchall()

    cochange_conditions = ["(file_a ILIKE '%test%' OR file_b ILIKE '%test%')"]
    cochange_params: list = []
    if scope_pattern:
        cochange_conditions.append("(file_a ILIKE %s OR file_b ILIKE %s)")
        cochange_params.extend([scope_pattern, scope_pattern])
    if tenant_id is not None:
        cochange_conditions.append("tenant_id = %s")
        cochange_params.append(tenant_id)

    cochange_rows = conn.execute(
        f"""
        SELECT file_a, file_b, frequency
        FROM cortex_cochange_pairs
        WHERE {' AND '.join(cochange_conditions)}
        ORDER BY frequency DESC
        LIMIT 10
        """,  # type: ignore[arg-type]
        tuple(cochange_params),
    ).fetchall()

    return {
        "test_files": [
            {
                "file_path": file_path,
                "churn_score": churn_score,
                "cochange_entropy": cochange_entropy,
                "defect_history_count": defect_history_count,
                "fragility": _fragility_score(churn_score, cochange_entropy, defect_history_count),
                "failure_count": failure_count,
            }
            for file_path, churn_score, cochange_entropy, defect_history_count, failure_count in file_rows
        ],
        "cochange_pairs": [
            {"file_a": a, "file_b": b, "frequency": freq}
            for a, b, freq in cochange_rows
        ],
        "scope": scope,
        "status": "ok",
    }
