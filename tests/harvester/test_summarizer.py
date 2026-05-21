from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.summarizer import DiffSummarizer
from chips.harvester.enrichment.models import EnrichmentResult
from chips.harvester.git_reader import CommitRecord

def _commit():
    return CommitRecord(
        sha="abc123",
        author="Alice",
        committed_at="2026-05-01T00:00:00+00:00",
        message="fix auth crash",
        files_changed=["src/auth/token.py"],
    )

def _enrichment(**kwargs):
    return EnrichmentResult(**kwargs)

def _summarizer():
    return DiffSummarizer(base_url="http://localhost:11434", model="qwen2.5-coder:7b")

def test_summarize_calls_ollama():
    with patch("httpx.Client") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "lesson text"}
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        result = _summarizer().summarize(_commit(), _enrichment())
    assert result == "lesson text"
    mock_client_cls.return_value.__enter__.return_value.post.assert_called_once()

def test_summarize_falls_back_to_commit_message_on_error():
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("timeout")
        result = _summarizer().summarize(_commit(), _enrichment())
    assert result == "fix auth crash"

def test_summarize_includes_hunk_headers_in_prompt():
    enrichment = _enrichment(hunk_headers=["def create_auth_token"])
    with patch("httpx.Client") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "lesson"}
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        _summarizer().summarize(_commit(), enrichment)
    call_args = mock_client_cls.return_value.__enter__.return_value.post.call_args
    prompt = call_args[1]["json"]["prompt"]
    assert "create_auth_token" in prompt

def test_summarize_includes_semgrep_findings_in_prompt():
    enrichment = _enrichment(semgrep_findings=[{"check_id": "python.security.sql-injection"}])
    with patch("httpx.Client") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "lesson"}
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        _summarizer().summarize(_commit(), enrichment)
    call_args = mock_client_cls.return_value.__enter__.return_value.post.call_args
    prompt = call_args[1]["json"]["prompt"]
    assert "sql-injection" in prompt

def test_summarize_includes_scope_memories_in_prompt():
    enrichment = _enrichment(scope_memories=[{"content": "never bypass token validation", "type": "invariant", "tags": []}])
    with patch("httpx.Client") as mock_client_cls:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "lesson"}
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        _summarizer().summarize(_commit(), enrichment)
    call_args = mock_client_cls.return_value.__enter__.return_value.post.call_args
    prompt = call_args[1]["json"]["prompt"]
    assert "token validation" in prompt

def test_build_prompt_includes_complexity_when_high():
    enrichment = _enrichment(complexity_metrics=[
        {"file": "src/auth.py", "function": "process_payment", "cyclomatic_complexity": 15, "nloc": 80}
    ])
    summarizer = DiffSummarizer("http://localhost:11434", "qwen2.5-coder")
    prompt = summarizer._build_prompt(_commit(), enrichment)
    assert "process_payment" in prompt
