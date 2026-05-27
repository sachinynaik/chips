from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone

import psycopg

from chips.compiler.classifier import classify_task
from chips.compiler.compressor import OllamaCompressor
from chips.compiler.learning import BriefLearningService
from chips.compiler.models import ContextBrief, RetrievedItems, SoftContextItem, SourceStatus
from chips.compiler.policy import PolicyLoader
from chips.compiler.ranker import rank_signals
from chips.compiler.retrieval import retrieve_diffs, retrieve_file_signals, retrieve_memories
from chips.harvester.embedding import OllamaEmbedder
from chips.mcp.tools.runtime import probe_runtime
from chips.mcp.tools.workflow import probe_workflow

logger = logging.getLogger(__name__)


def _extract_brief_signals(
    memories: list[dict],
) -> tuple[list[str], list[str]]:
    """Extract hard_additions and soft_additions from structured_findings in memories.

    hard_additions: HIGH/MEDIUM security findings, architecture violations.
    soft_additions: dead code, API surface issues, clones, type errors,
                    uncovered changes, LOW security findings.

    structured_findings schema (produced by chips.harvester.findings.extract_findings):
      security: list[dict]  — sorted by severity desc
      dead_code: list[dict]
      api_surface: list[dict]
      architecture_violations: list[dict]
      clones: list[dict]
      type_errors: list[dict]
      semgrep: list[dict]
      ownership: dict
      uncovered_changes: dict[path, {changed_lines_missing, changed_lines_coverage_pct}]
    """
    hard_additions: list[str] = []
    soft_additions: list[str] = []

    for memory in memories:
        findings = memory.get("structured_findings", {}) or {}

        # Security findings: HIGH/MEDIUM → hard, LOW → soft
        for item in findings.get("security", []):
            severity = (item.get("severity") or "").upper()
            test_id = item.get("test_id", "")
            message = item.get("message", "")
            line = item.get("line", "?")
            file_ = item.get("file", "")
            formatted = f"Security [{test_id}] {message} (line {line}, file {file_})"
            if severity in ("HIGH", "MEDIUM"):
                hard_additions.append(formatted)
            else:
                soft_additions.append(formatted)

        # Architecture violations → hard
        for item in findings.get("architecture_violations", []):
            contract = item.get("contract", "")
            message = item.get("message", "")
            hard_additions.append(f"Architecture violation [{contract}]: {message}")

        # Dead code → soft
        for item in findings.get("dead_code", []):
            kind = item.get("type", "")
            name = item.get("name", "")
            file_ = item.get("file", "")
            confidence = item.get("confidence", "?")
            soft_additions.append(
                f"Dead code: {kind} '{name}' in {file_} (confidence {confidence}%)"
            )

        # API surface → soft
        for item in findings.get("api_surface", []):
            change_type = item.get("change_type", "")
            symbol = item.get("symbol", "")
            details = item.get("details", "")
            soft_additions.append(f"API issue [{change_type}]: {symbol} — {details}")

        # Clones → soft
        for item in findings.get("clones", []):
            lines = item.get("lines", "?")
            file_a = item.get("file_a", "")
            file_b = item.get("file_b", "")
            soft_additions.append(
                f"Code clone: {lines} lines duplicated between {file_a} and {file_b}"
            )

        # Type errors → soft
        for item in findings.get("type_errors", []):
            code = item.get("code", "")
            line = item.get("line", "?")
            message = item.get("message", "")
            soft_additions.append(f"Type error [{code}] line {line}: {message}")

        # Uncovered changes: dict[path → info] → soft
        for path, info in findings.get("uncovered_changes", {}).items():
            basename = os.path.basename(path)
            missing = info.get("changed_lines_missing", "?")
            soft_additions.append(
                f"Uncovered changes in {basename}: {missing} changed lines have no tests"
            )

    return hard_additions, soft_additions


