from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from chips.harvester.enrichment.ownership import CodeownersParser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_codeowners(directory: Path, content: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "CODEOWNERS").write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests: codeowners_available
# ---------------------------------------------------------------------------

def test_returns_unavailable_when_no_codeowners(tmp_path: Path) -> None:
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert result["codeowners_available"] is False


def test_finds_codeowners_in_github_subdir(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @org/team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert result["codeowners_available"] is True


def test_finds_codeowners_in_repo_root(tmp_path: Path) -> None:
    _write_codeowners(tmp_path, "* @org/team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert result["codeowners_available"] is True


def test_finds_codeowners_in_docs_subdir(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / "docs", "* @org/team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert result["codeowners_available"] is True


def test_prefers_github_over_root(tmp_path: Path) -> None:
    """When both .github/CODEOWNERS and root CODEOWNERS exist, .github wins."""
    _write_codeowners(tmp_path / ".github", "* @github-team\n")
    _write_codeowners(tmp_path, "* @root-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["any/file.py"])
    assert "@github-team" in result["all_owners"]
    assert "@root-team" not in result["all_owners"]


# ---------------------------------------------------------------------------
# Tests: parsing
# ---------------------------------------------------------------------------

def test_parses_team_handle(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @org/backend\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert "@org/backend" in result["owners_by_file"]["src/foo.py"]


def test_parses_user_handle(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @alice\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert "@alice" in result["owners_by_file"]["src/foo.py"]


def test_parses_email_owner(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* dev@example.com\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert "dev@example.com" in result["owners_by_file"]["src/foo.py"]


def test_skips_comment_lines(tmp_path: Path) -> None:
    content = "# This is a comment\n* @org/team\n"
    _write_codeowners(tmp_path / ".github", content)
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert result["owners_by_file"]["src/foo.py"] == ["@org/team"]


def test_skips_blank_lines(tmp_path: Path) -> None:
    content = "\n\n* @org/team\n\n"
    _write_codeowners(tmp_path / ".github", content)
    result = CodeownersParser(str(tmp_path)).analyze(["src/foo.py"])
    assert "@org/team" in result["owners_by_file"]["src/foo.py"]


# ---------------------------------------------------------------------------
# Tests: pattern matching
# ---------------------------------------------------------------------------

def test_wildcard_matches_any_file(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @everyone\n")
    result = CodeownersParser(str(tmp_path)).analyze(["deep/nested/file.ts"])
    assert "@everyone" in result["owners_by_file"]["deep/nested/file.ts"]


def test_py_extension_pattern_matches_py_files(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "*.py @python-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/module.py"])
    assert "@python-team" in result["owners_by_file"]["src/module.py"]


def test_py_extension_pattern_does_not_match_ts_files(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "*.py @python-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/module.ts"])
    assert result["owners_by_file"].get("src/module.ts", []) == []


def test_src_prefix_pattern_matches_files_under_src(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "src/* @src-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/module.py"])
    assert "@src-team" in result["owners_by_file"]["src/module.py"]


def test_last_matching_rule_wins(tmp_path: Path) -> None:
    content = (
        "* @first-team\n"
        "*.py @python-team\n"
    )
    _write_codeowners(tmp_path / ".github", content)
    result = CodeownersParser(str(tmp_path)).analyze(["src/module.py"])
    owners = result["owners_by_file"]["src/module.py"]
    assert owners == ["@python-team"]


def test_returns_empty_owners_for_unmatched_file(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "*.py @python-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/app.ts"])
    assert result["owners_by_file"].get("src/app.ts", []) == []


# ---------------------------------------------------------------------------
# Tests: cross_team_change and all_owners
# ---------------------------------------------------------------------------

def test_cross_team_false_when_single_owner_for_all_files(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @single-team\n")
    result = CodeownersParser(str(tmp_path)).analyze(["src/a.py", "src/b.py"])
    assert result["cross_team_change"] is False


def test_cross_team_true_when_different_owners_for_different_files(tmp_path: Path) -> None:
    content = (
        "*.py @python-team\n"
        "*.ts @frontend-team\n"
    )
    _write_codeowners(tmp_path / ".github", content)
    result = CodeownersParser(str(tmp_path)).analyze(["src/a.py", "src/b.ts"])
    assert result["cross_team_change"] is True


def test_all_owners_is_sorted_and_deduplicated(tmp_path: Path) -> None:
    content = (
        "*.py @beta-team\n"
        "*.ts @alpha-team\n"
        "*.js @beta-team\n"
    )
    _write_codeowners(tmp_path / ".github", content)
    result = CodeownersParser(str(tmp_path)).analyze(["src/a.py", "src/b.ts", "src/c.js"])
    owners = result["all_owners"]
    assert owners == sorted(set(owners))
    assert owners.count("@beta-team") == 1


# ---------------------------------------------------------------------------
# Tests: empty file_paths
# ---------------------------------------------------------------------------

def test_empty_file_paths_returns_empty_owners_by_file(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @org/team\n")
    result = CodeownersParser(str(tmp_path)).analyze([])
    assert result["codeowners_available"] is True
    assert result["owners_by_file"] == {}


def test_empty_file_paths_no_codeowners_returns_false_available(tmp_path: Path) -> None:
    result = CodeownersParser(str(tmp_path)).analyze([])
    assert result["codeowners_available"] is False
    assert result["owners_by_file"] == {}


def test_last_status_defaults_to_skipped_before_run(tmp_path: Path) -> None:
    assert CodeownersParser(str(tmp_path)).last_status == "skipped"


def test_last_status_skipped_when_no_codeowners(tmp_path: Path) -> None:
    parser = CodeownersParser(str(tmp_path))
    parser.analyze(["src/foo.py"])
    assert parser.last_status == "skipped"


def test_last_status_ok_when_codeowners_available(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @org/team\n")
    parser = CodeownersParser(str(tmp_path))
    parser.analyze(["src/foo.py"])
    assert parser.last_status == "ok"


def test_last_status_failed_when_codeowners_parse_crashes(tmp_path: Path) -> None:
    _write_codeowners(tmp_path / ".github", "* @org/team\n")
    parser = CodeownersParser(str(tmp_path))
    with patch.object(parser, "_parse_rules", side_effect=RuntimeError("boom")):
        result = parser.analyze(["src/foo.py"])
    assert parser.last_status == "failed"
    assert result["codeowners_available"] is True
    assert result["owners_by_file"] == {}
