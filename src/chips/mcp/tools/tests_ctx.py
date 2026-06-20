from __future__ import annotations

from datetime import datetime, timezone
import psycopg

from chips.compiler.retrieval import _fragility_inputs, _fragility_score
from chips.harvester.assay import assay_signal
from chips.harvester.defect_corpus import estimate_defect_density, high_precision_defect_sql
from chips.harvester.yield_score import compute_yield_score


def get_test_context(
    conn: psycopg.Connection,
    scope: str | None = None,
    limit: int = 20,
    tenant_id: str | None = None,
) -> dict:
    """Return test file signals and co-change pairs, optionally filtered by scope and tenant."""
    scope_pattern = f"%{scope}%" if scope else None

    file_conditions = ["file_path ILIKE '%test%'"]
    file_params: list = []
    if scope_pattern:
        file_conditions.append("file_path ILIKE %s")
        file_params.append(scope_pattern)
    if tenant_id is not None:
        file_conditions.append("tenant_id = %s")
        file_params.append(tenant_id)
    file_params.append(limit)
    predicate = high_precision_defect_sql("d")

    file_rows = conn.execute(
        f"""
        SELECT
            file_path,
            churn_score,
            cochange_entropy,
            generated_kind,
            (
                SELECT COUNT(DISTINCT g.sha)
                FROM cortex_git_commits g
                JOIN cortex_defect_corpus d ON d.sha = g.sha
                WHERE g.files_changed && ARRAY[cortex_file_signals.file_path]
                  AND {predicate}
            ) AS defect_history_count,
            failure_count
        FROM cortex_file_signals
        WHERE {' AND '.join(file_conditions)}
        ORDER BY churn_score DESC
        LIMIT %s
        """,  # type: ignore[arg-type]
        tuple(file_params),
    ).fetchall()

    cochange_conditions = ["(file_a ILIKE '%test%' OR file_b ILIKE '%test%')"]
    cochange_params: list = []
    if scope_pattern:
        cochange_conditions.append("(file_a ILIKE %s OR file_b ILIKE %s)")
        cochange_params.extend([scope_pattern, scope_pattern])
    if tenant_id is not None:
        cochange_conditions.append("tenant_id = %s")
        cochange_params.append(tenant_id)

    cochange_rows = conn.execute(
        f"""
        SELECT file_a, file_b, frequency
        FROM cortex_cochange_pairs
        WHERE {' AND '.join(cochange_conditions)}
        ORDER BY frequency DESC
        LIMIT 10
        """,  # type: ignore[arg-type]
        tuple(cochange_params),
    ).fetchall()

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
