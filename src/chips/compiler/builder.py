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
from chips.compiler.constraint_repository import ConstraintRepository
from chips.compiler.evidence import finding_evidence_id
from chips.compiler.evidence_bundle import assemble_evidence_bundle
from chips.compiler.constraints import (
    assemble_forbidden_edits,
    assemble_hard_constraints,
    effective_allowed_edits,
)
from chips.compiler.governor import GovernorDecision, evaluate as governor_evaluate
from chips.compiler.ranker import rank_signals
from chips.compiler.reranker import rerank
from chips.compiler.retrieval import retrieve_diffs, retrieve_file_signals, retrieve_memories
from chips.compiler.structural import retrieve_structural
from chips.harvester.embedding import OllamaEmbedder
from chips.mcp.tools.runtime import probe_runtime
from chips.mcp.tools.workflow import probe_workflow
from chips.observability.metrics import (
    observe_brief_build,
    observe_governor_decision,
    observe_structural_retrieval,
)
from chips.observability.openinference import (
    ATTR_BRIEF_ID,
    ATTR_EMBEDDING_DIMENSIONS,
    ATTR_GOVERNOR_TRIGGERED,
    ATTR_LATENCY_MS,
    ATTR_RERANKER_INPUT_COUNT,
    ATTR_RERANKER_OUTPUT_COUNT,
    ATTR_RETRIEVER_DIFF_COUNT,
    ATTR_RETRIEVER_FILE_SIGNAL_COUNT,
    ATTR_RETRIEVER_MEMORY_COUNT,
    ATTR_RETRIEVER_STRUCTURAL_COUNT,
    ATTR_SCOPE,
    ATTR_TASK_KIND,
    ATTR_TENANT_ID,
    SpanKind,
)
from chips.observability.tracing import start_span

logger = logging.getLogger(__name__)


def _normalized_finding(kind: str, item: dict) -> dict:
    """Identity-bearing fields of a soft finding, for the stable ``find:`` content hash.

    Contract §A (LOCKED 2026-05-31): hash over identity fields only — volatile metrics
    (``severity``/``confidence``/missing-line counts) are excluded so re-tuning them does
    not mint a new ID. The ``kind`` discriminator keeps distinct kinds from colliding.
    Kept here (not in ``evidence.py``) so the pure ID module stays kind-agnostic.
    """
    if kind == "security":
        return {"kind": kind, "test_id": item.get("test_id", ""), "file": item.get("file", ""),
                "line": item.get("line", "?"), "message": item.get("message", "")}
    if kind == "dead_code":
        return {"kind": kind, "type": item.get("type", ""), "name": item.get("name", ""),
                "file": item.get("file", "")}
    if kind == "api_surface":
        return {"kind": kind, "change_type": item.get("change_type", ""),
                "symbol": item.get("symbol", ""), "details": item.get("details", "")}
    if kind == "clones":
        return {"kind": kind, "files": sorted([item.get("file_a", ""), item.get("file_b", "")]),
                "lines": item.get("lines", "?")}
    if kind == "type_errors":
        return {"kind": kind, "code": item.get("code", ""), "line": item.get("line", "?"),
                "message": item.get("message", "")}
    # uncovered_changes is handled inline (its identity is the path string, not a dict).
    return {"kind": kind, **item}


def _soft(kind: str, item: dict, text: str) -> tuple[str, str]:
    """Pair a soft finding's stable ``find:`` ID with its rendered text."""
    return finding_evidence_id(_normalized_finding(kind, item)), text


def _apply_learning_adjustments(
    memories: list[dict], adjustments: dict[str, float]
) -> None:
    """Attach each memory's learning adjustment for the ranker — WITHOUT mutating
    ``confidence``.

    The adjustment biases *ranking* only: ``rank_signals`` adds ``learning_adjustment``
    to the semantic score. It must not touch ``confidence``, because (a) the governor
    reads ``confidence`` as a *pre-learning* retrieval signal (see ``governor.evaluate``)
    and a leaked adjustment can wrongly trip its short-circuit on the no-``similarity``
    fallback path, and (b) the ranker would then double-count the adjustment (``sem``
    falls back to the mutated confidence, then adds ``learning_adjustment`` again).
    """
    for memory in memories:
        memory["learning_adjustment"] = adjustments.get(str(memory.get("id", "")), 0.0)


