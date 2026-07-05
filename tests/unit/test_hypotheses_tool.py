from __future__ import annotations

from uuid import uuid4

from chips.mcp.tools.hypotheses import submit_hypotheses


def _bundle_wire() -> dict:
    bid = uuid4()
    return {
        "bundle_id": str(bid),
        "constraints": [
            {
                "evidence_id": "con:1",
                "kind": "constraint",
                "label": "Invariant lock",
                "text": "INVARIANT: preserve lock order",
                "weight": 1.0,
                "constraint_kind": "invariant",
                "target": {"path": "src/pay.py", "symbol": "checkout.pay"},
                "refs": {"source_ref": "policy:checkout"},
            }
        ],
        "evidence": [
            {
                "evidence_id": "mem:1",
                "kind": "memory",
                "label": "Prior race",
                "text": "A prior race happened in checkout.",
                "weight": 2.0,
                "constraint_kind": None,
                "target": {},
                "refs": {},
            },
            {
                "evidence_id": "find:fragility123",
                "kind": "finding",
                "label": "Fragility",
                "text": "Fragility: defect-linked churn is elevated.",
                "weight": 1.0,
                "constraint_kind": None,
                "target": {},
                "refs": {},
            },
        ],
    }


def _hypothesis(hid: str, **overrides) -> dict:
    payload = {
        "hypothesis_id": hid,
        "claim": f"claim {hid}",
        "mechanism": f"mechanism {hid}",
        "cited_evidence": ["mem:1"],
        "touched_paths": [],
        "touched_symbols": [],
        "declared_violations": [],
        "predicted_checks": [],
        "rank_hint": None,
    }
    payload.update(overrides)
    return payload


def test_submit_hypotheses_ranks_and_surfaces_contract_violations():
    result = submit_hypotheses(
        evidence_bundle=_bundle_wire(),
        hypotheses=[
            _hypothesis("weak", cited_evidence=["ghost:1"]),
            _hypothesis("strong", cited_evidence=["mem:1", "find:fragility123"]),
        ],
        tenant_id="tenant-x",
    )

    assert result["bundle_id"]
    assert [h["hypothesis_id"] for h in result["ranked_hypotheses"]] == ["strong", "weak"]
    assert result["ranked_hypotheses"][0]["coverage"] == 3.0
    assert result["ranked_hypotheses"][0]["violations"] == []
    assert result["ranked_hypotheses"][1]["violations"] == [
        {"kind": "unknown_evidence_id", "detail": "ghost:1"}
    ]
    assert result["constraint_candidates"] == []
    assert result["unknown_rejected_hypothesis_ids"] == []


def test_submit_hypotheses_emits_constraint_candidate_for_rejected_hypothesis():
    result = submit_hypotheses(
        evidence_bundle=_bundle_wire(),
        hypotheses=[
            _hypothesis(
                "h1",
                cited_evidence=["mem:1", "con:1"],
                touched_paths=["src/pay.py"],
                touched_symbols=["checkout.pay"],
            )
        ],
        rejected_hypothesis_ids=["h1"],
        scope="checkout",
        tenant_id="tenant-x",
    )

    assert len(result["constraint_candidates"]) == 1
    candidate = result["constraint_candidates"][0]
    assert candidate["source_hypothesis_id"] == "h1"
    assert candidate["tenant_id"] == "tenant-x"
    assert candidate["scope"] == "checkout"
    assert candidate["proposed_kind"] == "known_issue"
    assert candidate["proposed_target"] == {
        "path": "src/pay.py",
        "symbol": "checkout.pay",
    }


def test_submit_hypotheses_surfaces_unknown_rejected_ids_and_ignores_them():
    result = submit_hypotheses(
        evidence_bundle=_bundle_wire(),
        hypotheses=[_hypothesis("known")],
        rejected_hypothesis_ids=["known", "missing"],
    )

    assert [c["source_hypothesis_id"] for c in result["constraint_candidates"]] == ["known"]
    assert result["unknown_rejected_hypothesis_ids"] == ["missing"]


def test_submit_hypotheses_uses_empty_target_when_rejected_hypothesis_touches_many_items():
    result = submit_hypotheses(
        evidence_bundle=_bundle_wire(),
        hypotheses=[
            _hypothesis(
                "h1",
                touched_paths=["a.py", "b.py"],
                touched_symbols=["A.run", "B.run"],
            )
        ],
        rejected_hypothesis_ids=["h1"],
    )

    assert result["constraint_candidates"][0]["proposed_target"] == {}
