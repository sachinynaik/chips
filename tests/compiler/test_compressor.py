from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.compiler.compressor import OllamaCompressor


def _make_compressor() -> OllamaCompressor:
    return OllamaCompressor(base_url="http://localhost:11434", model="qwen2.5-coder:1.5b")


def _mock_ollama_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = {"response": text}
    return resp


def test_hard_constraints_always_present_in_output():
    compressor = _make_compressor()
    with patch("httpx.Client.post", return_value=_mock_ollama_response("summary")):
        result = compressor.compress(
            hard_constraints=["Never drop the users table"],
            soft_items=["Some context"],
            task="do stuff",
        )
    assert "Never drop the users table" in result


def test_compress_calls_ollama_for_soft_items():
    compressor = _make_compressor()
    with patch("httpx.Client.post", return_value=_mock_ollama_response("compressed")) as mock_post:
        compressor.compress(hard_constraints=[], soft_items=["item1", "item2"], task="fix auth")
    mock_post.assert_called_once()


def test_compress_no_soft_items_skips_ollama():
    compressor = _make_compressor()
    with patch("httpx.Client.post") as mock_post:
        result = compressor.compress(hard_constraints=["constraint"], soft_items=[], task="task")
    mock_post.assert_not_called()
    assert "constraint" in result


def test_compress_graceful_on_ollama_error():
    compressor = _make_compressor()
    with patch("httpx.Client.post", side_effect=Exception("connection refused")):
        result = compressor.compress(
            hard_constraints=[],
            soft_items=["fallback context"],
            task="task",
        )
    assert "fallback context" in result


def test_compress_output_contains_both_sections_when_both_present():
    compressor = _make_compressor()
    with patch("httpx.Client.post", return_value=_mock_ollama_response("soft summary")):
        result = compressor.compress(
            hard_constraints=["must not fail"],
            soft_items=["some background"],
            task="fix it",
        )
    assert "must not fail" in result
    assert "soft summary" in result
