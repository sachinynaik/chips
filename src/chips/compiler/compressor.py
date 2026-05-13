from __future__ import annotations

import httpx


class OllamaCompressor:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def compress(
        self,
        hard_constraints: list[str],
        soft_items: list[str],
        task: str,
    ) -> str:
        compressed_soft = self._compress_soft(soft_items, task) if soft_items else ""

        parts: list[str] = []
        if hard_constraints:
            lines = "\n".join(f"- {c}" for c in hard_constraints)
            parts.append(f"## Constraints (non-negotiable)\n{lines}")
        if compressed_soft:
            parts.append(f"## Context\n{compressed_soft}")
        return "\n\n".join(parts)

    def _compress_soft(self, soft_items: list[str], task: str) -> str:
        prompt = self._build_prompt(task, soft_items)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": self._model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception:
            return "\n".join(soft_items)

    def _build_prompt(self, task: str, soft_items: list[str]) -> str:
        items_text = "\n".join(f"- {item}" for item in soft_items)
        return (
            f"Summarize the following engineering context for the task: {task!r}\n\n"
            f"Context items:\n{items_text}\n\n"
            "Output 3-5 bullet points covering only what is most relevant. No preamble."
        )
