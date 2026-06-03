"""Dashboard consumer gate (seeds the slice-3 'metrics authority' CI check).

Enforces, non-vacuously:
  1. at least one dashboard exists in grafana/dashboards/ (an empty consumer
     directory must FAIL, not silently pass);
  2. every dashboard is valid JSON with the minimal Grafana shape;
  3. panels query Prometheus only (no SQL datasources until repo_metrics_v
     exists), and no target references raw cortex_* tables -- the ledger's
     "no dashboard aggregates raw tables" rule.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_DASHBOARD_DIR = Path(__file__).resolve().parents[2] / "grafana" / "dashboards"

#: Datasource types panels may use today. Extend with the SQL datasource only
#: when repo_metrics_v lands (slice 3) -- and even then, queries must hit the
#: view, never raw tables.
_ALLOWED_DATASOURCE_TYPES = {"prometheus"}


def _dashboards() -> list[Path]:
    return sorted(_DASHBOARD_DIR.glob("*.json"))


def test_consumer_artifact_exists_gate_is_not_vacuous():
    assert _DASHBOARD_DIR.is_dir(), "grafana/dashboards/ missing"
    assert _dashboards(), (
        "no dashboard JSON in grafana/dashboards/ -- the metrics-authority gate "
        "would be vacuous; the consumer artifact is required"
    )


@pytest.mark.parametrize("path", _dashboards(), ids=lambda p: p.name)
def test_dashboard_has_minimal_grafana_shape(path: Path):
    dash = json.loads(path.read_text(encoding="utf-8"))
    assert dash.get("title"), "dashboard needs a title"
    assert dash.get("uid"), "dashboard needs a stable uid"
    assert dash.get("schemaVersion"), "dashboard needs a schemaVersion"
    assert dash.get("panels"), "dashboard needs at least one panel"


@pytest.mark.parametrize("path", _dashboards(), ids=lambda p: p.name)
def test_panels_query_prometheus_only_and_no_raw_tables(path: Path):
    dash = json.loads(path.read_text(encoding="utf-8"))
    for panel in dash["panels"]:
        ds_type = (panel.get("datasource") or {}).get("type")
        assert ds_type in _ALLOWED_DATASOURCE_TYPES, (
            f"{path.name}: panel {panel.get('title')!r} uses datasource "
            f"{ds_type!r}; allowed: {sorted(_ALLOWED_DATASOURCE_TYPES)}"
        )
        for target in panel.get("targets", []):
            assert "rawSql" not in target, (
                f"{path.name}: panel {panel.get('title')!r} carries rawSql -- "
                "SQL panels are not allowed until repo_metrics_v exists"
            )
            expr = target.get("expr", "")
            assert "cortex_" not in expr, (
                f"{path.name}: panel {panel.get('title')!r} references a raw "
                "cortex_* table -- dashboards must use chips_* metrics or "
                "repo_metrics_v only"
            )
