from __future__ import annotations

import httpx


class OllamaCompressor:
    def __init__(
        self,
        base_url: str,
        model: str,
        soft_char_budget: int = 4000,
        num_predict: int = 200,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._soft_char_budget = soft_char_budget
        self._num_predict = num_predict

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

    def _trim_to_budget(self, items: list[str]) -> list[str]:
        """Keep leading items (assumed pre-sorted by score) until char budget is used."""
        result = []
        used = 0
        for item in items:
            cost = len(item) + 4  # +4 for "- \n" formatting overhead
            if used + cost > self._soft_char_budget:
                break
            result.append(item)
            used += cost
        return result if result else items[:1]

    def _compress_soft(self, soft_items: list[str], task: str) -> str:
        trimmed = self._trim_to_budget(soft_items)
        prompt = self._build_prompt(task, trimmed)
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "num_predict": self._num_predict,
                    },
                )
                resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception:
            return "\n".join(trimmed)

    def _build_prompt(self, task: str, soft_items: list[str]) -> str:
        items_text = "\n".join(f"- {item}" for item in soft_items)
        return (
            f"Summarize the following engineering context for the task: {task!r}\n\n"
            f"Context items:\n{items_text}\n\n"
            "Output 3-5 bullet points covering only what is most relevant. No preamble."
        )