def _extract_brief_signals(
    memories: list[dict],
) -> tuple[list[str], list[tuple[str, str]]]:
    """Extract hard_additions and soft_additions from structured_findings in memories.

    hard_additions: HIGH/MEDIUM security findings, architecture violations (plain text —
        these become ``hard_constraints``, not citable evidence, so they carry no ID).
    soft_additions: ``(find_id, text)`` pairs for dead code, API surface issues, clones,
        type errors, uncovered changes, and LOW security findings. The ID is the stable
        ``find:<content-hash>`` (contract §A), replacing the old positional ``finding:{i}``.

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
    soft_additions: list[tuple[str, str]] = []

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
                soft_additions.append(_soft("security", item, formatted))

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
            soft_additions.append(_soft(
                "dead_code", item,
                f"Dead code: {kind} '{name}' in {file_} (confidence {confidence}%)",
            ))

        # API surface → soft
        for item in findings.get("api_surface", []):
            change_type = item.get("change_type", "")
            symbol = item.get("symbol", "")
            details = item.get("details", "")
            soft_additions.append(_soft(
                "api_surface", item, f"API issue [{change_type}]: {symbol} — {details}",
            ))

        # Clones → soft
        for item in findings.get("clones", []):
            lines = item.get("lines", "?")
            file_a = item.get("file_a", "")
            file_b = item.get("file_b", "")
            soft_additions.append(_soft(
                "clones", item,
                f"Code clone: {lines} lines duplicated between {file_a} and {file_b}",
            ))

        # Type errors → soft
        for item in findings.get("type_errors", []):
            code = item.get("code", "")
            line = item.get("line", "?")
            message = item.get("message", "")
            soft_additions.append(_soft(
                "type_errors", item, f"Type error [{code}] line {line}: {message}",
            ))

        # Uncovered changes: dict[path → info] → soft. Identity is the path string, so
        # the ID is built inline rather than through the dict-typed _normalized_finding.
        for path, info in findings.get("uncovered_changes", {}).items():
            basename = os.path.basename(path)
            missing = info.get("changed_lines_missing", "?")
            find_id = finding_evidence_id({"kind": "uncovered_changes", "path": path})
            soft_additions.append((
                find_id,
                f"Uncovered changes in {basename}: {missing} changed lines have no tests",
            ))

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

        with start_span(
            "chips.compile.brief",
            kind=SpanKind.CHAIN,
            **{ATTR_SCOPE: scope, ATTR_TENANT_ID: tenant_id},
        ) as root_span:
            task_kind = classify_task(task)

            with start_span("chips.embed.task", kind=SpanKind.EMBEDDING) as embed_span:
                embedding = self._embedder.embed(task)
                if embed_span is not None:
                    embed_span.set_attribute(ATTR_EMBEDDING_DIMENSIONS, len(embedding))

            learning = BriefLearningService(self._conn)
            adjustments = learning.load_adjustments(tenant_id=tenant_id)

            with start_span("chips.retrieve", kind=SpanKind.RETRIEVER) as retrieve_span:
                memories = retrieve_memories(
                    self._conn, embedding, scope=scope, tenant_id=tenant_id
                )
                _apply_learning_adjustments(memories, adjustments)

                # Governor: if memories are already high-confidence, skip secondary sources.
                governor = governor_evaluate(memories)
                observe_governor_decision(triggered=governor.triggered)

                effective_files = files if files else []
                if governor.triggered:
                    file_signals = []
                    file_signals_status = SourceStatus(
                        status="not_configured",
                        detail=f"governor short-circuit: {governor.reason}",
                    )
                    diffs = []
                else:
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

                # Structural retrieval: AST call-graph walk over provided files.
                structural_items: list[dict] = []
                if effective_files and not governor.triggered:
                    try:
                        structural_items = retrieve_structural(effective_files)
                        observe_structural_retrieval(status="success")
                    except Exception as exc:
                        logger.warning("structural retrieval failed: %s", exc)
                        observe_structural_retrieval(status="error")
                else:
                    observe_structural_retrieval(status="skipped")

                if retrieve_span is not None:
                    retrieve_span.set_attribute(ATTR_RETRIEVER_MEMORY_COUNT, len(memories))
                    retrieve_span.set_attribute(ATTR_RETRIEVER_DIFF_COUNT, len(diffs))
                    retrieve_span.set_attribute(
                        ATTR_RETRIEVER_FILE_SIGNAL_COUNT, len(file_signals)
                    )
                    retrieve_span.set_attribute(
                        ATTR_RETRIEVER_STRUCTURAL_COUNT, len(structural_items)
                    )

            runtime_status = probe_runtime()
            if runtime_status.status == "error":
                logger.warning("runtime source probe failed: %s", runtime_status.detail)

            workflow_status = probe_workflow()
            if workflow_status.status == "error":
                logger.warning("workflow source probe failed: %s", workflow_status.detail)

            ranked = rank_signals(memories, file_signals, diffs=diffs)

            # Static policy layer
            policy_forbidden: list[str] = []
            policy_required: list[str] = []
            if self._policy_loader is not None:
                for policy in self._policy_loader.for_scope(scope):
                    policy_forbidden.extend(policy.forbidden)
                    policy_required.extend(policy.required)

            # Dynamic policy layer: learned anti-regression / declared constraints for scope.
            learned = ConstraintRepository(self._conn).for_scope(scope, tenant_id=tenant_id)

            # Hard constraints in locked precedence order (learned forbidden, policy
            # forbidden, learned invariant, memory invariants, learned known_issue,
            # findings). forbidden_edits stays strictly prohibitive; a forbidden/invariant
            # constraint overrides a conflicting allowed edit (restrictive wins).
            memory_constraints = [
                m["content"] for m in memories
                if m.get("type") in ("invariant", "contract")
            ]
            hard_additions, soft_additions = _extract_brief_signals(memories)
            hard_constraints = assemble_hard_constraints(
                learned,
                policy_forbidden=policy_forbidden,
                memory_invariants=memory_constraints,
                hard_additions=hard_additions,
            )
            forbidden_edits = assemble_forbidden_edits(learned, policy_forbidden)
            allowed_edits = effective_allowed_edits(policy_required, learned)

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
            # File signals (#2): retrieved + ranked above; inject so the paid cost reaches
            # the brief body. category="file" is intentionally NOT a citable EvidenceKind, so
            # assemble_evidence_bundle skips these — they inform context, not hypotheses.
            for sig in file_signals:
                file_path = sig["file_path"]
                soft_items.append(
                    SoftContextItem(
                        item_id=file_path,
                        category="file",
                        text=(
                            f"File {file_path}: churn={sig.get('churn_score')}, "
                            f"failures={sig.get('failure_count')}"
                        ),
                        score=score_by_id.get(file_path, 0.0),
                    )
                )
            for find_id, text in soft_additions:
                soft_items.append(
                    SoftContextItem(
                        item_id=find_id,
                        category="finding",
                        text=text,
                        score=0.0,
                    )
                )
            for s in structural_items:
                soft_items.append(
                    SoftContextItem(
                        item_id=s["item_id"],
                        category="structural",
                        text=s["text"],
                        score=0.0,
                    )
                )
            soft_items.sort(key=lambda item: (-item.score, item.item_id))

            # Rerank soft items using cross-encoder so query-item relevance beats raw scores.
            with start_span("chips.rerank", kind=SpanKind.RERANKER) as rerank_span:
                rerank_input_count = len(ranked) + len(soft_items)
                ranked, soft_items = rerank(task, ranked, soft_items)
                if rerank_span is not None:
                    rerank_span.set_attribute(ATTR_RERANKER_INPUT_COUNT, rerank_input_count)
                    rerank_span.set_attribute(
                        ATTR_RERANKER_OUTPUT_COUNT, len(ranked) + len(soft_items)
                    )

            with start_span("chips.compress", kind=SpanKind.TOOL):
                compressed, compression_trace = self._compressor.compress_with_trace(
                    hard_constraints, soft_items, task
                )

            latency_ms = int((time.monotonic() - start) * 1000)
            brief_id = uuid.uuid4()
            generated_at = datetime.now(timezone.utc)

            if root_span is not None:
                root_span.set_attribute(ATTR_TASK_KIND, str(task_kind))
                root_span.set_attribute(ATTR_BRIEF_ID, str(brief_id))
                root_span.set_attribute(ATTR_LATENCY_MS, latency_ms)
                root_span.set_attribute(ATTR_GOVERNOR_TRIGGERED, governor.triggered)

            # Phase 1 (§I.5): project the assembled constraints + soft items into a typed,
            # stable-ID EvidenceBundle (bundle_id == brief_id). Findings already carry their
            # find:<hash> IDs; constraints become the contradiction layer.
            evidence_bundle = assemble_evidence_bundle(brief_id, learned, soft_items)

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
                governor_decision={
                    "triggered": governor.triggered,
                    "mean_confidence": governor.mean_confidence,
                    "item_count": governor.item_count,
                    "skipped_sources": governor.skipped_sources,
                    "reason": governor.reason,
                },
                evidence_bundle=evidence_bundle,
            )

            self._persist(brief)
            observe_brief_build(status="success", latency_ms=latency_ms)
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
