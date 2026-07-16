from __future__ import annotations

import httpx


# A cold Ollama model load pulls ~1GB into memory before the first token; under
# load (e.g. a concurrent harvest backfill) requests also queue behind one
# another (Ollama serialises at NUM_PARALLEL=1). httpx's 5s default timeout is
# far too tight for that and throws an uncaught ReadTimeout that breaks both the
# harvester daemon and brief compile. Default generous; override per call site.
_DEFAULT_EMBED_TIMEOUT_SECONDS = 120.0


class OllamaEmbedder:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout: float = _DEFAULT_EMBED_TIMEOUT_SECONDS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def embed(self, text: str) -> list[float]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
            )
            resp.raise_for_status()
        return resp.json()["embeddings"][0]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            )
            resp.raise_for_status()
        return resp.json()["embeddings"]
