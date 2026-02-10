"""
Wallet execution mode preferences: Manual vs Automatic per message type.

Used to require manual signature in the app for messages created for a given wallet
(e.g. set AcceptObligation to Manual for a loan wallet so Python-triggered accept
shows in the app for signing).

All endpoints are on the payments service: PAY_SERVICE_URL.
"""

from typing import Any, List, Optional

import requests

from .http_client import auth_headers


# Message types supported by the payments service (must match backend enum)
VALID_MESSAGE_TYPES = (
    "HelloWorld",
    "DeployAccount",
    "CreateObligation",
    "AcceptObligation",
    "TransferObligation",
    "CancelObligation",
    "CreateSwap",
    "CompleteSwap",
    "CancelSwap",
    "RepurchaseSwap",
    "ExpireCollateral",
    "Deposit",
    "Withdraw",
    "Send",
    "Retrieve",
    "AddPolicy",
    "AddOwner",
    "RemoveOwner",
    "AddMember",
    "RemoveMember",
    "RedeemCredit",
    "Mint",
    "AddSecret",
    "Burn",
    "Transfer",
    "ComposedOperation",
)

EXECUTION_MODES = ("Manual", "Automatic")


def set_wallet_execution_mode_preference(
    pay_service_url: str,
    jwt_token: str,
    wallet_id: str,
    message_type: str,
    execution_mode: str,
    authorized_keys: Optional[List[str]] = None,
    timeout: int = 15,
) -> dict:
    """
    PUT /api/wallets/{wallet_id}/execution-mode-preferences/{message_type}.
    Set execution mode for a wallet + message type (e.g. Manual for AcceptObligation).
    execution_mode must be "Manual" or "Automatic".
    """
    wallet_id = (wallet_id or "").strip()
    message_type = (message_type or "").strip()
    execution_mode = (execution_mode or "").strip()
    if not wallet_id or not message_type:
        raise ValueError("wallet_id and message_type are required")
    if execution_mode not in EXECUTION_MODES:
        raise ValueError(f"execution_mode must be one of {EXECUTION_MODES}")
    payload = {"execution_mode": execution_mode}
    if authorized_keys is not None:
        payload["authorized_keys"] = authorized_keys
    url = f"{pay_service_url.rstrip('/')}/api/wallets/{wallet_id}/execution-mode-preferences/{message_type}"
    headers = auth_headers(jwt_token)
    resp = requests.put(url, json=payload, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Set wallet execution mode failed ({resp.status_code}): {msg}")
    return resp.json()


def get_wallet_execution_mode_preferences(
    pay_service_url: str,
    jwt_token: str,
    wallet_id: str,
    timeout: int = 15,
) -> dict:
    """
    GET /api/wallets/{wallet_id}/execution-mode-preferences.
    Returns dict with "preferences": list of { message_type, execution_mode, authorized_keys, ... }.
    """
    wallet_id = (wallet_id or "").strip()
    if not wallet_id:
        raise ValueError("wallet_id is required")
    url = f"{pay_service_url.rstrip('/')}/api/wallets/{wallet_id}/execution-mode-preferences"
    headers = auth_headers(jwt_token)
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Get wallet execution mode preferences failed ({resp.status_code}): {msg}")
    return resp.json()
