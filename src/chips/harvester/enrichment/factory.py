from __future__ import annotations

from chips.harvester.enrichment.api_surface import GriffeAnalyzer
from chips.harvester.enrichment.architecture import ImportLinterAnalyzer
from chips.harvester.enrichment.clones import JscpdAnalyzer
from chips.harvester.enrichment.cochange import CochangeFetcher
from chips.harvester.enrichment.code_embed import CodeEmbedder
from chips.harvester.enrichment.complexity import LizardAnalyzer
from chips.harvester.enrichment.coverage_reader import CoverageReader
from chips.harvester.enrichment.dead_code import VultureAnalyzer
from chips.harvester.enrichment.defect import DefectPredictor
from chips.harvester.enrichment.git_diff import GitDiffFetcher
from chips.harvester.enrichment.graphify import GraphifyEnricher
from chips.harvester.enrichment.joern import JoernAnalyzer
from chips.harvester.enrichment.ownership import CodeownersParser
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.refactoring import RefactoringDetector
from chips.harvester.enrichment.scope_memories import ScopeMemoryFetcher
from chips.harvester.enrichment.security import BanditAnalyzer
from chips.harvester.enrichment.semble import SembleEnricher
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer
from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.summarizer import DiffSummarizer


def create_enrichment_pipeline(
    repo_path: str,
    ollama_url: str,
    conn_factory,
    ollama_model: str = "nomic-embed-code",
    summarizer_model: str = "qwen2.5-coder:7b",
    type_checker_backend: str = "pyrefly",
    pyrefly_config_path: str | None = None,
    bandit_severity_threshold: str = "LOW",
    vulture_min_confidence: int = 60,
    jscpd_min_lines: int = 5,
    jscpd_min_tokens: int = 50,
) -> tuple[EnrichmentPipeline, DiffSummarizer]:
    """Assemble a fully-wired EnrichmentPipeline and DiffSummarizer.

    All enrichers are included. Optional-dep enrichers (griffe, vulture,
    bandit, jscpd) degrade gracefully to empty results when the tool is
    not installed. coverage_reader returns nothing if no .coverage artifact
    exists. architecture returns nothing if no .importlinter config exists.
    ownership returns nothing if no CODEOWNERS file exists.

    Args:
        repo_path: Absolute path to the git repository root.
        ollama_url: Base URL of the Ollama server.
        conn_factory: Zero-arg callable returning a psycopg Connection.
        ollama_model: Ollama model for code embeddings (nomic-embed-code).
        summarizer_model: Ollama model for lesson summarisation.
        type_checker_backend: Type checker to use ("pyrefly").
        pyrefly_config_path: Optional path to pyrefly.toml.
        bandit_severity_threshold: Minimum severity for bandit findings ("LOW"|"MEDIUM"|"HIGH").
        vulture_min_confidence: Minimum confidence for vulture dead-code findings (0-100).
        jscpd_min_lines: Minimum duplicated lines for jscpd to report a clone.
        jscpd_min_tokens: Minimum duplicated tokens for jscpd to report a clone.

    Returns:
        (pipeline, summarizer) — pass both to CommitMemoryExtractor.
    """
    pipeline = EnrichmentPipeline(
        git_diff=GitDiffFetcher(repo_path=repo_path),
        complexity=LizardAnalyzer(),
        semgrep=SemgrepAnalyzer(),
        semble=SembleEnricher(repo_path=repo_path),
        graphify=GraphifyEnricher(repo_path=repo_path),
        refactoring=RefactoringDetector(),
        joern=JoernAnalyzer(),
        defect=DefectPredictor(),
        scope_memories=ScopeMemoryFetcher(),
        cochange=CochangeFetcher(),
        code_embedder=CodeEmbedder(base_url=ollama_url, model=ollama_model),
        type_checker=TypeCheckerAnalyzer(
            backend=type_checker_backend,
            repo_path=repo_path,
            config_path=pyrefly_config_path,
        ),
        api_surface=GriffeAnalyzer(),
        dead_code=VultureAnalyzer(min_confidence=vulture_min_confidence),
        security=BanditAnalyzer(severity_threshold=bandit_severity_threshold),
        coverage_reader=CoverageReader(repo_path=repo_path),
        architecture=ImportLinterAnalyzer(repo_path=repo_path),
        clones=JscpdAnalyzer(
            repo_path=repo_path,
            min_lines=jscpd_min_lines,
            min_tokens=jscpd_min_tokens,
        ),
        ownership=CodeownersParser(repo_path=repo_path),
        conn_factory=conn_factory,
    )
    summarizer = DiffSummarizer(base_url=ollama_url, model=summarizer_model)
    return pipeline, summarizer


def create_enriched_extractor(
    repo_path: str,
    ollama_url: str,
    conn_factory,
    **kwargs,
) -> CommitMemoryExtractor:
    """Convenience wrapper: returns a CommitMemoryExtractor wired with all enrichers.

    Usage:
        extractor = create_enriched_extractor(
            repo_path=".",
            ollama_url="http://localhost:11434",
            conn_factory=lambda: psycopg.connect(os.environ["CHIPS_DB_URL"]),
        )
        daemon = HarvesterDaemon(conn=conn, embedder=embedder, repo_path=".", extractor=extractor)
    """
    pipeline, summarizer = create_enrichment_pipeline(
        repo_path=repo_path,
        ollama_url=ollama_url,
        conn_factory=conn_factory,
        **kwargs,
    )
    return CommitMemoryExtractor(enricher=pipeline, summarizer=summarizer)
