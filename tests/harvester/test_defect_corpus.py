from __future__ import annotations

from chips.harvester.defect_corpus import extract_defect_evidence


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
