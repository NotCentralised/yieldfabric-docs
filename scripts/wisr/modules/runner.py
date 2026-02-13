"""
Shared workflow runner: preflight and auth context.
Mirrors the idea of nc_acacia.yaml where setup (participants, auth) is explicit
before running the command list.
"""

from typing import Any, Optional

from .auth import (
    check_service_running,
    deploy_issuer_account,
    get_user_id_from_profile,
    login_user,
)
from .payments import get_default_wallet_id
from .workflow_config import IssueWorkflowConfig


def issue_auth_context(config: IssueWorkflowConfig) -> dict[str, Any]:
    """
    Authenticate issuer, optionally deploy issuer/acceptor accounts, resolve entity id.
    Returns a context dict for issue workflow: jwt_token, issuer_user_id, issuer_entity_id_raw.
    Caller must check context is non-empty and handle deploy failures.
    """
    jwt_token = login_user(config.auth_service_url, config.user_email, config.password)
    if not jwt_token:
        return {}
    issuer_user_id = get_user_id_from_profile(config.auth_service_url, jwt_token)
    issuer_entity_id_raw = (
        (issuer_user_id or "").replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "").strip()
    )
    ctx = {
        "jwt_token": jwt_token,
        "issuer_user_id": issuer_user_id,
        "issuer_entity_id_raw": issuer_entity_id_raw,
    }
    if config.deploy_issuer:
        deploy_result = deploy_issuer_account(
            config.auth_service_url, config.user_email, config.password
        )
        if not deploy_result.get("success"):
            ctx["_deploy_issuer_error"] = deploy_result.get("error", "Unknown error")
            return ctx
    if config.deploy_acceptor and config.acceptor_email and config.acceptor_password:
        deploy_result = deploy_issuer_account(
            config.auth_service_url,
            config.acceptor_email,
            config.acceptor_password,
        )
        if not deploy_result.get("success"):
            ctx["_deploy_acceptor_error"] = deploy_result.get("error", "Unknown error")
            return ctx
    return ctx


def run_preflight(auth_service_url: str, pay_service_url: str) -> bool:
    """Check auth and payments services are reachable. Returns True if both ok."""
    if not check_service_running("Auth Service", auth_service_url):
        return False
    if not check_service_running("Payments Service", pay_service_url):
        return False
    return True


def payment_auth_context(
    auth_service_url: str,
    pay_service_url: str,
    acceptor_email: str,
    acceptor_password: str,
    issuer_email: Optional[str],
    issuer_password: Optional[str],
) -> dict[str, Any]:
    """
    Authenticate acceptor (required) and optionally issuer; resolve entity id and
    acceptor default wallet. Returns a context dict for payment row processing.
    Keys: acceptor_token, issuer_token (or None), issuer_entity_id_raw, acceptor_default_wallet_id.
    """
    acceptor_token = login_user(auth_service_url, acceptor_email, acceptor_password)
    if not acceptor_token:
        return {}
    entity_user_id = get_user_id_from_profile(auth_service_url, acceptor_token)
    acceptor_default_wallet_id = get_default_wallet_id(
        pay_service_url, acceptor_token, entity_id=entity_user_id
    )
    issuer_token = None
    issuer_user_id = None
    if issuer_email and issuer_password:
        issuer_token = login_user(auth_service_url, issuer_email, issuer_password)
        if issuer_token:
            issuer_user_id = get_user_id_from_profile(auth_service_url, issuer_token)
    entity_user_id = (
        issuer_user_id
        if issuer_token and issuer_user_id
        else get_user_id_from_profile(auth_service_url, acceptor_token)
    )
    issuer_entity_id_raw = (entity_user_id or "").replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "").strip()
    return {
        "acceptor_token": acceptor_token,
        "issuer_token": issuer_token,
        "issuer_user_id": issuer_user_id,
        "issuer_entity_id_raw": issuer_entity_id_raw,
        "acceptor_default_wallet_id": acceptor_default_wallet_id,
    }
