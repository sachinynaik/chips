from __future__ import annotations

import psycopg

from chips.compiler.fragility import fragility_inputs, fragility_score
from chips.harvester.storage import HarvesterStore, PostgresHarvesterStore
from chips.harvester.assay import assay_signal
from chips.harvester.defect_corpus import estimate_defect_density
from chips.harvester.yield_score import compute_yield_score
from chips.mcp.tools.diffs import get_diffs_for_scope as _get_diffs_for_scope
from chips.mcp.tools.memory import search_memory as _search_memory
from datetime import datetime, timezone


def retrieve_memories(
    conn: psycopg.Connection,
    embedding: list[float],
    scope: str | None = None,
    limit: int = 5,
    tenant_id: str | None = None,
) -> list[dict]:
    return _search_memory(conn, embedding, scope=scope, limit=limit, tenant_id=tenant_id)


def retrieve_file_signals(
    conn: psycopg.Connection | HarvesterStore,
    files: list[str],
    tenant_id: str | None = None,
) -> list[dict]:
    if not files:
        return []
    rows = _as_harvester_store(conn).file_signals_for_paths(files, tenant_id=tenant_id)
    results = []
    for row in rows:
        defect_density, defect_density_basis_nloc = estimate_defect_density(
            [row[0]],
            defect_count=row[4],
        )
        yield_score = compute_yield_score(
            churn_score=row[1],
            cochange_entropy=row[2],
            defect_history_count=row[4],
            defect_density=defect_density,
        )
        assay = assay_signal(
            source_kind="git_history",
            assayed_at=datetime.now(timezone.utc),
            code_version=None,
            observed_changed_at=row[6],
            dopants=[],
        )
        results.append(
            {
                "file_path": row[0],
                "churn_score": row[1],
                "cochange_entropy": row[2],
                "generated_kind": row[3],
                "defect_history_count": row[4],
                "defect_density": defect_density,
                "defect_density_basis_nloc": defect_density_basis_nloc,
                "yield_score": yield_score,
                "assay": assay,
                "fragility": _fragility_score(row[1], row[2], row[4]),
                "fragility_inputs": _fragility_inputs(row[1], row[2], row[4]),
                "failure_count": row[5],
                "last_changed_at": row[6],
            }
        )
    return results


def _fragility_score(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
) -> float:
    return fragility_score(churn_score, cochange_entropy, defect_history_count)


def _fragility_inputs(
    churn_score: float | None,
    cochange_entropy: float | None,
    defect_history_count: int | None,
) -> dict[str, object]:
    return fragility_inputs(churn_score, cochange_entropy, defect_history_count)


def retrieve_diffs(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 10,
    tenant_id: str | None = None,
) -> list[dict]:
    return _get_diffs_for_scope(conn, scope=scope, limit=limit, tenant_id=tenant_id)["commits"]


def retrieve_cochanges(
    conn: psycopg.Connection | HarvesterStore,
    files: list[str],
    limit: int = 10,
    tenant_id: str | None = None,
) -> list[dict]:
    if not files:
        return []
    rows = _as_harvester_store(conn).cochanges_for_files(files, limit=limit, tenant_id=tenant_id)
    return [
        {"file_a": row[0], "file_b": row[1], "frequency": row[2], "last_seen_at": row[3]}
        for row in rows
    ]


def _as_harvester_store(conn: psycopg.Connection | HarvesterStore) -> HarvesterStore:
    if isinstance(conn, PostgresHarvesterStore) or hasattr(type(conn), "file_signals_for_paths"):
        return conn
    return PostgresHarvesterStore(conn)
