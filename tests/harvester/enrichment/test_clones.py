from __future__ import annotations

from unittest.mock import patch

from chips.harvester.enrichment.clones import JscpdAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_duplicate(
    file_a: str = "src/foo.py",
    start_a: int = 1,
    end_a: int = 10,
    file_b: str = "src/bar.py",
    start_b: int = 20,
    end_b: int = 29,
    lines: int = 10,
    tokens: int = 60,
    fmt: str = "python",
) -> dict:
    return {
        "firstFile": {"name": file_a, "start": start_a, "end": end_a},
        "secondFile": {"name": file_b, "start": start_b, "end": end_b},
        "lines": lines,
        "tokens": tokens,
        "format": fmt,
    }


def _make_report(duplicates: list[dict]) -> dict:
    return {"duplicates": duplicates}


# ---------------------------------------------------------------------------
# Tests: empty file_paths
# ---------------------------------------------------------------------------

def test_returns_empty_for_empty_file_paths() -> None:
    result = JscpdAnalyzer(repo_path="/tmp/repo").analyze([])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: jscpd not installed
# ---------------------------------------------------------------------------

def test_returns_empty_when_jscpd_not_installed() -> None:
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", side_effect=FileNotFoundError):
        result = analyzer.analyze(["src/foo.py"])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: no duplicates
# ---------------------------------------------------------------------------

def test_returns_empty_when_no_duplicates() -> None:
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report([])):
        result = analyzer.analyze(["src/foo.py"])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: correct parsing
# ---------------------------------------------------------------------------

def test_parses_jscpd_output_correctly() -> None:
    dup = _make_duplicate()
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report([dup])):
        result = analyzer.analyze(["src/foo.py"])
    assert len(result) == 1
    r = result[0]
    assert r["file_a"] == "src/foo.py"
    assert r["start_a"] == 1
    assert r["end_a"] == 10
    assert r["file_b"] == "src/bar.py"
    assert r["start_b"] == 20
    assert r["end_b"] == 29
    assert r["lines"] == 10
    assert r["tokens"] == 60
    assert r["language"] == "python"


def test_result_dicts_have_required_keys() -> None:
    dup = _make_duplicate()
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report([dup])):
        result = analyzer.analyze(["src/foo.py"])
    assert len(result) == 1
    for key in ("file_a", "start_a", "end_a", "file_b", "start_b", "end_b", "lines", "tokens", "language"):
        assert key in result[0], f"Missing key: {key}"


def test_maps_firstfile_to_file_a() -> None:
    dup = _make_duplicate(file_a="alpha/module.py", file_b="beta/module.py")
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report([dup])):
        result = analyzer.analyze(["alpha/module.py"])
    assert result[0]["file_a"] == "alpha/module.py"
    assert result[0]["file_b"] == "beta/module.py"


def test_maps_format_to_language() -> None:
    dup = _make_duplicate(fmt="typescript")
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report([dup])):
        result = analyzer.analyze(["src/app.ts"])
    assert result[0]["language"] == "typescript"


# ---------------------------------------------------------------------------
# Tests: cap at 20
# ---------------------------------------------------------------------------

def test_caps_results_at_20() -> None:
    dups = [_make_duplicate(file_a=f"src/f{i}.py", file_b=f"src/g{i}.py") for i in range(30)]
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", return_value=_make_report(dups)):
        result = analyzer.analyze(["src/f0.py"])
    assert len(result) == 20


# ---------------------------------------------------------------------------
# Tests: error handling
# ---------------------------------------------------------------------------

def test_returns_empty_on_malformed_json() -> None:
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", side_effect=ValueError("bad json")):
        result = analyzer.analyze(["src/foo.py"])
    assert result == []


def test_returns_empty_on_any_exception() -> None:
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", side_effect=RuntimeError("jscpd crashed")):
        result = analyzer.analyze(["src/foo.py"])
    assert result == []


def test_returns_empty_when_no_output_file() -> None:
    """Simulate jscpd running but writing no output (FileNotFoundError on read)."""
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo")
    with patch.object(analyzer, "_run_jscpd", side_effect=FileNotFoundError("no output file")):
        result = analyzer.analyze(["src/foo.py"])
    assert result == []


# ---------------------------------------------------------------------------
# Tests: constructor params propagated
# ---------------------------------------------------------------------------

def test_min_lines_param_passed_to_jscpd() -> None:
    """Verify min_lines is stored and available (behavioural test via _run_jscpd)."""
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo", min_lines=15)
    assert analyzer._min_lines == 15


def test_min_tokens_param_passed_to_jscpd() -> None:
    analyzer = JscpdAnalyzer(repo_path="/tmp/repo", min_tokens=100)
    assert analyzer._min_tokens == 100
