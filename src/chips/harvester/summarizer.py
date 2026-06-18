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

        defect_history_count = enrichment.defect_risk.get("history_count", 0)
        if defect_history_count:
            commits = ", ".join(enrichment.defect_risk.get("matched_commits", [])[:3])
            detail = f" ({commits})" if commits else ""
            parts.append(
                f"Prior defect-linked changes in this area: {defect_history_count}{detail}"
            )

        if enrichment.type_errors:
            error_lines = "; ".join(
                f"{e.get('code', '?')} at line {e.get('line', '?')}: {e.get('message', '')}"
                for e in enrichment.type_errors[:5]
            )
            parts.append(f"Type errors ({enrichment.type_checker_backend}): {error_lines}")

        if enrichment.type_coverage:
            low = [
                f"{path.split('/')[-1]} {int(info.get('annotation_completeness', 1.0) * 100)}%"
                for path, info in enrichment.type_coverage.items()
                if info.get("annotation_completeness", 1.0) < 0.5
            ]
            if low:
                parts.append(f"Low annotation coverage: {', '.join(low[:3])}")

        if enrichment.security_findings:
            high = [f for f in enrichment.security_findings if f.get("severity") == "HIGH"]
            sample = high[:3] if high else enrichment.security_findings[:3]
            ids = ", ".join(f"{f.get('test_id','?')} {f.get('message','')[:60]}" for f in sample)
            label = f"HIGH-severity " if high else ""
            parts.append(f"Bandit {label}security findings: {ids}")

        if enrichment.dead_code_findings:
            names = [f"{d.get('type','?')}: {d.get('name','?')}" for d in enrichment.dead_code_findings[:4]]
            parts.append(f"Dead code detected: {', '.join(names)}")

        if enrichment.api_surface_findings:
            missing_ret = [f for f in enrichment.api_surface_findings if f.get("change_type") == "missing_return_annotation"]
            undoc = [f for f in enrichment.api_surface_findings if f.get("change_type") == "undocumented_public_api"]
            notes = []
            if missing_ret:
                notes.append(f"{len(missing_ret)} missing return annotations")
            if undoc:
                notes.append(f"{len(undoc)} undocumented public symbols")
            if notes:
                parts.append(f"API surface issues: {', '.join(notes)}")

        if enrichment.architecture_violations:
            contracts = list({v.get("contract", "?") for v in enrichment.architecture_violations})
            parts.append(f"Architecture violations (import-linter): {', '.join(contracts[:3])}")

        if enrichment.clone_findings:
            parts.append(
                f"Code clones detected: {len(enrichment.clone_findings)} duplicate block(s) "
                f"(largest: {max(c.get('lines', 0) for c in enrichment.clone_findings)} lines)"
            )

        if enrichment.ownership:
            all_owners = enrichment.ownership.get("all_owners", [])
            cross = enrichment.ownership.get("cross_team_change", False)
            if all_owners:
                parts.append(
                    f"CODEOWNERS: {', '.join(all_owners[:5])}"
                    + (" [cross-team change]" if cross else "")
                )

        if enrichment.line_coverage:
            files_info = enrichment.line_coverage.get("files", {})
            uncovered = [
                p.split("/")[-1]
                for p, info in files_info.items()
                if info.get("changed_lines_coverage_pct") is not None
                and info.get("changed_lines_coverage_pct", 100.0) == 0.0
            ]
            if uncovered:
                parts.append(f"Changed lines with no test coverage: {', '.join(uncovered[:4])}")

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
