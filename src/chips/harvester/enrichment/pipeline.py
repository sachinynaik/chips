from __future__ import annotations

from chips.harvester.enrichment.models import EnrichmentResult
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
from chips.harvester.enrichment.refactoring import RefactoringDetector
from chips.harvester.enrichment.scope_memories import ScopeMemoryFetcher
from chips.harvester.enrichment.security import BanditAnalyzer
from chips.harvester.enrichment.semble import SembleEnricher
from chips.harvester.enrichment.semgrep import SemgrepAnalyzer
from chips.harvester.enrichment.type_checker import TypeCheckerAnalyzer
from chips.harvester.git_reader import CommitRecord


class EnrichmentPipeline:
    def __init__(
        self,
        git_diff: GitDiffFetcher,
        complexity: LizardAnalyzer,
        semgrep: SemgrepAnalyzer,
        semble: SembleEnricher,
        graphify: GraphifyEnricher,
        refactoring: RefactoringDetector,
        joern: JoernAnalyzer,
        defect: DefectPredictor,
        scope_memories: ScopeMemoryFetcher,
        cochange: CochangeFetcher,
        code_embedder: CodeEmbedder | None = None,
        type_checker: TypeCheckerAnalyzer | None = None,
        api_surface: GriffeAnalyzer | None = None,
        dead_code: VultureAnalyzer | None = None,
        security: BanditAnalyzer | None = None,
        coverage_reader: CoverageReader | None = None,
        architecture: ImportLinterAnalyzer | None = None,
        clones: JscpdAnalyzer | None = None,
        ownership: CodeownersParser | None = None,
        conn_factory=None,
    ) -> None:
        self._git_diff = git_diff
        self._complexity = complexity
        self._semgrep = semgrep
        self._code_embedder = code_embedder
        self._type_checker = type_checker
        self._api_surface = api_surface
        self._dead_code = dead_code
        self._security = security
        self._coverage_reader = coverage_reader
        self._architecture = architecture
        self._clones = clones
        self._ownership = ownership
        self._semble = semble
        self._graphify = graphify
        self._refactoring = refactoring
        self._joern = joern
        self._defect = defect
        self._scope_memories = scope_memories
        self._cochange = cochange
        self._conn_factory = conn_factory

    def enrich(self, commit: CommitRecord, scope: str) -> EnrichmentResult:
        diff_content, hunk_headers = self._git_diff.fetch(commit.sha)

        complexity_metrics = self._complexity.analyze(commit.files_changed)
        semgrep_findings = self._semgrep.analyze(commit.files_changed)

        type_errors: list[dict] = []
        type_coverage: dict = {}
        type_checker_backend = "none"
        if self._type_checker is not None:
            tc_result = self._type_checker.analyze(commit.files_changed)
            type_errors = tc_result.get("errors", [])
            type_coverage = tc_result.get("coverage", {})
            type_checker_backend = tc_result.get("backend", self._type_checker.backend)

        api_surface_findings: list[dict] = []
        if self._api_surface is not None:
            api_surface_findings = self._api_surface.analyze(commit.files_changed)

        dead_code_findings: list[dict] = []
        if self._dead_code is not None:
            dead_code_findings = self._dead_code.analyze(commit.files_changed)

        security_findings: list[dict] = []
        if self._security is not None:
            security_findings = self._security.analyze(commit.files_changed)

        line_coverage: dict = {}
        if self._coverage_reader is not None:
            line_coverage = self._coverage_reader.analyze(commit.files_changed)

        architecture_violations: list[dict] = []
        if self._architecture is not None:
            architecture_violations = self._architecture.analyze(commit.files_changed)

        clone_findings: list[dict] = []
        if self._clones is not None:
            clone_findings = self._clones.analyze(commit.files_changed)

        ownership: dict = {}
        if self._ownership is not None:
            ownership = self._ownership.analyze(commit.files_changed)

        similar_commits: list[dict] = []
        if self._code_embedder is not None and self._conn_factory is not None:
            conn = self._conn_factory()
            try:
                similar_commits = self._code_embedder.find_similar_commits(diff_content, conn)
            finally:
                conn.close()

        related_symbols = self._semble.enrich(commit.files_changed, diff_content)
        community_context = self._graphify.enrich(scope)

        refactoring_type = self._refactoring.detect(diff_content)
        cpg_findings = self._joern.analyze(commit.files_changed)
        defect_risk = self._defect.predict(diff_content, commit.message)

        scope_memories: list[dict] = []
        cochange_pairs: list[dict] = []
        if self._conn_factory is not None:
            conn = self._conn_factory()
            try:
                scope_memories = self._scope_memories.fetch(conn, scope)
                cochange_pairs = self._cochange.fetch(conn, commit.files_changed)
            finally:
                conn.close()

        return EnrichmentResult(
            diff_content=diff_content,
            hunk_headers=hunk_headers,
            complexity_metrics=complexity_metrics,
            semgrep_findings=semgrep_findings,
            type_errors=type_errors,
            type_coverage=type_coverage,
            type_checker_backend=type_checker_backend,
            api_surface_findings=api_surface_findings,
            dead_code_findings=dead_code_findings,
            security_findings=security_findings,
            line_coverage=line_coverage,
            architecture_violations=architecture_violations,
            clone_findings=clone_findings,
            ownership=ownership,
            similar_commits=similar_commits,
            related_symbols=related_symbols,
            community_context=community_context,
            refactoring_type=refactoring_type,
            cpg_findings=cpg_findings,
            defect_risk=defect_risk,
            scope_memories=scope_memories,
            cochange_pairs=cochange_pairs,
        )
