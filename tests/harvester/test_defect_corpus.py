from __future__ import annotations

import tempfile
from pathlib import Path

from chips.harvester.defect_corpus import (
    estimate_defect_density,
    extract_defect_evidence,
    high_precision_defect_sql,
    is_high_precision_defect,
)


def test_extract_defect_evidence_collects_issue_refs_and_keywords():
    evidence = extract_defect_evidence(
        "fix(auth): resolve incident in login flow ABC-123 closes #45 hotfix"
    )

    assert evidence.issue_refs == ["#45", "ABC-123"]
    assert evidence.has_bug_keyword is False
    assert evidence.has_defect_keyword is False
    assert evidence.has_hotfix_keyword is True
    assert evidence.has_incident_keyword is True
    assert evidence.revert_of_sha is None


def test_extract_defect_evidence_detects_bug_and_defect_words_case_insensitively():
    evidence = extract_defect_evidence("BUG: Defect in retry loop")

    assert evidence.issue_refs == []
    assert evidence.has_bug_keyword is True
    assert evidence.has_defect_keyword is True


def test_extract_defect_evidence_extracts_reverted_sha():
    evidence = extract_defect_evidence(
        'Revert "break auth flow"\n\nThis reverts commit 0123456789abcdef0123456789abcdef01234567.'
    )

    assert evidence.revert_of_sha == "0123456789abcdef0123456789abcdef01234567"


def test_extract_defect_evidence_deduplicates_and_sorts_issue_refs():
    evidence = extract_defect_evidence("refs #77 and ABC-3 and #77 again with ABC-3")

    assert evidence.issue_refs == ["#77", "ABC-3"]


def test_high_precision_defect_requires_bug_or_defect_for_issue_only_case():
    evidence = extract_defect_evidence("refs ABC-123 closes #77")

    assert is_high_precision_defect(evidence) is False


def test_high_precision_defect_accepts_issue_linked_bug_fix():
    evidence = extract_defect_evidence("bugfix(auth): closes #77 for ABC-123")

    assert is_high_precision_defect(evidence) is True


def test_high_precision_defect_accepts_revert_without_other_markers():
    evidence = extract_defect_evidence(
        'Revert "break auth flow"\n\nThis reverts commit 0123456789abcdef0123456789abcdef01234567.'
    )

    assert is_high_precision_defect(evidence) is True


def test_high_precision_defect_sql_uses_issue_and_keyword_conjunction():
    sql = high_precision_defect_sql("d")

    assert "cardinality(d.issue_refs) > 0" in sql
    assert "d.has_bug_keyword = TRUE" in sql
    assert "d.has_defect_keyword = TRUE" in sql
    assert "d.revert_of_sha IS NOT NULL" in sql
    assert "d.has_hotfix_keyword = TRUE" in sql
    assert "d.has_incident_keyword = TRUE" in sql


def _local_tmp_path() -> Path:
    root = Path(".pytest_tmp")
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(dir=root))


def test_estimate_defect_density_returns_none_without_existing_files():
    tmp_path = _local_tmp_path()
    density, basis_nloc = estimate_defect_density(
        ["src/missing.py"],
        defect_count=2,
        repo_root=tmp_path,
    )

    assert density is None
    assert basis_nloc == 0


def test_estimate_defect_density_is_per_kloc_of_nonblank_lines():
    tmp_path = _local_tmp_path()
    src = tmp_path / "src"
    src.mkdir()
    target = src / "auth.py"
    target.write_text("line1\n\nline2\nline3\n", encoding="utf-8")

    density, basis_nloc = estimate_defect_density(
        ["src/auth.py"],
        defect_count=2,
        repo_root=tmp_path,
    )

    assert basis_nloc == 3
    assert density == round((2 / 3) * 1000, 4)
