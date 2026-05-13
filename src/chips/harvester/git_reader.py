from __future__ import annotations
from dataclasses import dataclass, field
import math


@dataclass
class CommitRecord:
    sha: str
    author: str
    committed_at: str
    message: str
    files_changed: list[str] = field(default_factory=list)


@dataclass
class CochangePair:
    file_a: str
    file_b: str
    frequency: int


@dataclass
class FileSignal:
    file_path: str
    churn_count: int
    churn_score: float


_LOG_FORMAT = "%H|%an|%aI|%s"
_COMMIT_SEP = "==="
_FILE_SEP = "---"


class GitReader:
    def __init__(self, repo_path: str) -> None:
        import git
        self._repo = git.Repo(repo_path)

    def commits_since(self, since_sha: str | None = None, limit: int = 100) -> list[CommitRecord]:
        args = [f"--max-count={limit}", f"--format={_LOG_FORMAT}", "--name-only"]
        if since_sha:
            args.append(f"{since_sha}..HEAD")
        raw = self._repo.git.log(*args)
        return self._parse_log(raw)

    def _parse_log(self, raw: str) -> list[CommitRecord]:
        commits: list[CommitRecord] = []
        for block in raw.strip().split(_COMMIT_SEP):
            block = block.strip()
            if not block:
                continue
            lines = block.splitlines()
            header = lines[0].strip()
            if not header:
                continue
            parts = header.split("|", 3)
            if len(parts) < 4:
                continue
            sha, author, committed_at, message = parts

            files: list[str] = []
            in_files = False
            for line in lines[1:]:
                line = line.strip()
                if line == _FILE_SEP:
                    in_files = True
                    continue
                if in_files and line:
                    files.append(line)

            commits.append(CommitRecord(
                sha=sha.strip(),
                author=author.strip(),
                committed_at=committed_at.strip(),
                message=message.strip(),
                files_changed=files,
            ))
        return commits

    def _compute_cochange_pairs(self, commits: list[CommitRecord]) -> list[tuple[str, str, int]]:
        freq: dict[tuple[str, str], int] = {}
        for commit in commits:
            files = sorted(commit.files_changed)
            for i, fa in enumerate(files):
                for fb in files[i + 1:]:
                    key = (fa, fb)
                    freq[key] = freq.get(key, 0) + 1
        return [(a, b, f) for (a, b), f in freq.items()]

    def _compute_file_signals(self, commits: list[CommitRecord]) -> list[FileSignal]:
        churn: dict[str, int] = {}
        for commit in commits:
            for f in commit.files_changed:
                churn[f] = churn.get(f, 0) + 1
        max_count = max(churn.values(), default=1)
        return [
            FileSignal(
                file_path=fp,
                churn_count=count,
                churn_score=math.log(1 + count) / math.log(1 + max_count),
            )
            for fp, count in churn.items()
        ]
