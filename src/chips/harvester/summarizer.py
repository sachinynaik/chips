from __future__ import annotations

import httpx

from chips.harvester.enrichment.models import EnrichmentResult
from chips.harvester.git_reader import CommitRecord


class DiffSummarizer:
    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    def summarize(self, commit: CommitRecord, enrichment: EnrichmentResult) -> str:
        prompt = self._build_prompt(commit, enrichment)
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(
                    f"{self._base_url}/api/generate",
                    json={"model": self._model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
            return resp.json()["response"].strip()
        except Exception:
            return commit.message

    def _build_prompt(self, commit: CommitRecord, enrichment: EnrichmentResult) -> str:
        parts = [
            f"Commit: {commit.message}",
            f"Author: {commit.author}",
            f"Files: {', '.join(commit.files_changed[:5])}",
        ]

        if enrichment.hunk_headers:
            parts.append(f"Changed functions: {', '.join(enrichment.hunk_headers[:5])}")

        if enrichment.complexity_metrics:
            high = [m for m in enrichment.complexity_metrics if m.get("cyclomatic_complexity", 0) > 10]
            if high:
                names = [m["function"] for m in high[:3]]
                parts.append(f"High complexity functions: {', '.join(names)}")

        if enrichment.semgrep_findings:
            rules = list({f.get("check_id", "unknown") for f in enrichment.semgrep_findings})[:3]
            parts.append(f"Anti-patterns flagged: {', '.join(rules)}")

        if enrichment.related_symbols:
            related = [s["related"] for s in enrichment.related_symbols[:5]]
            parts.append(f"Related symbols: {', '.join(related)}")

        if enrichment.community_context:
            parts.append(f"Module graph context: {enrichment.community_context[:400]}")

        if enrichment.scope_memories:
            memories_text = "\n".join(f"- {m['content']}" for m in enrichment.scope_memories[:3])
            parts.append(f"Existing knowledge about this scope:\n{memories_text}")

        if enrichment.cochange_pairs:
            pairs_text = ", ".join(
                f"{p['file_a'].split('/')[-1]}↔{p['file_b'].split('/')[-1]}"
                for p in enrichment.cochange_pairs[:3]
            )
            parts.append(f"Files that frequently change together: {pairs_text}")

        if enrichment.diff_content:
            parts.append(f"Diff (truncated):\n{enrichment.diff_content[:2000]}")

        context = "\n\n".join(parts)

        return (
            "Extract a precise engineering lesson from this git commit. "
            "Focus on: what changed, why it matters, what other engineers should know "
            "about this module going forward.\n\n"
            f"{context}\n\n"
            "Output a single concise lesson (2-4 sentences). No preamble, no bullet points."
        )
