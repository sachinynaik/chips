from __future__ import annotations

from chips.harvester.defect_corpus import estimate_defect_density, high_precision_defect_sql


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

        predicate = high_precision_defect_sql("d")
        history_count = conn.execute(
            f"""
            SELECT COUNT(DISTINCT g.sha)
            FROM cortex_git_commits g
            JOIN cortex_defect_corpus d ON d.sha = g.sha
            WHERE g.files_changed && %s
              AND {predicate}
            """,
            (files_changed,),
        ).fetchone()[0]
        if history_count == 0:
            return {
                **base,
                "reason": "no_prior_defects",
                "defect_density": None,
                "density_basis_nloc": 0,
            }

        rows = conn.execute(
            """
            SELECT DISTINCT g.sha
            FROM cortex_git_commits g
            JOIN cortex_defect_corpus d ON d.sha = g.sha
            WHERE g.files_changed && %s
              AND """ + predicate + """
            ORDER BY g.sha DESC
            LIMIT %s
            """,
            (files_changed, limit),
        ).fetchall()
        matched_commits = [row[0] for row in rows]
        density, basis_nloc = estimate_defect_density(files_changed, defect_count=history_count)
        return {
            **base,
            "reason": "history_found",
            "history_count": history_count,
            "matched_commits": matched_commits,
            "defect_density": density,
            "density_basis_nloc": basis_nloc,
        }
