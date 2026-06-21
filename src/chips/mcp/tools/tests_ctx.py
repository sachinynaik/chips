from __future__ import annotations

from datetime import datetime, timezone
import psycopg

from chips.compiler.retrieval import _fragility_inputs, _fragility_score
from chips.harvester.storage import HarvesterStore, PostgresHarvesterStore
from chips.harvester.assay import assay_signal
from chips.harvester.defect_corpus import estimate_defect_density
from chips.harvester.yield_score import compute_yield_score


def get_test_context(
    conn: psycopg.Connection | HarvesterStore,
    scope: str | None = None,
    limit: int = 20,
    tenant_id: str | None = None,
) -> dict:
    """Return test file signals and co-change pairs, optionally filtered by scope and tenant."""
    store = _as_harvester_store(conn)
    file_rows = store.test_file_signals(scope=scope, limit=limit, tenant_id=tenant_id)
    cochange_rows = store.test_cochanges(scope=scope, limit=10, tenant_id=tenant_id)

    return {
        "test_files": [
            _build_test_file_context(
                file_path=file_path,
                churn_score=churn_score,
                cochange_entropy=cochange_entropy,
                generated_kind=generated_kind,
                defect_history_count=defect_history_count,
                failure_count=failure_count,
            )
            for file_path, churn_score, cochange_entropy, generated_kind, defect_history_count, failure_count in file_rows
        ],
        "cochange_pairs": [
            {"file_a": a, "file_b": b, "frequency": freq}
            for a, b, freq in cochange_rows
        ],
        "scope": scope,
        "status": "ok",
    }


def _as_harvester_store(conn: psycopg.Connection | HarvesterStore) -> HarvesterStore:
    if isinstance(conn, PostgresHarvesterStore) or hasattr(type(conn), "test_file_signals"):
        return conn
    return PostgresHarvesterStore(conn)


def _build_test_file_context(
    *,
    file_path: str,
    churn_score: float | None,
    cochange_entropy: float | None,
    generated_kind: str | None,
    defect_history_count: int | None,
    failure_count: int | None,
) -> dict:
    defect_density, defect_density_basis_nloc = estimate_defect_density(
        [file_path],
        defect_count=defect_history_count or 0,
    )
    return {
        "file_path": file_path,
        "churn_score": churn_score,
        "cochange_entropy": cochange_entropy,
        "generated_kind": generated_kind,
        "defect_history_count": defect_history_count,
        "defect_density": defect_density,
        "defect_density_basis_nloc": defect_density_basis_nloc,
        "yield_score": compute_yield_score(
            churn_score=churn_score,
            cochange_entropy=cochange_entropy,
            defect_history_count=defect_history_count,
            defect_density=defect_density,
        ),
        "assay": assay_signal(
            source_kind="git_history",
            assayed_at=datetime.now(timezone.utc),
            code_version=None,
            observed_changed_at=None,
            dopants=[],
        ),
        "fragility": _fragility_score(churn_score, cochange_entropy, defect_history_count),
        "fragility_inputs": _fragility_inputs(churn_score, cochange_entropy, defect_history_count),
        "failure_count": failure_count,
    }
