from __future__ import annotations
import httpx

class CodeEmbedder:
    def __init__(self, base_url: str, model: str = "nomic-embed-code") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def find_similar_commits(self, diff_content: str, conn, limit: int = 5) -> list[dict]:
        if not diff_content:
            return []
        try:
            embedding = self._embed(diff_content)
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            rows = conn.execute(
                """
                SELECT content, scope, 1 - (embedding <=> %s::vector) AS similarity
                FROM cortex_memories
                WHERE embedding IS NOT NULL AND type = 'lesson'
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (embedding_str, embedding_str, limit),
            ).fetchall()
            return [{"content": r[0], "scope": r[1], "similarity": float(r[2])} for r in rows]
        except Exception:
            return []

    def _embed(self, text: str) -> list[float]:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
            )
            resp.raise_for_status()
        return resp.json()["embeddings"][0]
