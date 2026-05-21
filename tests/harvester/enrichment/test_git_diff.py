from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.git_diff import GitDiffFetcher

SAMPLE_DIFF = """\
commit abc123
Author: Alice
Date: 2026-05-01

    fix auth token

diff --git a/src/auth/token.py b/src/auth/token.py
index 123..456 100644
--- a/src/auth/token.py
+++ b/src/auth/token.py
@@ -10,5 +10,7 @@ def create_auth_token(user_id):
     return jwt.encode(...)
"""

def _fetcher():
    return GitDiffFetcher(repo_path="/fake/repo")

def test_fetch_returns_diff_content():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=SAMPLE_DIFF)
        diff, _ = _fetcher().fetch("abc123")
    assert "fix auth token" in diff

def test_fetch_extracts_hunk_header():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=SAMPLE_DIFF)
        _, headers = _fetcher().fetch("abc123")
    assert any("create_auth_token" in h for h in headers)

def test_fetch_returns_empty_on_nonzero_returncode():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        diff, headers = _fetcher().fetch("bad_sha")
    assert diff == ""
    assert headers == []

def test_fetch_returns_empty_on_exception():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        diff, headers = _fetcher().fetch("abc123")
    assert diff == ""
    assert headers == []

def test_fetch_no_headers_when_no_context():
    raw = "@@ -1,3 +1,4 @@\n+new line\n"
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout=raw)
        _, headers = _fetcher().fetch("abc123")
    assert headers == []
