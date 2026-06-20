from __future__ import annotations

from chips.harvester.signals import (
    classify_generated_kind,
    cochange_entropy_for_file,
    normalized_entropy,
)


def test_classify_generated_kind_marks_migrations_as_scaffolded():
    assert classify_generated_kind("src/app/migrations/001_initial.py") == "scaffolded"


def test_classify_generated_kind_marks_generated_dir_as_generated():
    assert classify_generated_kind("src/__generated__/client.py") == "generated"


def test_classify_generated_kind_leaves_regular_source_unclassified():
    assert classify_generated_kind("src/auth/service.py") is None


def test_normalized_entropy_clamps_uniform_distribution_to_one():
    assert normalized_entropy([1, 1, 1]) == 1.0


def test_cochange_entropy_ignores_generated_partners():
    partner_frequencies = {
        "src/auth/service.py": 2,
        "src/migrations/001_auth.py": 2,
    }
    assert cochange_entropy_for_file("src/auth/controller.py", partner_frequencies) == 0.0


def test_cochange_entropy_zero_for_generated_focal_file():
    partner_frequencies = {
        "src/auth/service.py": 1,
        "src/auth/repo.py": 1,
    }
    assert cochange_entropy_for_file("src/migrations/001_auth.py", partner_frequencies) == 0.0