class BriefBuilder:
    def __init__(
        self,
        conn: psycopg.Connection,
        embedder: OllamaEmbedder,
        compressor: OllamaCompressor,
        policy_loader: PolicyLoader | None = None,
    ) -> None:
        self._conn = conn
        self._embedder = embedder
        self._compressor = compressor
        self._policy_loader = policy_loader

    def build(
        self,
        task: str,
        scope: str | None = None,
        files: list[str] | None = None,
        tenant_id: str | None = None,
    ) -> ContextBrief:
        from chips.tenant import require_tenant
        require_tenant(tenant_id)

        start = time.monotonic()

        task_kind = classify_task(task)
        embedding = self._embedder.embed(task)
        learning = BriefLearningService(self._conn)
        adjustments = learning.load_adjustments(tenant_id=tenant_id)

        memories = retrieve_memories(self._conn, embedding, scope=scope, tenant_id=tenant_id)
        for memory in memories:
            adjustment = adjustments.get(str(memory.get("id", "")), 0.0)
            memory["learning_adjustment"] = adjustment
            memory["confidence"] = min(
                max(float(memory.get("confidence") or 0.0) + adjustment, 0.0), 1.0
            )

        effective_files = files if files else []
        file_signals = retrieve_file_signals(
            self._conn, effective_files, tenant_id=tenant_id
        )
        if not effective_files:
            file_signals_status = SourceStatus(
                status="not_configured", detail="no files provided to build()"
            )
        elif file_signals:
            file_signals_status = SourceStatus(status="available")
        else:
            file_signals_status = SourceStatus(status="unavailable")

        diffs = retrieve_diffs(self._conn, scope=scope, tenant_id=tenant_id)

        runtime_status = probe_runtime()
        if runtime_status.status == "error":
            logger.warning("runtime source probe failed: %s", runtime_status.detail)

        workflow_status = probe_workflow()
        if workflow_status.status == "error":
            logger.warning("workflow source probe failed: %s", workflow_status.detail)

        ranked = rank_signals(memories, file_signals, diffs=diffs)

        # Collect policy forbidden/required items
        forbidden_edits: list[str] = []
        allowed_edits: list[str] = []
        if self._policy_loader is not None:
            for policy in self._policy_loader.for_scope(scope):
                forbidden_edits.extend(policy.forbidden)
                allowed_edits.extend(policy.required)

        # Hard constraints = memory invariants/contracts + policy forbidden items
        memory_constraints = [
            m["content"] for m in memories
            if m.get("type") in ("invariant", "contract")
        ]
        hard_additions, soft_additions = _extract_brief_signals(memories)
        hard_constraints = memory_constraints + forbidden_edits + hard_additions

        # Build scored soft items then sort by relevance before compression.
        score_by_id: dict[str, float] = {s.item_id: s.score for s in ranked}
        soft_items: list[SoftContextItem] = []
        for m in memories:
            if m.get("type") not in ("invariant", "contract"):
                soft_items.append(
                    SoftContextItem(
                        item_id=str(m.get("id", "")),
                        category="memory",
                        text=m["content"],
                        score=score_by_id.get(str(m.get("id", "")), 0.0),
                    )
                )
        for d in diffs:
            sha = str(d.get("sha", ""))
            soft_items.append(
                SoftContextItem(
                    item_id=sha,
                    category="diff",
                    text=f"Commit {sha[:8]}: {d['message']}",
                    score=score_by_id.get(sha, 0.0),
                )
            )
        for index, item in enumerate(soft_additions):
            soft_items.append(
                SoftContextItem(
                    item_id=f"finding:{index}",
                    category="finding",
                    text=item,
                    score=0.0,
                )
            )
        soft_items.sort(key=lambda item: (-item.score, item.item_id))

        compressed, compression_trace = self._compressor.compress_with_trace(
            hard_constraints, soft_items, task
        )

        latency_ms = int((time.monotonic() - start) * 1000)
        brief_id = uuid.uuid4()
        generated_at = datetime.now(timezone.utc)

        brief = ContextBrief(
            brief_id=brief_id,
            task=task,
            scope=scope,
            generated_at=generated_at,
            latency_ms=latency_ms,
            task_kind=str(task_kind),
            retrieved=RetrievedItems(memories=memories, diffs=diffs),
            ranked_signals=ranked,
            hard_constraints=hard_constraints,
            compressed_context=compressed,
            tenant_id=tenant_id,
            data_sources={
                "file_signals": file_signals_status,
                "runtime": runtime_status,
                "workflow": workflow_status,
            },
            compression_trace=compression_trace,
            forbidden_edits=forbidden_edits,
            allowed_edits=allowed_edits,
        )

        self._persist(brief)
        return brief

    def _persist(self, brief: ContextBrief) -> None:
        data_sources_json = json.dumps({
            k: {
                "status": v.status,
                "detail": v.detail,
                "checked_at": v.checked_at.isoformat() if v.checked_at else None,
            }
            for k, v in brief.data_sources.items()
        })
        ranked_signals_json = json.dumps([
            {
                "item_id": s.item_id,
                "item_type": s.item_type,
                "score": s.score,
                "signal_breakdown": s.signal_breakdown,
            }
            for s in brief.ranked_signals
        ])
        self._conn.execute(
            """
            INSERT INTO cortex_briefs (
                brief_id, task, scope, generated_at, latency_ms,
                retrieved_memories, retrieved_diffs, compressed_context, hard_constraints,
                tenant_id, data_sources, ranked_signals, compression_trace
            ) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::jsonb, %s, %s::jsonb, %s::jsonb, %s::jsonb)
            """,
            (
                str(brief.brief_id),
                brief.task,
                brief.scope,
                brief.generated_at,
                brief.latency_ms,
                json.dumps(brief.retrieved.memories),
                json.dumps(brief.retrieved.diffs),
                brief.compressed_context,
                json.dumps(brief.hard_constraints),
                brief.tenant_id,
                data_sources_json,
                ranked_signals_json,
                json.dumps(brief.compression_trace),
            ),
        )
        self._conn.commit()
