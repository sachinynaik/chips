from __future__ import annotations
from unittest.mock import MagicMock, patch
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.git_diff import GitDiffFetcher
from chips.harvester.enrichment.complexity import LizardAnalyzer
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer
from chips.harvester.enrichment.semble import SembleEnricher
from chips.harvester.enrichment.graphify import GraphifyEnricher
from chips.harvester.enrichment.refactoring import RefactoringDetector
from chips.harvester.enrichment.joern import JoernAnalyzer
from chips.harvester.enrichment.defect import DefectPredictor
from chips.harvester.enrichment.scope_memories import ScopeMemoryFetcher
from chips.harvester.enrichment.cochange import CochangeFetcher
from chips.harvester.git_reader import CommitRecord

def _commit():
    return CommitRecord(
        sha="abc123",
        author="Alice",
        committed_at="2026-05-01T00:00:00+00:00",
        message="fix auth crash",
        files_changed=["src/auth/token.py"],
    )

def _pipeline(conn_factory=None):
    git_diff = MagicMock(spec=GitDiffFetcher)
    git_diff.fetch.return_value = ("diff content", ["def create_auth_token"])
    complexity = MagicMock(spec=LizardAnalyzer)
    complexity.analyze.return_value = []
    semgrep = MagicMock(spec=SemgrepAnalyzer)
    semgrep.analyze.return_value = []
    semble = MagicMock(spec=SembleEnricher)
    semble.enrich.return_value = []
    graphify = MagicMock(spec=GraphifyEnricher)
    graphify.enrich.return_value = "auth cluster"
    refactoring = RefactoringDetector()
    joern = JoernAnalyzer()
    defect = DefectPredictor()
    scope_mem = MagicMock(spec=ScopeMemoryFetcher)
    scope_mem.fetch.return_value = []
    cochange = MagicMock(spec=CochangeFetcher)
    cochange.fetch.return_value = []
    return EnrichmentPipeline(
        git_diff=git_diff,
        complexity=complexity,
        semgrep=semgrep,
        semble=semble,
        graphify=graphify,
        refactoring=refactoring,
        joern=joern,
        defect=defect,
        scope_memories=scope_mem,
        cochange=cochange,
        conn_factory=conn_factory,
    )

def test_pipeline_returns_enrichment_result():
    from chips.harvester.enrichment.models import EnrichmentResult
    result = _pipeline().enrich(_commit(), "auth")
    assert isinstance(result, EnrichmentResult)

def test_pipeline_diff_content_populated():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.diff_content == "diff content"

def test_pipeline_hunk_headers_populated():
    result = _pipeline().enrich(_commit(), "auth")
    assert "def create_auth_token" in result.hunk_headers

def test_pipeline_community_context_populated():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.community_context == "auth cluster"

def test_pipeline_defect_risk_is_stub():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.defect_risk["risk_score"] is None

def test_pipeline_refactoring_type_is_none():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.refactoring_type is None

def test_pipeline_fetches_scope_memories_when_conn_factory_provided():
    conn = MagicMock()
    conn.execute.return_value.fetchall.return_value = []
    pipeline = _pipeline(conn_factory=lambda: conn)
    pipeline.enrich(_commit(), "auth")
    pipeline._scope_memories.fetch.assert_called_once()

def test_pipeline_skips_db_when_no_conn_factory():
    pipeline = _pipeline(conn_factory=None)
    result = pipeline.enrich(_commit(), "auth")
    assert result.scope_memories == []
    assert result.cochange_pairs == []
