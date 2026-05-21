from __future__ import annotations

from unittest.mock import MagicMock

from chips.harvester.enrichment.api_surface import GriffeAnalyzer
from chips.harvester.enrichment.architecture import ImportLinterAnalyzer
from chips.harvester.enrichment.clones import JscpdAnalyzer
from chips.harvester.enrichment.code_embed import CodeEmbedder
from chips.harvester.enrichment.complexity import LizardAnalyzer
from chips.harvester.enrichment.coverage_reader import CoverageReader
from chips.harvester.enrichment.dead_code import VultureAnalyzer
from chips.harvester.enrichment.factory import create_enriched_extractor, create_enrichment_pipeline
from chips.harvester.enrichment.git_diff import GitDiffFetcher
from chips.harvester.enrichment.graphify import GraphifyEnricher
from chips.harvester.enrichment.ownership import CodeownersParser
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.security import BanditAnalyzer
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


# ── New enrichers wired by factory ────────────────────────────────────────────

def test_pipeline_has_griffe_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._api_surface, GriffeAnalyzer)


def test_pipeline_has_vulture_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._dead_code, VultureAnalyzer)


def test_pipeline_has_bandit_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._security, BanditAnalyzer)


def test_pipeline_has_coverage_reader():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._coverage_reader, CoverageReader)


def test_pipeline_has_import_linter():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._architecture, ImportLinterAnalyzer)


def test_pipeline_has_jscpd_analyzer():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._clones, JscpdAnalyzer)


def test_pipeline_has_codeowners_parser():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert isinstance(pipeline._ownership, CodeownersParser)


def test_bandit_severity_threshold_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(bandit_severity_threshold="HIGH"))
    assert pipeline._security._threshold == "HIGH"


def test_vulture_min_confidence_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(vulture_min_confidence=80))
    assert pipeline._dead_code._min_confidence == 80


def test_jscpd_min_lines_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(jscpd_min_lines=10))
    assert pipeline._clones._min_lines == 10


def test_jscpd_min_tokens_configurable():
    pipeline, _ = create_enrichment_pipeline(**_args(jscpd_min_tokens=100))
    assert pipeline._clones._min_tokens == 100


def test_coverage_reader_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._coverage_reader._repo_path == "/fake/repo"


def test_architecture_uses_repo_path():
    from pathlib import Path
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._architecture._repo_path == Path("/fake/repo")


def test_jscpd_uses_repo_path():
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._clones._repo_path == "/fake/repo"


def test_codeowners_uses_repo_path():
    from pathlib import Path
    pipeline, _ = create_enrichment_pipeline(**_args())
    assert pipeline._ownership._repo_path == Path("/fake/repo")
