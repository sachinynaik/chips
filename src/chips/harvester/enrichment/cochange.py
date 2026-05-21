from __future__ import annotations

class CochangeFetcher:
    def fetch(self, conn, files: list[str], limit: int = 10) -> list[dict]:
        if not files:
            return []
        try:
            rows = conn.execute(
                """
                SELECT file_a, file_b, frequency
                FROM cortex_cochange_pairs
                WHERE file_a = ANY(%s) OR file_b = ANY(%s)
                ORDER BY frequency DESC
                LIMIT %s
                """,
                (files, files, limit),
            ).fetchall()
            return [{"file_a": r[0], "file_b": r[1], "frequency": r[2]} for r in rows]
        except Exception:
            return []
