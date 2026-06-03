# Observability & Analysis Architecture — Design

**Status:** STAGED PROGRAM (proposal). Governed by `02_06_execution_ledger.md`. Restructured 2026-06-02 per Codex sign-off into Foundation → Activation → Optimization, with the `02_06_design_pressure_test.md` blocking fixes folded in. Additive, **post-A4**.
**Readiness:** Foundation (OTel/OpenInference schema + `repo_metrics_v` authority + one exposed surface) = **active**; Activation (Grafana over real signals) = **active over existing signals, but trend panels blocked on CB metrics existing**; Optimization (Superset, custom UI) = **blocked on demand/workflows**.

---

## 1. Purpose

Turn CHIPS's existing instrumentation (OTel traces + Prometheus metrics + DuckDB export) into an operator/analyst/product surface — **without UI-product lock-in**. The minimal standing surface is **Grafana over signals CHIPS already emits**; everything heavier is gated on demonstrated need. Metrics are computed in CHIPS; surfaces only visualize.

## 2. Scope (phase-local)

**In scope (this program):** an OpenInference attribute schema; a single metrics authority (`repo_metrics_v`); Grafana as the standing surface; Tempo as an optional trace datasource.

**Out of scope for the current phase:** Superset and the custom CHIPS UI (preserved in §6, **blocked** on demand/workflow evidence); Phoenix (dropped — §11). Trend dashboards for mastery/drift/freshness/risk are **inert until CB metrics exist** (§5).

## 3. Capability map

| Capability | Layer | Status | Prerequisite | Unlock evidence | Test gate |
|---|---|---|---|---|---|
| OpenInference `chips.*` schema | Foundation | **active** | — | attr registry snapshot | span contract test |
| `metrics_authority` (`repo_metrics_v`) | Foundation | **active** | metrics computed in CHIPS | view defined | CI: no dashboard aggregates raw tables |
| `grafana_surface` (ops/alerts) | Foundation→Activation | **active** | Prometheus `/metrics` | provisioned | panels reference only Prometheus / `repo_metrics_v` |
| `grafana_repo_trends` | Activation | **blocked** | CB mastery/drift/freshness/risk exist | CB metrics active | trends sourced from Postgres SQL, not Prom labels |
| `tempo_trace_ui` | Activation (optional) | **dormant** | live trace-debug need | stated need | n/a (Grafana datasource) |
| `superset` | Optimization | **blocked** | multi-analyst demand; Grafana insufficient | stated need | n/a |
| `custom_chips_ui` | Optimization | **blocked** | stable workflows; MCP/CLI proven insufficient | workflow evidence | n/a |

## 4. Foundations (buildable now)

- **OpenInference attribute schema** — snapshot the `chips.*` custom-attribute registry (repo/tenant/scope/task-kind, signals, governor decision, evidence-bundle summary, policy/action/reward) alongside the standard RETRIEVER/RERANKER/EMBEDDING/TOOL/CHAIN kinds (`openinference-assessment.md`). Emit **manually** (no auto-instrumentors).
- **`repo_metrics_v`** — one CHIPS-owned SQL view that is the **sole source** for every panel. This is the executable form of the "metrics computed in CHIPS" invariant.
- **Span contract test** — an end-to-end test that runs a brief and asserts the expected span tree exists (manual emission → otherwise silent gaps). Replaces the vague "review-gate check."

## 5. Activation path (what turns it on)

- **`grafana_surface`** is active now over **existing** Prometheus metrics + OTel traces (ops dashboards, alerts, source health, governor/reranker rates) — zero re-instrumentation.
- **`grafana_repo_trends`** (per-repo mastery/drift/freshness/risk) is **blocked until the CB metrics exist** (verifier-gated). When active, these trends are sourced from **Postgres/DuckDB via Grafana SQL, NEVER Prometheus labels** (per-`repo×tenant×policy_version` labels = cardinality bomb).
- **Durable "why" vs live trace:** the durable per-brief rationale is the **decision log** (CB §9), not the trace; Tempo/Jaeger is for **live/recent** debugging only (traces are retention-bounded).

## 6. Optimization path (later, each gated)

- **`superset`** (Apache-2.0; DuckDB + Postgres native) — analyst BI (reward/regret by repo/task/language/policy, constraint effectiveness, cohorts). **Blocked on demonstrated multi-analyst demand.** Caveat: heavy runtime (Redis + Celery + metadata DB) — until unlocked, the fallback is **DuckDB CLI / notebook** (zero standing services). Reuse Postgres for metadata if adopted.
- **`custom_chips_ui`** — domain-only control surfaces (constraint promote/retire queue, evidence-bundle inspection, "why did this brief score poorly", learning-loop controls). **Blocked on stable workflows**; the true minimum first is **MCP tools / CLI + Grafana read-only** (CHIPS is MCP-native). Build a web UI only when CLI review demonstrably doesn't scale; thin, last; read-only before control. (AGPL note: if a custom UI ever embeds Grafana panels, the AGPL network-use clause applies.)

