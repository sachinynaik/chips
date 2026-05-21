from __future__ import annotations

from chips.harvester.enrichment.cochange import CochangeFetcher
from chips.harvester.enrichment.code_embed import CodeEmbedder
from chips.harvester.enrichment.complexity import LizardAnalyzer
from chips.harvester.enrichment.defect import DefectPredictor
from chips.harvester.enrichment.git_diff import GitDiffFetcher
from chips.harvester.enrichment.graphify import GraphifyEnricher
from chips.harvester.enrichment.joern import JoernAnalyzer
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.refactoring import RefactoringDetector
from chips.harvester.enrichment.scope_memories import ScopeMemoryFetcher
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer
from chips.harvester.enrichment.semble import SembleEnricher
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
) -> tuple[EnrichmentPipeline, DiffSummarizer]:
    """Assemble a fully-wired EnrichmentPipeline and DiffSummarizer.

    All enrichers are included; Layer 4 stubs (Joern, RefactoringMiner,
    DefectPredictor) degrade gracefully until JVM backends are available.

    Args:
        repo_path: Absolute path to the git repository root.
        ollama_url: Base URL of the Ollama server.
        conn_factory: Zero-arg callable returning a psycopg Connection.
        ollama_model: Ollama model for code embeddings (nomic-embed-code).
        summarizer_model: Ollama model for lesson summarisation.
        type_checker_backend: Type checker to use ("pyrefly").
        pyrefly_config_path: Optional path to pyrefly.toml.

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
