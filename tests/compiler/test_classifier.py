from __future__ import annotations

import pytest

from chips.compiler.classifier import TaskKind, classify_task


def test_classify_bugfix():
    assert classify_task("fix the auth crash on login") == TaskKind.bugfix


def test_classify_feature():
    assert classify_task("add dark mode to the settings screen") == TaskKind.feature


def test_classify_refactor():
    assert classify_task("refactor the payment module to remove duplication") == TaskKind.refactor


def test_classify_test():
    assert classify_task("write tests for the user service") == TaskKind.test


def test_classify_migration():
    assert classify_task("create alembic migration for the new tenant_id column") == TaskKind.migration


def test_classify_docs():
    assert classify_task("document the booking API endpoints") == TaskKind.docs


def test_classify_unknown():
    assert classify_task("") == TaskKind.unknown


def test_classify_unknown_unrecognised():
    assert classify_task("zxqpqp blorb") == TaskKind.unknown


def test_classify_case_insensitive():
    assert classify_task("FIX the broken pipeline") == TaskKind.bugfix


def test_bugfix_takes_priority_over_feature_when_fix_present():
    result = classify_task("fix and add retry logic")
    assert result == TaskKind.bugfix
