from __future__ import annotations
import psycopg


def get_recent_commits(conn: psycopg.Connection, limit: int = 10) -> list[dict]:
    commits = conn.execute(
        """
        SELECT sha, author, committed_at, message, files_changed
        FROM cortex_git_commits
        ORDER BY committed_at DESC
        LIMIT %s
        """,
        (limit,),
    ).fetchall()

    result = []
    for sha, author, committed_at, message, files_changed in commits:
        pairs = conn.execute(
            """
            SELECT file_a, file_b, frequency
            FROM cortex_cochange_pairs
            WHERE file_a = ANY(%s) OR file_b = ANY(%s)
            ORDER BY frequency DESC
            LIMIT 10
            """,
            (files_changed, files_changed),
        ).fetchall()

        result.append({
            "sha": sha,
            "author": author,
            "committed_at": committed_at.isoformat() if committed_at else None,
            "message": message,
            "files_changed": list(files_changed) if files_changed else [],
            "cochange_pairs": [
                {"file_a": a, "file_b": b, "frequency": f}
                for a, b, f in pairs
            ],
        })

    return result
