"""
Unit tests for the shared helpers on BaseExecutor —
`_acquire_token_or_error`, `_finalize_success`,
`_finalize_graphql_error`, `_finalize_business_error`.

These helpers are called from every concrete executor, so pinning
their contract keeps the whole executor family honest when the
base class changes.
"""

from unittest.mock import MagicMock

import pytest

from yieldfabric.config import YieldFabricConfig
from yieldfabric.core.output_store import OutputStore
from yieldfabric.executors.base import BaseExecutor
from yieldfabric.models import Command, CommandParameters
from yieldfabric.models.response import GraphQLResponse
from yieldfabric.models.user import User


# ---- Fixtures -----------------------------------------------------------


@pytest.fixture
def config():
    """Config with everything local and debug on (so tests can inspect logs)."""
    return YieldFabricConfig(
        pay_service_url="http://localhost:3002",
        auth_service_url="http://localhost:3000",
        command_delay=0,
        debug=False,
    )


@pytest.fixture
def output_store():
    return OutputStore(debug=False)


@pytest.fixture
def auth_service():
    """MagicMock satisfying the AuthService subset we invoke."""
    svc = MagicMock(name="AuthService")
    svc.login.return_value = "fake.jwt.token"
    svc.login_with_group.return_value = "fake.delegation.token"
    return svc


@pytest.fixture
def payments_service():
    return MagicMock(name="PaymentsService")


@pytest.fixture
def executor(auth_service, payments_service, output_store, config):
    """A BaseExecutor directly — `execute()` isn't implemented but
    the helper methods live on the base class."""
    return BaseExecutor(auth_service, payments_service, output_store, config)


def _command(name="cmd", cmd_type="deposit", *, group=None, params=None):
    """Build a plausible Command for helper-level tests."""
    return Command(
        name=name,
        type=cmd_type,
        user=User(id="u@example.com", password="pw", group=group),
        parameters=params or CommandParameters(),
    )


# ---- _acquire_token_or_error ------------------------------------------


def test_acquire_token_returns_token_on_successful_login(executor, auth_service):
    cmd = _command()
    token, err = executor._acquire_token_or_error(cmd)
    assert token == "fake.jwt.token"
    assert err is None
    auth_service.login.assert_called_once_with("u@example.com", "pw")


def test_acquire_token_uses_delegation_when_user_has_group(executor, auth_service):
    cmd = _command(group="Issuer Group")
    token, err = executor._acquire_token_or_error(cmd)
    assert token == "fake.delegation.token"
    assert err is None
    auth_service.login_with_group.assert_called_once_with(
        "u@example.com", "pw", "Issuer Group"
    )


def test_acquire_token_skips_delegation_when_use_delegation_false(executor, auth_service):
    """Group-admin path: even with `user.group` set, use direct login."""
    cmd = _command(group="Issuer Group")
    token, err = executor._acquire_token_or_error(cmd, use_delegation=False)
    assert token == "fake.jwt.token"
    assert err is None
    auth_service.login.assert_called_once_with("u@example.com", "pw")
    auth_service.login_with_group.assert_not_called()


def test_acquire_token_returns_error_when_login_fails(executor, auth_service):
    auth_service.login.return_value = None
    cmd = _command()
    token, err = executor._acquire_token_or_error(cmd)
    assert token is None
    assert err is not None
    assert err.success is False
    assert err.command_name == "cmd"
    assert err.command_type == "deposit"
    assert any("JWT" in e for e in err.errors)


# ---- _finalize_graphql_error ------------------------------------------


def test_finalize_graphql_error_surfaces_backend_message(executor):
    resp = GraphQLResponse(
        success=False,
        errors=[{"message": "Asset with ID foo not found"}],
    )
    cmd = _command()
    out = executor._finalize_graphql_error(cmd, resp, operation_name="Deposit")
    assert out.success is False
    assert out.errors == ["Asset with ID foo not found"]


