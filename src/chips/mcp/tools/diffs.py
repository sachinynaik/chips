from __future__ import annotations

import psycopg


def get_diffs_for_scope(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 10,
    tenant_id: str | None = None,
) -> dict:
    from chips.tenant import apply_tenant_clause

    commit_conditions: list[str] = []
    commit_params: list = []

    if scope:
        commit_conditions.append(
            "EXISTS (SELECT 1 FROM unnest(files_changed) AS f WHERE f ILIKE %s)"
        )
        commit_params.append(f"%{scope}%")
    apply_tenant_clause(commit_conditions, commit_params, tenant_id)

    where_clause = f"WHERE {' AND '.join(commit_conditions)}" if commit_conditions else ""
    commit_params.append(limit)

    rows = conn.execute(
        f"""
        SELECT sha, author, committed_at, message, files_changed
        FROM cortex_git_commits
        {where_clause}
        ORDER BY committed_at DESC
        LIMIT %s
        """,  # type: ignore[arg-type]
        tuple(commit_params),
    ).fetchall()

    commits = []
    for sha, author, committed_at, message, files_changed in rows:
        files = list(files_changed) if files_changed else []

        cochange_conditions: list[str] = ["(file_a = ANY(%s) OR file_b = ANY(%s))"]
        cochange_params: list = [files, files]
        apply_tenant_clause(cochange_conditions, cochange_params, tenant_id)

        pairs = conn.execute(
            f"""
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE {' AND '.join(cochange_conditions)}
            ORDER BY frequency DESC
            LIMIT 10
            """,
            tuple(cochange_params),
        ).fetchall()

        commits.append({
            "sha": sha,
            "author": author,
            "committed_at": committed_at.isoformat() if committed_at else None,
            "message": message,
            "files_changed": files,
            "cochange_pairs": [
                {"file_a": a, "file_b": b, "frequency": f}
                for a, b, f in pairs
            ],
        })

    return {
        "scope": scope,
        "commits": commits,
        "status": "ok",
    }
