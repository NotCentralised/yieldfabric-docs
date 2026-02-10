"""
Messages API: get message, list awaiting signature, wait for completion.

Used to link Python-triggered operations with manual signing in the app:
- After triggering an operation (e.g. acceptObligation), poll until the user has signed and the message completed.
- List messages awaiting signature (same as the app's "awaiting signature" view).

All endpoints are on the payments service: PAY_SERVICE_URL.
"""

import time
from typing import Any, List, Optional

import requests

from .http_client import auth_headers


def get_message(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    message_id: str,
    timeout: int = 15,
) -> dict:
    """
    GET /api/users/{user_id}/messages/{message_id}.
    Returns the message payload (id, executed, response.status, response.success, data, etc.).
    """
    url = f"{pay_service_url.rstrip('/')}/api/users/{user_id}/messages/{message_id}"
    headers = auth_headers(jwt_token)
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Get message failed ({resp.status_code}): {msg}")
    return resp.json()


def get_messages_awaiting_signature(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    timeout: int = 15,
) -> List[dict]:
    """
    GET /api/users/{user_id}/messages/awaiting-signature.
    Returns the list of messages that require manual signature (same as the app's drawer list).
    """
    url = f"{pay_service_url.rstrip('/')}/api/users/{user_id}/messages/awaiting-signature"
    headers = auth_headers(jwt_token)
    resp = requests.get(url, headers=headers, timeout=timeout)
    if resp.status_code != 200:
        try:
            err = resp.json()
            msg = err.get("error", resp.text)
        except Exception:
            msg = resp.text
        raise RuntimeError(f"Get messages awaiting signature failed ({resp.status_code}): {msg}")
    data = resp.json()
    return data if isinstance(data, list) else []


def wait_for_message_completion(
    pay_service_url: str,
    jwt_token: str,
    user_id: str,
    message_id: str,
    poll_interval_seconds: float = 2.0,
    max_wait_seconds: float = 300.0,
    timeout_per_request: int = 15,
) -> dict:
    """
    Poll GET message until executed or max_wait_seconds.
    Returns the last message payload. If completed, message has executed=True.
    On timeout, returns dict with "error" and "last" (last message payload).
    """
    start = time.monotonic()
    last: Optional[dict] = None
    while (time.monotonic() - start) < max_wait_seconds:
        try:
            last = get_message(
                pay_service_url, jwt_token, user_id, message_id, timeout=timeout_per_request
            )
        except Exception as e:
            if last is not None:
                return {"error": str(e), "last": last}
            raise
        if last.get("executed"):
            return last
        time.sleep(poll_interval_seconds)
    return {
        "error": f"Timeout waiting for message completion ({max_wait_seconds}s)",
        "last": last,
    }