def test_finalize_graphql_error_falls_back_to_operation_name(executor):
    # No errors array at all — we still get a useful message.
    resp = GraphQLResponse(success=False, errors=[])
    cmd = _command()
    out = executor._finalize_graphql_error(cmd, resp, operation_name="Withdraw")
    assert out.errors == ["Withdraw failed"]


# ---- _finalize_business_error -----------------------------------------


def test_finalize_business_error_returns_supplied_message(executor):
    cmd = _command()
    out = executor._finalize_business_error(
        cmd, "insufficient balance", operation_name="Deposit"
    )
    assert out.success is False
    assert out.errors == ["insufficient balance"]
    assert out.command_name == "cmd"


# ---- _finalize_success -------------------------------------------------


def test_finalize_success_stores_outputs_and_returns_success(executor, output_store):
    cmd = _command(name="deposit_1")
    outputs = {"message_id": "msg-1", "amount": "10", "empty_field": None}
    out = executor._finalize_success(
        cmd, token="tok", outputs=outputs, success_message="Deposit ok"
    )
    assert out.success is True
    assert out.command_name == "deposit_1"
    assert out.data["message_id"] == "msg-1"
    # All non-None outputs should be in the store for downstream chaining.
    assert output_store.get("deposit_1", "message_id") == "msg-1"
    assert output_store.get("deposit_1", "amount") == "10"


def test_finalize_success_skips_wait_when_not_requested(
    executor, payments_service
):
    # No `wait: true` on the command → poll_message_completion should
    # NEVER be called.
    cmd = _command(params=CommandParameters())
    executor._finalize_success(
        cmd, token="tok",
        outputs={"message_id": "msg-1"},
        success_message="ok",
    )
    payments_service.poll_message_completion.assert_not_called()


def test_finalize_success_polls_when_wait_true_and_message_id_present(
    executor, payments_service
):
    # wait: true + a message_id to poll on. Stub the poller to return
    # a completed result so we can check the output-merge logic.
    from yieldfabric.utils.polling import PollResult

    payments_service.poll_message_completion.return_value = PollResult(
        observation={"executed": "2026-04-21T10:00:00Z", "response": {"ok": True}},
        attempts=3,
        elapsed=4.2,
    )

    params = CommandParameters(raw_params={"wait": True, "user_id": "entity-1"})
    cmd = _command(params=params)
    out = executor._finalize_success(
        cmd, token="tok",
        outputs={"message_id": "msg-1"},
        success_message="ok",
    )
    payments_service.poll_message_completion.assert_called_once()
    # Wait metadata must be merged into the stored outputs.
    assert out.data["executed_at"] == "2026-04-21T10:00:00Z"
    assert out.data["wait_attempts"] == 3
    assert out.data["wait_elapsed"] == 4.2


def test_finalize_success_wait_noop_when_message_id_missing(
    executor, payments_service
):
    # wait: true but no message_id in outputs — poll should NOT run.
    params = CommandParameters(raw_params={"wait": True, "user_id": "entity-1"})
    cmd = _command(params=params)
    executor._finalize_success(
        cmd, token="tok",
        outputs={"accepted_count": 2},  # no message_id
        success_message="bulk ok",
    )
    payments_service.poll_message_completion.assert_not_called()


def test_finalize_success_wait_surfaces_timeout_without_raising(
    executor, payments_service
):
    # If poll_message_completion raises TimeoutError, _finalize_success
    # should still return a success CommandResponse (the mutation itself
    # succeeded — wait is advisory). It must mark wait_timed_out in
    # outputs so callers can detect it.
    payments_service.poll_message_completion.side_effect = TimeoutError(
        "message never executed"
    )
    params = CommandParameters(raw_params={"wait": True, "user_id": "entity-1"})
    cmd = _command(params=params)
    out = executor._finalize_success(
        cmd, token="tok",
        outputs={"message_id": "msg-1"},
        success_message="ok",
    )
    assert out.success is True
    assert out.data.get("wait_timed_out") is True
    assert "never executed" in (out.data.get("wait_error") or "")
