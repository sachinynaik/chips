from __future__ import annotations

class ScopeMemoryFetcher:
    def fetch(self, conn, scope: str, limit: int = 5) -> list[dict]:
        if not scope:
            return []
        try:
            rows = conn.execute(
                """
                SELECT content, type, tags
                FROM cortex_memories
                WHERE scope = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (scope, limit),
            ).fetchall()
            return [{"content": r[0], "type": r[1], "tags": r[2] or []} for r in rows]
        except Exception:
            return []
