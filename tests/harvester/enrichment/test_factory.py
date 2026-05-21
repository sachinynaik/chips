from __future__ import annotations

from unittest.mock import MagicMock

from chips.harvester.enrichment.factory import create_enriched_extractor, create_enrichment_pipeline
from chips.harvester.enrichment.code_embed import CodeEmbedder
from chips.harvester.enrichment.complexity import LizardAnalyzer
from chips.harvester.enrichment.git_diff import GitDiffFetcher
from chips.harvester.enrichment.graphify import GraphifyEnricher
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer
from chips.harvester.enrichment.semble import SembleEnricher
from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.summarizer import DiffSummarizer


def _conn_factory():
    return MagicMock()


def _args(**overrides):
    base = dict(
        repo_path="/fake/repo",
        ollama_url="http://localhost:11434",
        conn_factory=_conn_factory,
    )
    base.update(overrides)
    return base


# ── Return types ──────────────────────────────────────────────────────────────

def test_returns_pipeline_and_summarizer():
    pipeline, summarizer = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline, EnrichmentPipeline)
    assert isinstance(summarizer, DiffSummarizer)


# ── repo_path forwarding ──────────────────────────────────────────────────────

def test_git_diff_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._git_diff, GitDiffFetcher)
    assert pipeline._git_diff._repo_path == "/fake/repo"


def test_semble_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._semble, SembleEnricher)
    assert pipeline._semble._repo_path == "/fake/repo"


def test_graphify_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._graphify, GraphifyEnricher)
    assert pipeline._graphify._repo_path == "/fake/repo"


def test_pyrefly_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._type_checker._analyzer._repo_path == "/fake/repo"


# ── ollama_url forwarding ─────────────────────────────────────────────────────

def test_code_embedder_uses_ollama_url():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._code_embedder, CodeEmbedder)
    assert pipeline._code_embedder._base_url == "http://localhost:11434"


def test_summarizer_uses_ollama_url():
    _, summarizer = create_enrichment_pipeline(**_args())
    assert summarizer._base_url == "http://localhost:11434"


# ── model params ─────────────────────────────────────────────────────────────

def test_code_embedder_default_model():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._code_embedder._model == "nomic-embed-code"


def test_code_embedder_model_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(ollama_model="all-minilm"))
    assert pipeline._code_embedder._model == "all-minilm"


def test_summarizer_default_model():
    _, summarizer = create_enrichment_pipeline(**_args())
    assert summarizer._model == "qwen2.5-coder:7b"


def test_summarizer_model_configurable():
    _, summarizer = create_enrichment_pipeline(**_args(summarizer_model="llama3.2:3b"))
    assert summarizer._model == "llama3.2:3b"


# ── type checker ──────────────────────────────────────────────────────────────

def test_type_checker_default_backend_is_pyrefly():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._type_checker, TypeCheckerAnalyzer)
    assert pipeline._type_checker.backend == "pyrefly"


def test_type_checker_backend_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(type_checker_backend="pyrefly"))
    assert pipeline._type_checker.backend == "pyrefly"


def test_pyrefly_config_path_forwarded():
    pipeline, _ = create_enrichment_pipeline(**_args(pyrefly_config_path="/proj/pyrefly.toml"))
    assert pipeline._type_checker._analyzer._config_path == "/proj/pyrefly.toml"


def test_pyrefly_config_path_none_by_default():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._type_checker._analyzer._config_path is None


# ── Layer 1 analyzers present ─────────────────────────────────────────────────

def test_pipeline_has_complexity_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._complexity, LizardAnalyzer)


def test_pipeline_has_semgrep_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._semgrep, SemgrepAnalyzer)


# ── conn_factory ──────────────────────────────────────────────────────────────

def test_conn_factory_stored_in_pipeline():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._conn_factory is _conn_factory


# ── create_enriched_extractor ─────────────────────────────────────────────────

def test_create_enriched_extractor_returns_extractor():
    extractor = create_enriched_extractor(**_args())
    assert isinstance(extractor, CommitMemoryExtractor)


def test_create_enriched_extractor_has_enricher():
    extractor = create_enriched_extractor(**_args())
    assert isinstance(extractor._enricher, EnrichmentPipeline)


def test_create_enriched_extractor_has_summarizer():
    extractor = create_enriched_extractor(**_args())
    assert isinstance(extractor._summarizer, DiffSummarizer)


def test_create_enriched_extractor_forwards_kwargs():
    extractor = create_enriched_extractor(**_args(summarizer_model="phi3:mini"))
    assert extractor._summarizer._model == "phi3:mini"
