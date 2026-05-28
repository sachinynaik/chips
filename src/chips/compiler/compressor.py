from __future__ import annotations

import math

import httpx

from chips.compiler.models import SoftContextItem

try:
    import tiktoken as _tiktoken
    _TIKTOKEN_AVAILABLE = True
except ImportError:
    _TIKTOKEN_AVAILABLE = False

# cl100k_base (GPT-4 / text-embedding-3) is a good approximation for code-focused
# models including Qwen variants; within ~10-15% of their actual token counts.
_DEFAULT_TIKTOKEN_ENCODING = "cl100k_base"


def _build_token_counter(encoding_name: str):
    """Return a callable (text) -> int using tiktoken, or fall back to char/4."""
    if not _TIKTOKEN_AVAILABLE:
        return lambda text: max(1, math.ceil(len(text) / 4))
    enc = _tiktoken.get_encoding(encoding_name)
    return lambda text: max(1, len(enc.encode(text, disallowed_special=())))


class OllamaCompressor:
    def __init__(
        self,
        base_url: str,
        model: str,
        soft_char_budget: int = 4000,
        soft_token_budget: int | None = None,
        num_predict: int = 200,
        max_items: int = 20,
        tiktoken_encoding: str = _DEFAULT_TIKTOKEN_ENCODING,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._soft_char_budget = soft_char_budget
        self._soft_token_budget = soft_token_budget or max(1, soft_char_budget // 4)
        self._num_predict = num_predict
        self._max_items = max_items
        self._count_tokens = _build_token_counter(tiktoken_encoding)

    def compress(
        self,
        hard_constraints: list[str],
        soft_items: list[str | SoftContextItem],
        task: str,
    ) -> str:
        compressed, _ = self.compress_with_trace(hard_constraints, soft_items, task)
        return compressed

    def compress_with_trace(
        self,
        hard_constraints: list[str],
        soft_items: list[str | SoftContextItem],
        task: str,
    ) -> tuple[str, dict[str, list[str]]]:
        normalized = self._normalize_items(soft_items)
        compressed_soft = self._compress_soft(normalized, task) if normalized else ""

        parts: list[str] = []
        if hard_constraints:
            lines = "\n".join(f"- {c}" for c in hard_constraints)
            parts.append(f"## Constraints (non-negotiable)\n{lines}")
        if compressed_soft:
            parts.append(f"## Context\n{compressed_soft}")

        kept = self._trim_soft_items(normalized)
        kept_ids = [item.item_id for item in kept]
        kept_id_set = set(kept_ids)
        dropped_ids = [
            item.item_id for item in normalized if item.item_id not in kept_id_set
        ]
        return "\n\n".join(parts), {
            "kept_item_ids": kept_ids,
            "dropped_item_ids": dropped_ids,
        }

    def _normalize_items(
        self, items: list[str | SoftContextItem]
    ) -> list[SoftContextItem]:
        normalized: list[SoftContextItem] = []
        for index, item in enumerate(items):
            if isinstance(item, SoftContextItem):
                normalized.append(item)
            else:
                normalized.append(
                    SoftContextItem(
                        item_id=f"generic:{index}",
                        category="generic",
                        text=item,
                        score=float(len(items) - index),
                    )
                )
        return normalized

    def _item_fits(
        self,
        item: SoftContextItem,
        *,
        char_used: int,
        token_used: int,
        item_count: int,
    ) -> bool:
        if item_count >= self._max_items:
            return False
        char_cost = len(item.text) + 4
        token_cost = self._count_tokens(item.text)
        return (
            char_used + char_cost <= self._soft_char_budget
            and token_used + token_cost <= self._soft_token_budget
        )

    def _trim_soft_items(self, items: list[SoftContextItem]) -> list[SoftContextItem]:
        if not items:
            return []

        ordered = sorted(items, key=lambda item: (-item.score, item.item_id))
        char_used = 0
        token_used = 0
        kept: list[SoftContextItem] = []
        seen_ids: set[str] = set()

        category_heads: dict[str, SoftContextItem] = {}
        for item in ordered:
            category_heads.setdefault(item.category, item)

        for item in category_heads.values():
            if self._item_fits(
                item,
                char_used=char_used,
                token_used=token_used,
                item_count=len(kept),
            ):
                kept.append(item)
                seen_ids.add(item.item_id)
                char_used += len(item.text) + 4
                token_used += self._count_tokens(item.text)

        for item in ordered:
            if item.item_id in seen_ids:
                continue
            if not self._item_fits(
                item,
                char_used=char_used,
                token_used=token_used,
                item_count=len(kept),
            ):
                continue
            kept.append(item)
            seen_ids.add(item.item_id)
            char_used += len(item.text) + 4
            token_used += self._count_tokens(item.text)

        return kept if kept else ordered[:1]

    def _trim_to_budget(
        self, items: list[str | SoftContextItem]
    ) -> list[str | SoftContextItem]:
        normalized = self._normalize_items(items)
        kept = self._trim_soft_items(normalized)
        if items and isinstance(items[0], SoftContextItem):
            return kept
        kept_by_id = {item.item_id for item in kept}
        return [
            original
            for index, original in enumerate(items)
            if f"generic:{index}" in kept_by_id
        ]

    def _compress_soft(self, soft_items: list[SoftContextItem], task: str) -> str:
        trimmed = self._trim_soft_items(soft_items)
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
            return "\n".join(item.text for item in trimmed)

    def _build_prompt(self, task: str, soft_items: list[SoftContextItem]) -> str:
        items_text = "\n".join(
            f"- [{item.category}] {item.text}" for item in soft_items
        )
        return (
            f"Summarize the following engineering context for the task: {task!r}\n\n"
            f"Context items:\n{items_text}\n\n"
            "Output 3-5 bullet points covering only what is most relevant. No preamble."
        )
