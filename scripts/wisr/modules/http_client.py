"""HTTP and GraphQL client helpers: auth headers, POST GraphQL, workflow REST."""

import json
import sys
from typing import Optional

import requests

from .console import BLUE, NC, RED, YELLOW, echo_with_color


def graphql_errors_message(data: dict) -> Optional[str]:
    """Return the first GraphQL error message from data['errors'], or None."""
    errors = data.get("errors") if isinstance(data, dict) else None
    if not errors or not isinstance(errors, list) or len(errors) == 0:
        return None
    first = errors[0]
    return first.get("message", str(first)) if isinstance(first, dict) else str(errors[0])


def auth_headers(
    jwt_token: str,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """Build headers with Bearer token and optional X-Account-Address / X-Wallet-Id."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jwt_token}",
    }
    if account_address and account_address.strip().startswith("0x"):
        headers["X-Account-Address"] = account_address.strip()
    if wallet_id and wallet_id.strip():
        headers["X-Wallet-Id"] = wallet_id.strip()
    return headers


def post_graphql(
    base_url: str,
    jwt_token: str,
    query: str,
    variables: dict,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
    timeout: int = 30,
) -> dict:
    """POST a GraphQL request; returns parsed JSON (dict)."""
    url = f"{base_url.rstrip('/')}/graphql"
    headers = auth_headers(jwt_token, account_address, wallet_id)
    response = requests.post(
        url,
        json={"query": query, "variables": variables},
        headers=headers,
        timeout=timeout,
    )
    if not response.text:
        return {}
    try:
        return response.json()
    except Exception:
        return {"error": response.text}


def post_workflow_json(
    base_url: str,
    path: str,
    json_body: dict,
    jwt_token: str,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """POST JSON to base_url + path with Bearer token; log 422; return parsed JSON or error dict."""
    url = f"{base_url.rstrip('/')}{path}"
    headers = auth_headers(jwt_token, account_address, wallet_id)
    try:
        response = requests.post(
            url,
            json=json_body,
            headers=headers,
            timeout=30,
        )
        echo_with_color(BLUE, f"  📡 Response received (HTTP {response.status_code})", file=sys.stderr)
        if not response.text:
            echo_with_color(YELLOW, "  ⚠️  Warning: Empty response body", file=sys.stderr)
        if response.status_code == 422:
            echo_with_color(YELLOW, "  ⚠️  Validation error - full response:", file=sys.stderr)
            try:
                print(json.dumps(response.json(), indent=2), file=sys.stderr)
            except Exception:
                print(response.text, file=sys.stderr)
        try:
            return response.json()
        except Exception:
            return {"error": response.text, "status_code": response.status_code}
    except Exception as e:
        echo_with_color(RED, f"  ❌ Error making request: {e}", file=sys.stderr)
        return {"error": str(e)}
