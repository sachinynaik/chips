"""RED: MCP /git/recent tool tests."""
from chips.harvester.git_reader import CommitRecord
from chips.harvester.ingestion import GitIngestion
from chips.mcp.tools.git import get_recent_commits


def _commit(sha: str, files: list[str], msg: str = "msg") -> CommitRecord:
    return CommitRecord(
        sha=sha,
        author="dev",
        committed_at="2026-05-10T12:00:00+00:00",
        message=msg,
        files_changed=files,
    )


def test_get_recent_commits_returns_list(conn):
    ingestion = GitIngestion(conn)
    ingestion.ingest_commits([_commit("r001", ["src/a.py"])])

    results = get_recent_commits(conn=conn, limit=10)
    assert isinstance(results, list)
    assert len(results) >= 1


def test_get_recent_commits_includes_sha_and_files(conn):
    ingestion = GitIngestion(conn)
    ingestion.ingest_commits([_commit("r002", ["src/auth.py", "src/test_auth.py"])])

    results = get_recent_commits(conn=conn, limit=10)
    shas = [r["sha"] for r in results]
    assert "r002" in shas

    commit = next(r for r in results if r["sha"] == "r002")
    assert "src/auth.py" in commit["files_changed"]


def test_get_recent_commits_includes_cochange(conn):
    ingestion = GitIngestion(conn)
    ingestion.ingest_commits([_commit("r003", ["src/x.py", "src/y.py"])])

    results = get_recent_commits(conn=conn, limit=10)
    commit = next(r for r in results if r["sha"] == "r003")
    assert "cochange_pairs" in commit


def test_get_recent_commits_limit_respected(conn):
    ingestion = GitIngestion(conn)
    for i in range(10):
        ingestion.ingest_commits([_commit(f"lim{i:03d}", ["src/f.py"])])

    results = get_recent_commits(conn=conn, limit=3)
    assert len(results) <= 3
