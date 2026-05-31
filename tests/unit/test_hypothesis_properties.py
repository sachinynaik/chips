from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from chips.compiler.evidence import finding_content_hash
from chips.compiler.hypothesis import coverage
from chips.compiler.models import EvidenceBundle, EvidenceItem, Hypothesis


def _bundle() -> EvidenceBundle:
    return EvidenceBundle(
        bundle_id="bundle",  # type: ignore[arg-type]
        evidence=[
            EvidenceItem("mem:1", "memory", "m1", "memory one", weight=0.7),
            EvidenceItem("diff:1", "diff", "d1", "diff one", weight=0.4),
            EvidenceItem("find:1", "finding", "f1", "finding one", weight=0.2),
        ],
    )


@given(
    st.lists(
        st.sampled_from(["mem:1", "diff:1", "find:1", "ghost:1"]),
        min_size=0,
        max_size=12,
    )
)
def test_coverage_counts_unique_valid_ids_only(cited_ids: list[str]):
    bundle = _bundle()
    hypothesis = Hypothesis(
        hypothesis_id="h1",
        claim="c",
        mechanism="m",
        cited_evidence=cited_ids,
    )

    weights = {
        "mem:1": 0.7,
        "diff:1": 0.4,
        "find:1": 0.2,
    }
    expected = sum(weights[eid] for eid in set(cited_ids) if eid in weights)

    assert coverage(hypothesis, bundle) == expected


@given(
    st.dictionaries(
        keys=st.text(min_size=1, max_size=8),
        values=st.one_of(
            st.integers(),
            st.text(max_size=12),
            st.booleans(),
            st.none(),
        ),
        min_size=1,
        max_size=6,
    )
)
def test_finding_hash_is_independent_of_key_insertion_order(finding: dict):
    reordered = dict(reversed(list(finding.items())))

    assert finding_content_hash(finding) == finding_content_hash(reordered)
