"""
E2E flow test: deposit -> instant -> accept across two users.

This rewrites the intent of the first block of `yieldfabric-docs/scripts/commands.yaml`
(issuer_deposit -> issuer_send_1 -> counterpart_accept_1) using the Python
framework's v2 service clients and freshly-provisioned users.

Why not run commands.yaml directly? commands.yaml hard-codes users
(issuer@yieldfabric.com, counterpart@yieldfabric.com, admin2@...) that only
exist after `setup_system.sh` has been run. We avoid that dependency by
provisioning two disposable users for this test.

What's pinned:
    1. Sender can deposit an existing denomination (`aud-token-asset`, seeded
       on the dev env). Deposit mutation returns `success: true`, meaning the
       message was queued to MQ — this is the contract GraphQL guarantees.
    2. Sender can instant-send to the receiver by email; the mutation returns
       a `paymentId` that becomes the handle for acceptance.
    3. Receiver can accept that `paymentId`. Mutation returns `success: true`.

What is NOT pinned here (deliberately):
    - On-chain settlement. All three mutations are async-submitted to MQ; their
      on-chain effect happens later. Asserting on final balances is a separate
      concern that needs a polling helper.
    - Idempotency-key dedup behaviour.
    - Partial acceptance (accept with amount < full).

If any of these three mutations starts returning `success: false` or a GraphQL
error, the flow is broken end-to-end and this test will trip — catching the
regression before it reaches on-chain code paths.
"""

import time
import uuid

import pytest

from yieldfabric.services.auth_service import AuthService
from yieldfabric.services.payments_service import PaymentsService
from yieldfabric.utils.graphql import GraphQLMutation

from .conftest import provision_user, SEEDED_USERS


# Seeded denomination on the dev backend. If this ever stops being seeded,
# the test will fail at the deposit step with a clear token-lookup error.
SEEDED_ASSET_ID = "aud-token-asset"

# How long to wait for async MQ processing of a submitted payment before
# giving up on `accept`. Shell harness uses COMMAND_DELAY=10s between
# commands as a fixed wait; we poll instead of sleeping blind. 60s gives
# ample headroom for a healthy consumer.
ACCEPT_POLL_TIMEOUT_SEC = 60
ACCEPT_POLL_INTERVAL_SEC = 2


def _accept_with_retry(payments, payment_id, token, idempotency_key):
    """
    Try accept; if the resolver reports the payment isn't persisted yet,
    wait and retry. The idempotencyKey is reused across retries so the
    first successful call is authoritative — subsequent retries against a
    now-existent payment would return the cached success.
    """
    deadline = time.time() + ACCEPT_POLL_TIMEOUT_SEC
    last_resp = None
    while time.time() < deadline:
        accept_vars = {
            "input": {
                "paymentId": payment_id,
                "idempotencyKey": idempotency_key,
            }
        }
        resp = payments.graphql_mutation(GraphQLMutation.ACCEPT, accept_vars, token)
        last_resp = resp

        if resp.success and resp.get_data("accept", {}).get("success") is True:
            return resp

        err = (resp.get_error_message() or "").lower()
        if "not found" in err:
            # Payment not yet persisted by the instant-send consumer.
            time.sleep(ACCEPT_POLL_INTERVAL_SEC)
            continue

        # Different error — not a timing issue. Surface immediately.
        return resp

    raise AssertionError(
        f"payment {payment_id} never became acceptable within "
        f"{ACCEPT_POLL_TIMEOUT_SEC}s; last response: {last_resp.raw_response}"
    )


@pytest.fixture
def sender(config):
    """
    Seeded `issuer@yieldfabric.com` from setup.yaml. Has on-chain balance
    for the denominations seeded by setup_system.sh (including
    aud-token-asset). Fresh provisioned users do not and hit
    "ERC20: transfer amount exceeds balance" at MQ execution time.
    """
    email, password = SEEDED_USERS["issuer"]
    auth = AuthService(config)
    token = auth.login(email, password)
    if not token:
        pytest.skip(
            f"seeded user {email} is not logged-in-able; has setup_system.sh "
            f"been run on this environment?"
        )
    return {"email": email, "password": password, "token": token}


