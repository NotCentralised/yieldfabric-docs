"""
E2E test fixtures.

The framework's singletons default to production URLs and don't read env vars
at import time. We configure a local-targeted `YieldFabricConfig` here and
provide fixtures that bypass setup.yaml — tests provision their own users via
`POST /auth/users` so they don't depend on seed state beyond what the live
dev backend already has (e.g., the `aud-token-asset` denomination).

Skip-clean behaviour: if the auth or payments service isn't reachable, every
test in this directory skips with a clear reason. Running without the stack
up is not an error.
"""

import os
import uuid
from typing import Tuple

import pytest
import requests

from yieldfabric import YieldFabricConfig

AUTH_URL = os.environ.get("AUTH_SERVICE_URL", "http://localhost:3000")
PAY_URL = os.environ.get("PAY_SERVICE_URL", "http://localhost:3002")


def _service_up(url: str) -> bool:
    try:
        r = requests.get(f"{url}/health", timeout=5)
        return r.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="session")
def config() -> YieldFabricConfig:
    """Session-scoped config pointing at local auth + payments services."""
    if not _service_up(AUTH_URL):
        pytest.skip(f"auth service not reachable at {AUTH_URL}")
    if not _service_up(PAY_URL):
        pytest.skip(f"payments service not reachable at {PAY_URL}")
    return YieldFabricConfig(
        pay_service_url=PAY_URL,
        auth_service_url=AUTH_URL,
    )


# Known seeded users from `yieldfabric-docs/scripts/setup.yaml`. Every test
# environment that has been bootstrapped via `setup_system.sh` will have these
# users AND — critically — they will already hold on-chain balance in the
# seeded denominations. Fresh users created via `POST /auth/users` do NOT have
# on-chain balance, so deposit/send mutations fail async with
# "ERC20: transfer amount exceeds balance" even though the GraphQL response
# says `success: true`. Use `SEEDED_USERS` for any flow test that needs the
# MQ consumer to actually execute the on-chain side of a mutation.
SEEDED_USERS = {
    # From yieldfabric-docs/scripts/setup.yaml. Passwords are NOT the ones in
    # commands.yaml — that file uses different credentials and pre-dates the
    # current setup.yaml. Always source from setup.yaml.
    "issuer": ("issuer@yieldfabric.com", "issuer_password"),
    "investor": ("investor@yieldfabric.com", "investor_password"),
    "payer": ("payer@yieldfabric.com", "payer_password"),
    "collateral": ("collateral@yieldfabric.com", "collateral_password"),
    "originator": ("originator@yieldfabric.com", "originator_password"),
}


def provision_user(role: str = "SuperAdmin") -> Tuple[str, str]:
    """
    Create a fresh user via `POST /auth/users` and return (email, password).

    USE WITH CARE: fresh users work for mutations that exercise ONLY the
    resolver/auth path (e.g., "accept an unknown paymentId is rejected")
    but fail at on-chain execution time for anything that moves tokens —
    they have no balance. For happy-path flow tests, prefer `SEEDED_USERS`.

    Default role is `SuperAdmin` because any flow that reaches the MQ
    consumer requires `CryptoOperations` permission, and SuperAdmin grants
    it. Override via the `role` kwarg for permission-boundary tests.

    The framework has no user-creation helper — that step lives in
    `setup_system.sh` and is out of scope for E2E command tests.
    """
    email = f"e2e-{uuid.uuid4()}@yf.local"
    password = f"pw-{uuid.uuid4()}"
    resp = requests.post(
        f"{AUTH_URL}/auth/users",
        json={"email": email, "password": password, "role": role},
        timeout=10,
    )
    if resp.status_code >= 400:
        raise RuntimeError(
            f"provision_user failed: status={resp.status_code} body={resp.text}"
        )
    return email, password
