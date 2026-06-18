from __future__ import annotations


class DefectPredictor:
    """Fetch prior evidence-backed defect history for touched files."""

    def predict(
        self,
        diff_content: str,
        commit_message: str,
        *,
        conn=None,
        files_changed: list[str] | None = None,
        limit: int = 5,
    ) -> dict:
        base = {
            "risk_score": None,
            "history_count": 0,
            "matched_commits": [],
        }
        if conn is None or not files_changed:
            return {**base, "reason": "insufficient_history"}

        rows = conn.execute(
            """
            SELECT DISTINCT g.sha
            FROM cortex_git_commits g
            JOIN cortex_defect_corpus d ON d.sha = g.sha
            WHERE g.files_changed && %s
              AND (
                cardinality(d.issue_refs) > 0
                OR d.revert_of_sha IS NOT NULL
                OR d.has_hotfix_keyword = TRUE
                OR d.has_incident_keyword = TRUE
              )
            ORDER BY g.sha DESC
            LIMIT %s
            """,
            (files_changed, limit),
        ).fetchall()
        matched_commits = [row[0] for row in rows]
        if not matched_commits:
            return {**base, "reason": "no_prior_defects"}
        return {
            **base,
            "reason": "history_found",
            "history_count": len(matched_commits),
            "matched_commits": matched_commits,
        }
