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
    complexity.last_status = "ok"
    semgrep = MagicMock(spec=SemgrepAnalyzer)
    semgrep.analyze.return_value = []
    semgrep.last_status = "ok"
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
    assert result.defect_risk["history_count"] == 0

def test_pipeline_refactoring_type_is_none():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.refactoring_type is None

def test_pipeline_fetches_scope_memories_when_conn_factory_provided():
    conn = MagicMock()
    count_cursor = MagicMock()
    count_cursor.fetchone.return_value = (0,)
    recent_cursor = MagicMock()
    recent_cursor.fetchall.return_value = []
    conn.execute.side_effect = [count_cursor, recent_cursor]
    pipeline = _pipeline(conn_factory=lambda: conn)
    pipeline.enrich(_commit(), "auth")
    pipeline._scope_memories.fetch.assert_called_once()

def test_pipeline_skips_db_when_no_conn_factory():
    pipeline = _pipeline(conn_factory=None)
    result = pipeline.enrich(_commit(), "auth")
    assert result.scope_memories == []
    assert result.cochange_pairs == []
    assert result.defect_risk["reason"] == "insufficient_history"


def test_pipeline_defect_risk_uses_db_history_when_conn_factory_provided():
    conn = MagicMock()

    def execute(sql, params):
        cursor = MagicMock()
        if "COUNT(DISTINCT g.sha)" in sql:
            cursor.fetchone.return_value = (2,)
        elif "FROM cortex_git_commits" in sql and "cortex_defect_corpus" in sql:
            cursor.fetchall.return_value = [("abc111",), ("abc222",)]
        else:
            cursor.fetchall.return_value = []
        return cursor

    conn.execute.side_effect = execute
    pipeline = _pipeline(conn_factory=lambda: conn)

    result = pipeline.enrich(_commit(), "auth")

    assert result.defect_risk["history_count"] == 2
    assert result.defect_risk["matched_commits"] == ["abc111", "abc222"]


# ── TypeChecker integration ───────────────────────────────────────────────────

def test_pipeline_type_errors_empty_when_no_type_checker():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.type_errors == []
    assert result.type_coverage == {}
    assert result.type_checker_backend == "none"


def test_pipeline_calls_type_checker_when_provided():
    from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
    tc = MagicMock(spec=TypeCheckerAnalyzer)
    tc.backend = "pyrefly"
    tc.analyze.return_value = {"errors": [], "coverage": {}, "backend": "pyrefly"}
    pipeline = _pipeline()
    pipeline._type_checker = tc
    pipeline.enrich(_commit(), "auth")
    tc.analyze.assert_called_once_with(_commit().files_changed)


def test_pipeline_type_errors_populated_from_type_checker():
    from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
    tc = MagicMock(spec=TypeCheckerAnalyzer)
    tc.backend = "pyrefly"
    tc.analyze.return_value = {
        "errors": [{"code": "bad-return-type", "message": "...", "path": "src/auth/token.py", "line": 5}],
        "coverage": {},
        "backend": "pyrefly",
    }
    pipeline = _pipeline()
    pipeline._type_checker = tc
    result = pipeline.enrich(_commit(), "auth")
    assert len(result.type_errors) == 1
    assert result.type_errors[0]["code"] == "bad-return-type"


def test_pipeline_type_coverage_populated_from_type_checker():
    from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
    tc = MagicMock(spec=TypeCheckerAnalyzer)
    tc.backend = "pyrefly"
    tc.analyze.return_value = {
        "errors": [],
        "coverage": {"src/auth/token.py": {"annotation_completeness": 0.75, "type_completeness": 0.80}},
        "backend": "pyrefly",
    }
    pipeline = _pipeline()
    pipeline._type_checker = tc
    result = pipeline.enrich(_commit(), "auth")
    assert result.type_coverage["src/auth/token.py"]["annotation_completeness"] == 0.75


def test_pipeline_backend_recorded_in_result():
    from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
    tc = MagicMock(spec=TypeCheckerAnalyzer)
    tc.backend = "pyrefly"
    tc.analyze.return_value = {"errors": [], "coverage": {}, "backend": "pyrefly"}
    pipeline = _pipeline()
    pipeline._type_checker = tc
    result = pipeline.enrich(_commit(), "auth")
    assert result.type_checker_backend == "pyrefly"


# ── analyzer_status wiring (Evidence > Guessing) ──────────────────────────────

def test_pipeline_analyzer_status_empty_when_no_analyzers():
    result = _pipeline().enrich(_commit(), "auth")
    assert result.analyzer_status["complexity"] == "ok"
    assert result.analyzer_status["semgrep"] == "ok"
    assert result.analyzer_status["joern"] == "not_installed"


def test_pipeline_records_type_checker_status():
    from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
    tc = MagicMock(spec=TypeCheckerAnalyzer)
    tc.backend = "pyrefly"
    tc.analyze.return_value = {
        "errors": [], "coverage": {}, "backend": "pyrefly", "status": "not_installed",
    }
    pipeline = _pipeline()
    pipeline._type_checker = tc
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["type_checker"] == "not_installed"


def test_pipeline_records_dead_code_status():
    from chips.harvester.enrichment.dead_code import VultureAnalyzer
    dc = MagicMock(spec=VultureAnalyzer)
    dc.analyze.return_value = []
    dc.last_status = "ok"
    pipeline = _pipeline()
    pipeline._dead_code = dc
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["dead_code"] == "ok"


def test_pipeline_records_api_surface_status():
    from chips.harvester.enrichment.api_surface import GriffeAnalyzer
    api = MagicMock(spec=GriffeAnalyzer)
    api.analyze.return_value = []
    api.last_status = "failed"
    pipeline = _pipeline()
    pipeline._api_surface = api
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["api_surface"] == "failed"


def test_pipeline_records_semgrep_status():
    pipeline = _pipeline()
    pipeline._semgrep.last_status = "not_installed"
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["semgrep"] == "not_installed"


def test_pipeline_records_security_status():
    from chips.harvester.enrichment.security import BanditAnalyzer
    security = MagicMock(spec=BanditAnalyzer)
    security.analyze.return_value = []
    security.last_status = "timed_out"
    pipeline = _pipeline()
    pipeline._security = security
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["security"] == "timed_out"


def test_pipeline_records_architecture_status():
    from chips.harvester.enrichment.architecture import ImportLinterAnalyzer
    architecture = MagicMock(spec=ImportLinterAnalyzer)
    architecture.analyze.return_value = []
    architecture.last_status = "failed"
    pipeline = _pipeline()
    pipeline._architecture = architecture
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["architecture"] == "failed"


def test_pipeline_records_clones_status():
    from chips.harvester.enrichment.clones import JscpdAnalyzer
    clones = MagicMock(spec=JscpdAnalyzer)
    clones.analyze.return_value = []
    clones.last_status = "ok"
    pipeline = _pipeline()
    pipeline._clones = clones
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["clones"] == "ok"


def test_pipeline_records_complexity_status():
    pipeline = _pipeline()
    pipeline._complexity.last_status = "failed"
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["complexity"] == "failed"


def test_pipeline_records_joern_status():
    from chips.harvester.enrichment.joern import JoernAnalyzer
    joern = MagicMock(spec=JoernAnalyzer)
    joern.analyze.return_value = []
    joern.last_status = "not_installed"
    pipeline = _pipeline()
    pipeline._joern = joern
    result = pipeline.enrich(_commit(), "auth")
    assert result.analyzer_status["joern"] == "not_installed"
