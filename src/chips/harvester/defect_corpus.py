from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


_ISSUE_NUMBER_RE = re.compile(r"#\d+\b")
_ISSUE_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
_REVERT_SHA_RE = re.compile(r"\b(?:This reverts commit|Reverts:)\s+([0-9a-f]{7,40})\b", re.IGNORECASE)
_BUG_RE = re.compile(r"\bbug(?:fix)?\b", re.IGNORECASE)
_DEFECT_RE = re.compile(r"\bdefect(?:fix)?\b", re.IGNORECASE)
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


def is_high_precision_defect(evidence: DefectEvidence) -> bool:
    issue_linked_bugfix = bool(evidence.issue_refs) and (
        evidence.has_bug_keyword or evidence.has_defect_keyword
    )
    return (
        issue_linked_bugfix
        or evidence.revert_of_sha is not None
        or evidence.has_hotfix_keyword
        or evidence.has_incident_keyword
    )


def high_precision_defect_sql(alias: str = "d") -> str:
    return (
        f"((cardinality({alias}.issue_refs) > 0 "
        f"AND ({alias}.has_bug_keyword = TRUE OR {alias}.has_defect_keyword = TRUE)) "
        f"OR {alias}.revert_of_sha IS NOT NULL "
        f"OR {alias}.has_hotfix_keyword = TRUE "
        f"OR {alias}.has_incident_keyword = TRUE)"
    )


def estimate_defect_density(
    file_paths: list[str],
    *,
    defect_count: int,
    repo_root: str | Path = ".",
) -> tuple[float | None, int]:
    if defect_count <= 0:
        return None, 0
    root = Path(repo_root)
    total_nloc = 0
    for file_path in file_paths:
        path = root / file_path
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        total_nloc += sum(1 for line in text.splitlines() if line.strip())
    if total_nloc <= 0:
        return None, 0
    density = round((defect_count / total_nloc) * 1000, 4)
    return density, total_nloc
