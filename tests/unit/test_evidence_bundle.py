"""Slice A1 (contract §B / §I.5): project assembled signals into an EvidenceBundle.

Pure tests (no DB, no LLM) for ``assemble_evidence_bundle`` and the wire serializer.
The bundle is a typed, stable-ID *projection* of what ``BriefBuilder.build()`` already
assembles — constraints (contradiction layer) + citable soft evidence.
"""
from __future__ import annotations

from uuid import uuid4

from chips.compiler.evidence import finding_evidence_id
from chips.compiler.evidence_bundle import assemble_evidence_bundle
from chips.compiler.models import Constraint, SoftContextItem
from chips.mcp.modules.brief import evidence_bundle_to_wire


def _constraint(**kw) -> Constraint:
    base = dict(
        id=uuid4(), tenant_id="t1", scope_pattern="*", kind="forbidden",
        text="never call os.system", target={"path": "app.py", "symbol": "run"},
    )
    base.update(kw)
    return Constraint(**base)


def _finding_item() -> SoftContextItem:
    fid = finding_evidence_id(
        {"kind": "dead_code", "type": "function", "name": "old", "file": "u.py"}
    )
    return SoftContextItem(item_id=fid, category="finding", text="Dead code: function 'old'", score=0.0)


def test_finding_item_keeps_find_id():
    bid = uuid4()
    bundle = assemble_evidence_bundle(bid, [], [_finding_item()])
    assert bundle.bundle_id == bid
    assert len(bundle.evidence) == 1
    e = bundle.evidence[0]
    assert e.kind == "finding"
    assert e.evidence_id.startswith("find:")


def test_memory_and_diff_get_prefixed_ids():
    mem = SoftContextItem(
        item_id="11111111-1111-1111-1111-111111111111", category="memory", text="m", score=0.7
    )
    diff = SoftContextItem(item_id="abc123", category="diff", text="Commit abc123: x", score=0.5)
    bundle = assemble_evidence_bundle(uuid4(), [], [mem, diff])
    by = {e.evidence_id: e for e in bundle.evidence}
    assert "mem:11111111-1111-1111-1111-111111111111" in by
    assert "diff:abc123" in by
    assert by["mem:11111111-1111-1111-1111-111111111111"].weight == 0.7  # soft score carried


def test_constraints_become_constraint_items_weight_one():
    c = _constraint()
    bundle = assemble_evidence_bundle(uuid4(), [c], [])
    assert len(bundle.constraints) == 1
    ci = bundle.constraints[0]
    assert ci.kind == "constraint"
    assert ci.constraint_kind == "forbidden"
    assert ci.weight == 1.0  # authority weight per §B
    assert ci.target == {"path": "app.py", "symbol": "run"}
    assert ci.evidence_id == f"con:{c.id}"


def test_by_id_and_constraint_by_id_resolve():
    c = _constraint()
    f = _finding_item()
    bundle = assemble_evidence_bundle(uuid4(), [c], [f])
    assert bundle.by_id(f"con:{c.id}") is not None
    assert bundle.by_id(f.item_id).kind == "finding"
    assert bundle.constraint_by_id(f"con:{c.id}") is not None
    assert bundle.constraint_by_id(f.item_id) is None  # a finding is not a constraint


def test_empty_natural_key_soft_item_is_skipped():
    empty = SoftContextItem(item_id="", category="memory", text="m", score=0.1)
    bundle = assemble_evidence_bundle(uuid4(), [], [empty])
    assert bundle.evidence == []  # no stable identity → not citable


def test_non_citable_category_skipped():
    # file/generic are not citable evidence kinds in v1 (file wired in A2a)
    f = SoftContextItem(item_id="x", category="file", text="f", score=0.2)
    g = SoftContextItem(item_id="y", category="generic", text="g", score=0.2)
    bundle = assemble_evidence_bundle(uuid4(), [], [f, g])
    assert bundle.evidence == []


def test_structural_id_prefixing():
    already = SoftContextItem(item_id="struct:app.py#run", category="structural", text="s", score=0.3)
    bare = SoftContextItem(item_id="app.py#helper", category="structural", text="s2", score=0.3)
    bundle = assemble_evidence_bundle(uuid4(), [], [already, bare])
    ids = {e.evidence_id for e in bundle.evidence}
    assert "struct:app.py#run" in ids
    assert "struct:app.py#helper" in ids


def test_constraint_provenance_populates_refs_and_label():
    c = _constraint(source_kind="bandit", source_ref="GoRule-104")
    bundle = assemble_evidence_bundle(uuid4(), [c], [])
    ci = bundle.constraints[0]
    assert ci.label == "GoRule-104"  # source_ref preferred over text snippet
    assert ci.refs == {"source_kind": "bandit", "source_ref": "GoRule-104"}


def test_empty_prefixed_id_is_skipped():
    # a finding/structural item with no item_id has no citable identity
    f = SoftContextItem(item_id="", category="finding", text="x", score=0.0)
    s = SoftContextItem(item_id="", category="structural", text="y", score=0.0)
    bundle = assemble_evidence_bundle(uuid4(), [], [f, s])
    assert bundle.evidence == []


def test_wire_serializer_shape():
    c = _constraint()
    f = _finding_item()
    bundle = assemble_evidence_bundle(uuid4(), [c], [f])
    wire = evidence_bundle_to_wire(bundle)
    assert wire is not None
    assert wire["bundle_id"] == str(bundle.bundle_id)
    assert len(wire["constraints"]) == 1
    assert wire["constraints"][0]["constraint_kind"] == "forbidden"
    assert wire["constraints"][0]["target"] == {"path": "app.py", "symbol": "run"}
    assert len(wire["evidence"]) == 1
    assert wire["evidence"][0]["kind"] == "finding"


def test_wire_serializer_none():
    assert evidence_bundle_to_wire(None) is None