## 7. Dependency graph

| Dependency | Required by | Blocking condition if absent |
|---|---|---|
| `metrics_authority` (`repo_metrics_v`) | grafana_repo_trends, superset, custom_ui | metric definitions fork across surfaces (gap #8) |
| OpenInference `chips.*` registry | span_emission, all trace surfaces | ad-hoc attribute drift |
| CB mastery/drift/freshness/risk | grafana_repo_trends | trend panels render null/inert |
| Postgres SQL datasource (not Prom) | grafana_repo_trends | Prometheus cardinality explosion |
| demonstrated analyst demand | superset | over-built standing service |
| stable review workflows | custom_chips_ui | scope-sink bespoke app |

## 8. Invariant table

| Invariant | Why | Mechanism | Proof |
|---|---|---|---|
| Metrics computed in CHIPS; surfaces only visualize | no lock-in; single definition | `repo_metrics_v` = sole panel source | CI check fails any dashboard JSON aggregating raw tables |
| Span coverage is complete | manual emission → silent gaps | end-to-end span contract test | test asserts expected span tree per brief |
| Per-repo trends never via Prometheus labels | cardinality safety | trends sourced from Postgres/DuckDB SQL only | dashboard-source lint |
| One standing surface until demand proven | simplicity | Grafana-only; Superset/UI gated in ledger | ledger status = blocked until unlock recorded |

## 9. Data contract

- **Spans:** standard OpenInference kinds + `chips.*` namespaced attributes (versioned/snapshotted registry).
- **`repo_metrics_v`:** the authoritative per-repo metric view; declares aggregation level (repo primary; scope/tenant rollups) and the **insufficient-evidence** state (surfaced distinctly when `n < N_min`, per ledger §6).
- **Cardinality rule:** high-cardinality dimensions (repo×tenant×policy_version) live in Postgres/DuckDB, **never** as Prometheus labels.
- **Retention:** traces are retention-bounded (live debugging); durable rationale is the decision log.

## 10. Failure modes

| Failure | How | Detection | Fallback |
|---|---|---|---|
| Metric definition forks | analyst computes "drift" in Superset/Grafana SQL | CI check on dashboard JSON | `repo_metrics_v` sole source |
| Cardinality explosion | per-repo trends via Prom labels | Prometheus TSDB growth alert | route trends via Postgres SQL |
| Silent span gaps | new code path emits no span | span contract test in CI | block merge until span added |
| Surface sprawl / effort SPOF | standing up 4 surfaces | ledger status review | Grafana-only until demand recorded |
| Superset weight | Redis+Celery+metadata DB | deployment review | DuckDB notebook fallback |
| Inert dashboards | trend panels built before CB metrics exist | metric-exists precondition | gate trends on CB activation |

## 11. Decision log

- **Accepted:** Grafana-only standing surface over existing signals; `repo_metrics_v` single authority + CI check; span contract test; Tempo as optional datasource; metrics computed in CHIPS.
- **Deferred:** Superset (→ DuckDB notebook until demand), custom CHIPS UI (→ MCP/CLI + Grafana read-only first), per-repo trend panels (until CB metrics exist).
- **Rejected:** Phoenix (generic LLM-trace product; CHIPS would outgrow it; OpenInference keeps it zero-lock-in later); standing up four surfaces at once; per-repo trends via Prometheus labels; "review-gate check" (replaced by an executable contract test).

## 12. Implementation sequence (each step ends with an artifact + test gate)

1. **OpenInference `chips.*` attribute registry** (snapshot) → *artifact:* registry doc; *gate:* attr-presence test.
2. **Manual span emission helper** → *artifact:* helper module; *gate:* end-to-end span contract test.
3. **`repo_metrics_v` view + CI check** → *artifact:* view + CI rule; *gate:* CI fails dashboards aggregating raw tables.
4. **Grafana over existing Prometheus + Tempo datasource** → *artifact:* ops dashboards/alerts; *gate:* panels reference only approved sources.
5. *(Activation — blocked on CB metrics)* per-repo trend panels via Postgres SQL.
6. *(Optimization — blocked)* Superset (on demand) → custom UI (on workflows).

## 13. Readiness exit criteria

- **Foundation → Activation:** `chips.*` registry snapshot; span contract test green; `repo_metrics_v` single-source + **CI-enforced**; Grafana live over existing signals.
- **Activation (trends):** CB mastery/drift/freshness/risk **exist** (verifier-gated) and are exposed via `repo_metrics_v`; trends sourced via Postgres SQL.
- **Optimization:** Superset only on recorded multi-analyst demand; custom UI only on recorded stable-workflow evidence + proof MCP/CLI is insufficient.

### Cross-references
`02_06_execution_ledger.md` (authority), `02_06_design_pressure_test.md` §4/§D (findings folded in), `research/openinference-assessment.md` (transport/semantics), `02_06_contextual_bandit_design.md` §9.3 (metrics this surfaces), roadmap §7.3 (decision record), §5 ledger (Phoenix dropped).
