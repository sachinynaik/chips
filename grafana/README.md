# CHIPS Grafana dashboards

The in-repo consumer artifact for the metrics surface (execution ledger:
`metrics_surface_grafana`). Dashboards here are the **only** sanctioned panel
sources, and they may reference **only**:

1. the Prometheus metrics CHIPS exposes (`chips_*`, rendered by
   `chips.observability.metrics.render_latest_metrics`), and
2. (once slice 3 lands) the `repo_metrics_v` SQL view — never raw `cortex_*` tables.

That rule is enforced by `tests/unit/test_grafana_dashboards.py` — the
"no dashboard aggregates raw tables" gate. It also fails if this directory is
empty, so the gate can never pass vacuously.

## Dashboards

- `dashboards/chips-foundation-ops.json` — ops view over the existing
  Prometheus signals: brief-build rate/latency p95, governor short-circuit
  rate, reranker / structural-retrieval outcomes, feedback submissions.

## Wiring (local)

Point a Grafana instance's dashboard provisioning at `grafana/dashboards/`,
with a Prometheus datasource scraping CHIPS's metrics endpoint. Example
provisioning snippet:

```yaml
apiVersion: 1
providers:
  - name: chips
    type: file
    options:
      path: /path/to/chips/grafana/dashboards
```

The dashboard resolves its datasource via the `DS_PROMETHEUS` template
variable, so it binds to whatever Prometheus datasource the instance has.
