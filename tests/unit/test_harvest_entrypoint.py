from __future__ import annotations

from unittest.mock import MagicMock, patch

from chips.ops.harvest import build_daemon


def test_build_daemon_wires_repo_path_and_poll_interval():
    with patch("chips.ops.harvest.psycopg.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        daemon = build_daemon(
            database_url="postgresql://postgres:postgres@127.0.0.1:5498/postgres",
            repo_path="/repos/chips",
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model="nomic-embed-text",
            poll_interval=45,
        )
    mock_connect.assert_called_once_with(
        "postgresql://postgres:postgres@127.0.0.1:5498/postgres"
    )
    assert daemon._repo_path == "/repos/chips"
    assert daemon._poll_interval == 45


def test_build_daemon_wires_embedder_base_url_and_model():
    with patch("chips.ops.harvest.psycopg.connect") as mock_connect:
        mock_connect.return_value = MagicMock()
        daemon = build_daemon(
            database_url="postgresql://postgres:postgres@127.0.0.1:5498/postgres",
            repo_path="/repos/chips",
            ollama_base_url="http://127.0.0.1:11434",
            ollama_model="nomic-embed-text",
        )
    assert daemon._embedder._base_url == "http://127.0.0.1:11434"
    assert daemon._embedder._model == "nomic-embed-text"
