from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.graphify import GraphifyEnricher

def _enr():
    return GraphifyEnricher(repo_path="/fake/repo")

def test_enrich_returns_community_context():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="auth community: token, session, login")
        result = _enr().enrich("auth")
    assert "auth" in result

def test_enrich_returns_none_when_graphify_not_found():
    with patch("subprocess.run", side_effect=FileNotFoundError):
        result = _enr().enrich("auth")
    assert result is None

def test_enrich_returns_none_for_empty_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="   ")
        result = _enr().enrich("auth")
    assert result is None

def test_enrich_returns_none_for_general_scope():
    result = _enr().enrich("general")
    assert result is None
