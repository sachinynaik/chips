from __future__ import annotations
from unittest.mock import patch, MagicMock
from chips.harvester.enrichment.code_embed import CodeEmbedder

def _embedder():
    return CodeEmbedder(base_url="http://localhost:11434")

def test_find_similar_commits_calls_ollama():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embeddings": [[0.1] * 768]}
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = []
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        _embedder().find_similar_commits("diff content", mock_conn)
    mock_client_cls.return_value.__enter__.return_value.post.assert_called_once()

def test_find_similar_commits_returns_results():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"embeddings": [[0.1] * 768]}
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = [
        ("fixed auth bug", "auth", 0.92)
    ]
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.return_value = mock_resp
        result = _embedder().find_similar_commits("diff content", mock_conn)
    assert len(result) == 1
    assert result[0]["content"] == "fixed auth bug"
    assert result[0]["similarity"] == 0.92

def test_find_similar_commits_returns_empty_on_http_error():
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.post.side_effect = Exception("timeout")
        result = _embedder().find_similar_commits("diff content", MagicMock())
    assert result == []

def test_find_similar_commits_returns_empty_for_empty_diff():
    result = _embedder().find_similar_commits("", MagicMock())
    assert result == []
