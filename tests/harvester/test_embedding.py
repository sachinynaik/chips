"""Ollama embedding client unit tests — no network required."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from chips.harvester.embedding import OllamaEmbedder


def _mock_response(embeddings: list[list[float]]) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"embeddings": embeddings}
    return resp


def test_embed_returns_list_of_floats():
    with patch("httpx.Client.post", return_value=_mock_response([[0.1, 0.2, 0.3]])):
        embedder = OllamaEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        result = embedder.embed("hello world")
    assert isinstance(result, list)
    assert all(isinstance(x, float) for x in result)


def test_embed_sends_correct_payload():
    with patch("httpx.Client.post", return_value=_mock_response([[0.1, 0.2, 0.3]])) as mock_post:
        embedder = OllamaEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        embedder.embed("test input")
    _, kwargs = mock_post.call_args
    payload = kwargs["json"]
    assert payload["model"] == "nomic-embed-text"
    assert payload["input"] == "test input"


def test_embed_raises_on_http_error():
    err_resp = MagicMock()
    err_resp.status_code = 500
    with patch(
        "httpx.Client.post",
        side_effect=httpx.HTTPStatusError("server error", request=MagicMock(), response=err_resp),
    ):
        embedder = OllamaEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        with pytest.raises(Exception):
            embedder.embed("test")


def test_embed_batch_returns_multiple_vectors():
    batch = [[0.1, 0.2], [0.3, 0.4]]
    with patch("httpx.Client.post", return_value=_mock_response(batch)):
        embedder = OllamaEmbedder(base_url="http://localhost:11434", model="nomic-embed-text")
        results = embedder.embed_batch(["hello", "world"])
    assert len(results) == 2
    assert results[0] == pytest.approx([0.1, 0.2])
    assert results[1] == pytest.approx([0.3, 0.4])
