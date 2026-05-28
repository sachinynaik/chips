"""Contract tests for the feedback write API (BriefOutcomeRepository.record()).

Covers:
- Accepted outcome values
- Idempotency key requirement and behaviour
- Tenant / brief validation
- Duplicate response behaviour
- Stable failure cases
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest  # noqa: F401 used for pytest.raises / pytest.mark

from chips.memory.outcome_repository import BriefOutcomeRepository, OutcomeValue

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_BRIEF_ID = uuid.UUID("bbbbbbbb-0000-0000-0000-000000000001")
_TENANT_A = "aaaaaaaa-0000-0000-0000-000000000001"
_TENANT_B = "aaaaaaaa-0000-0000-0000-000000000002"
_FAKE_OUTCOME_ID = str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Connection mock helpers
# ---------------------------------------------------------------------------

def _conn_no_idem(brief_tenant: str | None = None, outcome_id: str | None = None):
    """Two execute calls: brief existence check + INSERT RETURNING."""
    conn = MagicMock()
    brief_mock = MagicMock()
    brief_mock.fetchone.return_value = (brief_tenant,)
    insert_mock = MagicMock()
    insert_mock.fetchone.return_value = (outcome_id or _FAKE_OUTCOME_ID,)
    conn.execute.side_effect = [brief_mock, insert_mock]
    return conn


def _conn_with_idem_miss(brief_tenant: str | None = None):
    """Three calls: brief check + idempotency SELECT (miss) + INSERT."""
    conn = MagicMock()
    brief_mock = MagicMock()
    brief_mock.fetchone.return_value = (brief_tenant,)
    idem_mock = MagicMock()
    idem_mock.fetchone.return_value = None  # no existing row
    insert_mock = MagicMock()
    insert_mock.fetchone.return_value = (_FAKE_OUTCOME_ID,)
    conn.execute.side_effect = [brief_mock, idem_mock, insert_mock]
    return conn


def _conn_with_idem_hit(existing_id: str, brief_tenant: str | None = None):
    """Two calls: brief check + idempotency SELECT (hit) → early return."""
    conn = MagicMock()
    brief_mock = MagicMock()
    brief_mock.fetchone.return_value = (brief_tenant,)
    idem_mock = MagicMock()
    idem_mock.fetchone.return_value = (existing_id,)
    conn.execute.side_effect = [brief_mock, idem_mock]
    return conn


def _conn_brief_not_found():
    conn = MagicMock()
    m = MagicMock()
    m.fetchone.return_value = None
    conn.execute.return_value = m
    return conn


def _conn_tenant_mismatch(stored: str):
    """Brief found with stored tenant that won't match the caller's tenant."""
    conn = MagicMock()
    m = MagicMock()
    m.fetchone.return_value = (stored,)
    conn.execute.return_value = m
    return conn


# ---------------------------------------------------------------------------
# Accepted outcome values
# ---------------------------------------------------------------------------

class TestAcceptedOutcomeValues:
    """OutcomeValue literal must be exactly: accepted | rejected | ignored."""

    def test_outcome_value_type_is_literal(self):
        import typing
        args = typing.get_args(OutcomeValue)
        assert set(args) == {"accepted", "rejected", "ignored"}

    @pytest.mark.parametrize("outcome", ["accepted", "rejected", "ignored"])
    def test_valid_outcome_accepted(self, outcome):
        conn = _conn_no_idem()
        repo = BriefOutcomeRepository(conn)
        result = repo.record(_BRIEF_ID, outcome=outcome)
        assert isinstance(result, uuid.UUID)

    def test_no_other_outcome_in_literal(self):
        import typing
        args = typing.get_args(OutcomeValue)
        assert "success" not in args
        assert "failure" not in args
        assert "partial" not in args
        assert "abandoned" not in args


# ---------------------------------------------------------------------------
# Brief existence validation
# ---------------------------------------------------------------------------

class TestBriefValidation:
    def test_raises_when_brief_not_found(self):
        conn = _conn_brief_not_found()
        with pytest.raises(ValueError, match="brief_id not found"):
            BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")

    def test_error_message_includes_brief_id(self):
        conn = _conn_brief_not_found()
        with pytest.raises(ValueError) as exc_info:
            BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")
        assert str(_BRIEF_ID) in str(exc_info.value)

    def test_no_commit_when_brief_not_found(self):
        conn = _conn_brief_not_found()
        with pytest.raises(ValueError):
            BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")
        conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Tenant validation
# ---------------------------------------------------------------------------

class TestTenantValidation:
    def test_raises_on_tenant_mismatch(self):
        conn = _conn_tenant_mismatch(stored=_TENANT_A)
        with pytest.raises(ValueError, match="tenant_id mismatch"):
            BriefOutcomeRepository(conn).record(
                _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_B
            )

    def test_no_error_when_tenant_matches(self):
        conn = _conn_no_idem(brief_tenant=_TENANT_A)
        result = BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_A
        )
        assert isinstance(result, uuid.UUID)

    def test_no_error_when_brief_has_no_stored_tenant(self):
        conn = _conn_no_idem(brief_tenant=None)
        result = BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_A
        )
        assert isinstance(result, uuid.UUID)

    def test_no_error_when_caller_provides_no_tenant(self):
        conn = _conn_no_idem(brief_tenant=_TENANT_A)
        result = BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", tenant_id=None
        )
        assert isinstance(result, uuid.UUID)

    def test_no_commit_on_tenant_mismatch(self):
        conn = _conn_tenant_mismatch(stored=_TENANT_A)
        with pytest.raises(ValueError):
            BriefOutcomeRepository(conn).record(
                _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_B
            )
        conn.commit.assert_not_called()


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_returns_existing_id_on_duplicate_key(self):
        existing_id = str(uuid.uuid4())
        conn = _conn_with_idem_hit(existing_id)
        result = BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", idempotency_key="req-001"
        )
        assert result == uuid.UUID(existing_id)

    def test_no_insert_on_duplicate_key(self):
        existing_id = str(uuid.uuid4())
        conn = _conn_with_idem_hit(existing_id)
        BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", idempotency_key="req-001"
        )
        # brief check + idempotency SELECT only — no INSERT
        assert conn.execute.call_count == 2
        conn.commit.assert_not_called()

    def test_inserts_when_key_not_yet_seen(self):
        conn = _conn_with_idem_miss()
        result = BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", idempotency_key="req-new"
        )
        assert isinstance(result, uuid.UUID)
        conn.commit.assert_called_once()

    def test_inserts_every_time_when_no_key(self):
        """Without a key, every call is a fresh insert (append-only)."""
        conn = _conn_no_idem()
        result = BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")
        assert isinstance(result, uuid.UUID)
        conn.commit.assert_called_once()

    def test_idempotency_select_skipped_when_no_key(self):
        """Without a key, we skip the idempotency SELECT entirely."""
        conn = _conn_no_idem()
        BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")
        # Only brief check + INSERT
        assert conn.execute.call_count == 2

    def test_idempotency_key_passed_to_insert_sql(self):
        conn = _conn_with_idem_miss()
        BriefOutcomeRepository(conn).record(
            _BRIEF_ID, outcome="accepted", idempotency_key="req-x"
        )
        insert_call_params = conn.execute.call_args_list[2][0][1]
        assert "req-x" in insert_call_params


# ---------------------------------------------------------------------------
# Stable failure cases
# ---------------------------------------------------------------------------

class TestStableFailureCases:
    def test_brief_not_found_is_value_error(self):
        conn = _conn_brief_not_found()
        with pytest.raises(ValueError):
            BriefOutcomeRepository(conn).record(_BRIEF_ID, outcome="accepted")

    def test_tenant_mismatch_is_value_error(self):
        conn = _conn_tenant_mismatch(stored=_TENANT_A)
        with pytest.raises(ValueError):
            BriefOutcomeRepository(conn).record(
                _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_B
            )

    def test_errors_never_commit(self):
        for conn in [_conn_brief_not_found(), _conn_tenant_mismatch(stored=_TENANT_A)]:
            conn.commit.reset_mock()
            try:
                BriefOutcomeRepository(conn).record(
                    _BRIEF_ID, outcome="accepted", tenant_id=_TENANT_B
                )
            except ValueError:
                pass
            conn.commit.assert_not_called()
