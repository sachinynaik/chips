from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.semble import SembleEnricher

def _enr():
    return SembleEnricher(repo_path="/fake/repo")

SAMPLE_DIFF = """\
+++ b/src/auth/token.py
@@ -10,5 +10,7 @@ def create_auth_token(user_id):
"""

def test_enrich_returns_related_symbols():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="src/auth/session.py:45:validate_session")
        result = _enr().enrich(["src/auth/token.py"], SAMPLE_DIFF)
    assert len(result) == 1
    assert "src/auth/token.py" == result[0]["source_file"]

def test_enrich_returns_empty_on_exception():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _enr().enrich(["src/auth/token.py"])
    assert result == []

def test_enrich_limits_to_three_files():
    files = [f"src/mod{i}.py" for i in range(5)]
    calls = []
    def fake_run(*args, **kwargs):
        calls.append(args)
        return MagicMock(returncode=0, stdout="")
    with patch("subprocess.run", side_effect=fake_run):
        _enr().enrich(files)
    assert len(calls) == 3

def test_extract_changed_lines_parses_diff():
    diff = "+++ b/src/auth/token.py\n@@ -10,5 +10,7 @@ def fn():\n"
    enr = SembleEnricher("/repo")
    mapping = enr._extract_changed_lines(diff)
    assert mapping.get("src/auth/token.py") == 10


def test_last_status_defaults_to_skipped():
    assert _enr().last_status == "skipped"


def test_last_status_ok_after_related_results():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="src/auth/session.py:45:validate_session")
        enr = _enr()
        enr.enrich(["src/auth/token.py"], SAMPLE_DIFF)
    assert enr.last_status == "ok"


def test_last_status_not_installed_on_missing_binary():
    enr = _enr()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        enr.enrich(["src/auth/token.py"])
    assert enr.last_status == "not_installed"


def test_last_status_failed_on_generic_error():
    enr = _enr()
    with patch("subprocess.run", side_effect=RuntimeError("boom")):
        enr.enrich(["src/auth/token.py"])
    assert enr.last_status == "failed"
