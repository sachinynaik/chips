from __future__ import annotations

from dataclasses import dataclass
import re


_ISSUE_NUMBER_RE = re.compile(r"#\d+\b")
_ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_REVERT_SHA_RE = re.compile(r"\b(?:This reverts commit|Reverts:)\s+([0-9a-f]{7,40})\b", re.IGNORECASE)
_BUG_RE = re.compile(r"\bbug\b", re.IGNORECASE)
_DEFECT_RE = re.compile(r"\bdefect\b", re.IGNORECASE)
_HOTFIX_RE = re.compile(r"\bhotfix\b", re.IGNORECASE)
_INCIDENT_RE = re.compile(r"\bincident\b", re.IGNORECASE)


@dataclass(frozen=True)
class DefectEvidence:
    issue_refs: list[str]
    revert_of_sha: str | None
    has_bug_keyword: bool
    has_defect_keyword: bool
    has_hotfix_keyword: bool
    has_incident_keyword: bool


def extract_defect_evidence(message: str) -> DefectEvidence:
    issue_refs = sorted(
        set(_ISSUE_NUMBER_RE.findall(message)) | set(_ISSUE_KEY_RE.findall(message))
    )
    revert_match = _REVERT_SHA_RE.search(message)
    return DefectEvidence(
        issue_refs=issue_refs,
        revert_of_sha=revert_match.group(1) if revert_match else None,
        has_bug_keyword=bool(_BUG_RE.search(message)),
        has_defect_keyword=bool(_DEFECT_RE.search(message)),
        has_hotfix_keyword=bool(_HOTFIX_RE.search(message)),
        has_incident_keyword=bool(_INCIDENT_RE.search(message)),
    )
