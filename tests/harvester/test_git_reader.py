"""Git reader unit tests — no DB required."""
from chips.harvester.git_reader import GitReader, CommitRecord


GIT_LOG_SAMPLE = """\
abc123|Alice|2026-05-10T12:00:00+00:00|Fix checkout precondition
---
src/valet/checkout.py
src/valet/tests/test_checkout.py
===
def456|Bob|2026-05-09T09:00:00+00:00|Add parking slot model
---
src/parking/models.py
src/parking/migrations/001_slots.py
src/parking/tests/test_models.py
===
"""


def test_parse_commits_returns_correct_count():
    reader = GitReader.__new__(GitReader)
    commits = reader._parse_log(GIT_LOG_SAMPLE)
    assert len(commits) == 2


def test_parse_commit_fields():
    reader = GitReader.__new__(GitReader)
    commits = reader._parse_log(GIT_LOG_SAMPLE)
    c = commits[0]
    assert c.sha == "abc123"
    assert c.author == "Alice"
    assert c.message == "Fix checkout precondition"
    assert "src/valet/checkout.py" in c.files_changed


def test_parse_commit_files_changed():
    reader = GitReader.__new__(GitReader)
    commits = reader._parse_log(GIT_LOG_SAMPLE)
    c = commits[1]
    assert set(c.files_changed) == {
        "src/parking/models.py",
        "src/parking/migrations/001_slots.py",
        "src/parking/tests/test_models.py",
    }


def test_cochange_pairs_from_commits():
    reader = GitReader.__new__(GitReader)
    commits = reader._parse_log(GIT_LOG_SAMPLE)
    pairs = reader._compute_cochange_pairs(commits)

    pair_set = {(a, b) for a, b, _ in pairs}
    assert ("src/valet/checkout.py", "src/valet/tests/test_checkout.py") in pair_set or \
           ("src/valet/tests/test_checkout.py", "src/valet/checkout.py") in pair_set


def test_cochange_frequency_increments_for_repeated_pairs():
    reader = GitReader.__new__(GitReader)
    double_log = GIT_LOG_SAMPLE + GIT_LOG_SAMPLE
    commits = reader._parse_log(double_log)
    pairs = reader._compute_cochange_pairs(commits)

    freq = {
        tuple(sorted([a, b])): f
        for a, b, f in pairs
    }
    key = tuple(sorted(["src/valet/checkout.py", "src/valet/tests/test_checkout.py"]))
    assert freq[key] == 2


def test_compute_file_churn():
    reader = GitReader.__new__(GitReader)
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py"]),
    ]
    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["foo.py"].churn_count == 2
    assert by_file["bar.py"].churn_count == 1


def test_compute_file_signals_has_zero_entropy_for_single_stable_partner():
    reader = GitReader.__new__(GitReader)
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
    ]

    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["foo.py"].cochange_entropy == 0.0
    assert by_file["bar.py"].cochange_entropy == 0.0


def test_compute_file_signals_entropy_increases_with_scattered_partners():
    reader = GitReader.__new__(GitReader)
    # Each partner co-changes with foo.py twice so it clears the support threshold
    # (open decision #2: min support 2); single shared commits are noise.
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="a2", author="A", committed_at="2026-05-01T01:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="b2", author="B", committed_at="2026-05-02T01:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="c", author="C", committed_at="2026-05-03T00:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
        CommitRecord(sha="c2", author="C", committed_at="2026-05-03T01:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
    ]

    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["foo.py"].cochange_entropy > 0.0
    assert by_file["bar.py"].cochange_entropy == 0.0


def test_compute_file_signals_entropy_is_maximal_for_uniform_partner_distribution():
    reader = GitReader.__new__(GitReader)
    # Three partners, each at support 2 -> uniform distribution -> maximal entropy.
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="a2", author="A", committed_at="2026-05-01T01:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="b2", author="B", committed_at="2026-05-02T01:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="c", author="C", committed_at="2026-05-03T00:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
        CommitRecord(sha="c2", author="C", committed_at="2026-05-03T01:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
    ]

    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["foo.py"].cochange_entropy == 1.0


def test_compute_file_signals_entropy_is_lower_for_concentrated_partner_distribution():
    reader = GitReader.__new__(GitReader)
    # All partners are at support >= 2 so the threshold keeps them; the difference is
    # purely the shape of the distribution (uniform vs concentrated on one partner).
    uniform_commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="a2", author="A", committed_at="2026-05-01T01:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="b2", author="B", committed_at="2026-05-02T01:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="c", author="C", committed_at="2026-05-03T00:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
        CommitRecord(sha="c2", author="C", committed_at="2026-05-03T01:00:00",
                     message="m", files_changed=["foo.py", "qux.py"]),
    ]
    concentrated_commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="c", author="C", committed_at="2026-05-03T00:00:00",
                     message="m", files_changed=["foo.py", "bar.py"]),
        CommitRecord(sha="d", author="D", committed_at="2026-05-04T00:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
        CommitRecord(sha="d2", author="D", committed_at="2026-05-04T01:00:00",
                     message="m", files_changed=["foo.py", "baz.py"]),
    ]

    uniform = {s.file_path: s for s in reader._compute_file_signals(uniform_commits)}
    concentrated = {s.file_path: s for s in reader._compute_file_signals(concentrated_commits)}
    assert concentrated["foo.py"].cochange_entropy < uniform["foo.py"].cochange_entropy


def test_compute_file_signals_ignores_generated_partners_for_entropy():
    reader = GitReader.__new__(GitReader)
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["src/foo.py", "src/bar.py"]),
        CommitRecord(sha="b", author="B", committed_at="2026-05-02T00:00:00",
                     message="m", files_changed=["src/foo.py", "src/migrations/001_init.py"]),
    ]

    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["src/foo.py"].cochange_entropy == 0.0


def test_compute_file_signals_marks_generated_kind():
    reader = GitReader.__new__(GitReader)
    commits = [
        CommitRecord(sha="a", author="A", committed_at="2026-05-01T00:00:00",
                     message="m", files_changed=["src/__generated__/api.py"]),
    ]

    signals = reader._compute_file_signals(commits)
    by_file = {s.file_path: s for s in signals}
    assert by_file["src/__generated__/api.py"].generated_kind == "generated"
