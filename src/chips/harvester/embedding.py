from __future__ import annotations

import httpx


class OllamaEmbedder:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def embed(self, text: str) -> list[float]:
        with httpx.Client() as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
            )
            resp.raise_for_status()
        return resp.json()["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client() as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
        return resp.json()["embeddings"]
