from __future__ import annotations
from unittest.mock import MagicMock
from chips.harvester.extractor import CommitMemoryExtractor
from chips.harvester.enrichment.pipeline import EnrichmentPipeline
from chips.harvester.enrichment.models import EnrichmentResult
from chips.harvester.summarizer import DiffSummarizer
from chips.harvester.git_reader import CommitRecord

def _commit(**kwargs):
    defaults = dict(
        sha="abc123", author="Alice",
        committed_at="2026-05-01T00:00:00+00:00",
        message="fix auth crash",
        files_changed=["src/auth/token.py"],
    )
    defaults.update(kwargs)
    return CommitRecord(**defaults)

def test_extract_without_enricher_uses_commit_message():
    record = CommitMemoryExtractor().extract(_commit(message="add dark mode"))
    assert record.content == "add dark mode"

def test_extract_with_enricher_calls_summarizer():
    enricher = MagicMock(spec=EnrichmentPipeline)
    enricher.enrich.return_value = EnrichmentResult()
    summarizer = MagicMock(spec=DiffSummarizer)
    summarizer.summarize.return_value = "enriched lesson"
    record = CommitMemoryExtractor(enricher=enricher, summarizer=summarizer).extract(_commit())
    assert record.content == "enriched lesson"

def test_extract_enricher_called_with_commit_and_scope():
    enricher = MagicMock(spec=EnrichmentPipeline)
    enricher.enrich.return_value = EnrichmentResult()
    summarizer = MagicMock(spec=DiffSummarizer)
    summarizer.summarize.return_value = "lesson"
    CommitMemoryExtractor(enricher=enricher, summarizer=summarizer).extract(_commit())
    enricher.enrich.assert_called_once()
    call_args = enricher.enrich.call_args
    assert call_args[0][1] == "auth"  # scope inferred from files

def test_extract_without_summarizer_falls_back_to_message():
    enricher = MagicMock(spec=EnrichmentPipeline)
    record = CommitMemoryExtractor(enricher=enricher, summarizer=None).extract(_commit())
    assert record.content == "fix auth crash"

def test_existing_skip_merge_still_works():
    record = CommitMemoryExtractor().extract(_commit(message="Merge branch 'main'"))
    assert record is None

def test_existing_skip_empty_message_still_works():
    record = CommitMemoryExtractor().extract(_commit(message=""))
    assert record is None