@pytest.fixture
def receiver(config):
    """
    Seeded `investor@yieldfabric.com` from setup.yaml. Receiver doesn't
    need pre-existing balance, but they DO need to exist in the auth
    service so the instant mutation can resolve `destinationId` → address.
    """
    email, password = SEEDED_USERS["investor"]
    auth = AuthService(config)
    token = auth.login(email, password)
    if not token:
        pytest.skip(
            f"seeded user {email} is not logged-in-able; has setup_system.sh "
            f"been run on this environment?"
        )
    return {"email": email, "password": password, "token": token}


def test_deposit_instant_accept_between_two_users(config, sender, receiver):
    payments = PaymentsService(config)

    # ---- Step 1: sender deposits the seeded denomination ----
    deposit_vars = {
        "input": {
            "assetId": SEEDED_ASSET_ID,
            "amount": "10",
            "idempotencyKey": f"e2e-deposit-{uuid.uuid4()}",
        }
    }
    deposit_resp = payments.graphql_mutation(
        GraphQLMutation.DEPOSIT, deposit_vars, sender["token"]
    )
    assert deposit_resp.success, (
        f"deposit GraphQL errored: {deposit_resp.get_error_message()}"
    )
    deposit_data = deposit_resp.get_data("deposit", {})
    assert deposit_data.get("success") is True, (
        f"deposit mutation returned success=false: {deposit_data}"
    )
    assert deposit_data.get("messageId"), (
        f"deposit must return messageId: {deposit_data}"
    )

    # ---- Step 2: sender sends to receiver (destinationId = receiver email) ----
    instant_vars = {
        "input": {
            "assetId": SEEDED_ASSET_ID,
            "amount": "1",
            "destinationId": receiver["email"],
            "idempotencyKey": f"e2e-instant-{uuid.uuid4()}",
        }
    }
    instant_resp = payments.graphql_mutation(
        GraphQLMutation.INSTANT, instant_vars, sender["token"]
    )
    assert instant_resp.success, (
        f"instant GraphQL errored: {instant_resp.get_error_message()}"
    )
    instant_data = instant_resp.get_data("instant", {})
    assert instant_data.get("success") is True, (
        f"instant mutation returned success=false: {instant_data}"
    )
    payment_id = instant_data.get("paymentId")
    assert payment_id, f"instant must return paymentId: {instant_data}"

    # ---- Step 3: receiver accepts the payment by paymentId ----
    # The instant-send from step 2 was queued to MQ; the payment record
    # isn't visible to accept until the consumer processes it. Poll with
    # a bounded wait rather than sleeping blind.
    accept_resp = _accept_with_retry(
        payments,
        payment_id,
        receiver["token"],
        idempotency_key=f"e2e-accept-{uuid.uuid4()}",
    )
    assert accept_resp.success, (
        f"accept GraphQL errored: {accept_resp.get_error_message()}"
    )
    accept_data = accept_resp.get_data("accept", {})
    assert accept_data.get("success") is True, (
        f"accept mutation returned success=false: {accept_data}"
    )


def test_accept_with_unknown_payment_id_is_rejected(config, sender):
    """
    Companion test: if someone tries to accept a paymentId that doesn't exist,
    the resolver must surface a GraphQL error rather than silently succeed.
    Pins that accept is not a no-op for unknown IDs.
    """
    payments = PaymentsService(config)
    bogus_payment_id = f"PAYMENT-INSTANT-nope-{uuid.uuid4()}"

    accept_vars = {"input": {"paymentId": bogus_payment_id}}
    accept_resp = payments.graphql_mutation(
        GraphQLMutation.ACCEPT, accept_vars, sender["token"]
    )

    # Either: GraphQL returns an errors array, OR accept returns success=false.
    # Both are acceptable "rejected" shapes — pin that ONE of them fired.
    rejected = (not accept_resp.success) or (
        accept_resp.get_data("accept", {}).get("success") is False
    )
    assert rejected, (
        f"unknown paymentId must be rejected, got: {accept_resp.raw_response}"
    )
