#!/usr/bin/env python3

"""
Test script for the workflow-based Issue Composed Contract API endpoint.
Processes loans from a CSV file and creates composed contracts.
Number of loans is controlled by LOAN_COUNT env var (default: 10).

Each loan uses a dedicated sub-account wallet (WLT-LOAN-{entity_id}-{loan_id}):
- The obligation is created with obligorWalletId and counterpartWalletId set to that
  sub-account so the obligor and counterpart in the contract are the sub-account.
- We pass X-Account-Address and X-Wallet-Id when calling the workflow for issue.
- Accept is requested from the sub-account (not the main issuer) by calling the
  acceptObligation GraphQL mutation with X-Account-Address and X-Wallet-Id set to
  the obligor's address and wallet_id. For the obligation to be accepted as the
  sub-account, the backend must use these headers when processing the accept
  mutation (Python-only; no backend code changes in this script).
"""

import csv
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

# ANSI color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
PURPLE = '\033[0;35m'
CYAN = '\033[0;36m'
NC = '\033[0m'  # No Color

# Action modes
ACTION_ISSUE_ONLY = "issue_only"
ACTION_ISSUE_SWAP = "issue_swap"
ACTION_ISSUE_SWAP_COMPLETE = "issue_swap_complete"
VALID_ACTION_MODES = (ACTION_ISSUE_ONLY, ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE)


def echo_with_color(color: str, message: str, file=sys.stdout):
    """Print a colored message."""
    print(f"{color}{message}{NC}", file=file)


def _graphql_errors_message(data: dict) -> Optional[str]:
    """Return the first GraphQL error message from data['errors'], or None."""
    errors = data.get("errors") if isinstance(data, dict) else None
    if not errors or not isinstance(errors, list) or len(errors) == 0:
        return None
    first = errors[0]
    return first.get("message", str(first)) if isinstance(first, dict) else str(errors[0])


def _auth_headers(
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


def _post_graphql(
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
    headers = _auth_headers(jwt_token, account_address, wallet_id)
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


def _parse_bool_env(key: str, default: bool = False) -> bool:
    """Return True if env key is true/1/yes (case-insensitive)."""
    return os.environ.get(key, "").strip().lower() in ("true", "1", "yes")


def _parse_bool_env_with_mode_default(
    key: str,
    action_mode: str,
    default_for_swap_complete: bool,
) -> bool:
    """Parse bool env; if unset and action_mode is issue_swap_complete, use default_for_swap_complete."""
    raw = os.environ.get(key, "").strip().lower()
    if raw in ("true", "1", "yes"):
        return True
    if raw in ("false", "0", "no"):
        return False
    if action_mode == ACTION_ISSUE_SWAP_COMPLETE:
        return default_for_swap_complete
    return False


def _post_workflow_json(
    base_url: str,
    path: str,
    json_body: dict,
    jwt_token: str,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """POST JSON to base_url + path with Bearer token; log 422; return parsed JSON or error dict.
    When account_address/wallet_id are provided, send as X-Account-Address and X-Wallet-Id
    so the backend can use the sub-account as signer when supported.
    """
    url = f"{base_url.rstrip('/')}{path}"
    headers = _auth_headers(jwt_token, account_address, wallet_id)
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


def load_env_files(script_dir: Path, repo_root: Path):
    """Load environment variables from .env files"""
    env_files = [
        repo_root / ".env",
        repo_root / ".env.local",
        script_dir / ".env"
    ]
    
    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"\'')
                            os.environ[key.strip()] = value
            except Exception as e:
                echo_with_color(YELLOW, f"  ⚠️  Warning: Could not load {env_file}: {e}")


def check_service_running(service_name: str, service_url: str) -> bool:
    """Check if a service is running and reachable"""
    echo_with_color(BLUE, f"  🔍 Checking if {service_name} is running...")
    
    try:
        if service_url.startswith(('http://', 'https://')):
            # Try health endpoint first, then base URL
            for url in (f"{service_url.rstrip('/')}/health", service_url.rstrip("/")):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code < 500:
                        echo_with_color(GREEN, f"    ✅ {service_name} is reachable")
                        return True
                except Exception:
                    continue
            
            echo_with_color(RED, f"    ❌ {service_name} is not reachable at {service_url}")
            return False
        else:
            # Assume it's a port number
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex(('localhost', int(service_url)))
            sock.close()
            
            if result == 0:
                echo_with_color(GREEN, f"    ✅ {service_name} is running on port {service_url}")
                return True
            else:
                echo_with_color(RED, f"    ❌ {service_name} is not running on port {service_url}")
                return False
    except Exception as e:
        echo_with_color(RED, f"    ❌ Error checking {service_name}: {e}")
        return False


def get_user_id_from_profile(auth_service_url: str, jwt_token: str) -> Optional[str]:
    """Get the current user's ID (UUID) from GET /auth/users/me. Required for deploy-account."""
    try:
        response = requests.get(
            f"{auth_service_url}/auth/users/me",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}",
            },
            timeout=15,
        )
        if response.status_code != 200:
            return None
        data = response.json()
        user = data.get("user") if isinstance(data, dict) else None
        if not user or not isinstance(user, dict):
            return None
        user_id = user.get("id")
        return str(user_id).strip() if user_id else None
    except Exception:
        return None


def deploy_user_account(
    auth_service_url: str,
    jwt_token: str,
    user_id: str,
) -> dict:
    """
    Deploy an on-chain wallet account for a user (auth service).
    Mirrors POST /auth/users/:user_id/deploy-account from user_deployment.rs.
    Caller must be the user (same as user_id) or have Admin permission.
    Returns dict with success, new_account_address, message, or error.
    """
    echo_with_color(CYAN, f"  📤 Deploying wallet account for user {user_id}...", file=sys.stderr)
    try:
        response = requests.post(
            f"{auth_service_url}/auth/users/{user_id}/deploy-account",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}",
            },
            timeout=60,
        )
        if not response.text:
            return {"success": False, "error": "Empty response"}
        try:
            data = response.json()
        except Exception:
            return {"success": False, "error": response.text}
        if response.status_code == 200:
            return {
                "success": True,
                "message": data.get("message"),
                "user_id": data.get("user_id"),
                "new_account_address": data.get("new_account_address"),
                "status": data.get("status"),
            }
        return {
            "success": False,
            "error": data.get("error", data.get("message", response.text)),
            "status_code": response.status_code,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_wallet_in_payments(
    pay_service_url: str,
    jwt_token: str,
    entity_id: str,
    address: str,
    wallet_id: str,
    name: str = "Sub-Account",
    description: str = "Additional blockchain account",
) -> dict:
    """
    Create a wallet record in the payments graph store so the wallet appears as a
    sub-account under the entity (e.g. under issuer in the UI).
    Calls the same GraphQL mutation the app uses: wallets { createWallet(input: $input) }.
    Returns dict with success, wallet (id, address, entityId), or error.
    """
    # Normalize: backend expects raw UUID for entityId, no ENTITY- prefix
    entity_id = (entity_id or "").strip().replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "")
    address = (address or "").strip()
    wallet_id = (wallet_id or "").strip()
    if not entity_id or not address or not wallet_id:
        return {"success": False, "error": "entity_id, address and wallet_id are required"}

    # Match app/backend: CreateWalletInput uses camelCase in GraphQL
    query = (
        "mutation CreateWallet($input: CreateWalletInput!) {"
        "  wallets { createWallet(input: $input) { id name address entityId createdAt deleted transactionId } }"
        "}"
    )
    variables = {
        "input": {
            "walletId": wallet_id,
            "entityId": entity_id,
            "name": (name or "Sub-Account").strip(),
            "description": (description or "Additional blockchain account").strip(),
            "walletType": "SMART_CONTRACT",
            "address": address,
        }
    }
    try:
        data = _post_graphql(pay_service_url, jwt_token, query, variables)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error", "Empty response from createWallet")}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict):
            wallets_obj = data_obj.get("wallets")
            if isinstance(wallets_obj, dict):
                w = wallets_obj.get("createWallet")
                if w is not None:
                    return {"success": True, "wallet": w if isinstance(w, dict) else {"id": wallet_id}}
        msg = _graphql_errors_message(data)
        if msg:
            return {"success": False, "error": msg}
        return {"success": False, "error": data.get("error", "Unknown createWallet failure")}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_wallet_by_id(
    pay_service_url: str,
    jwt_token: str,
    wallet_id: str,
) -> Optional[dict]:
    """
    Fetch a wallet by ID from the payments GraphQL API.
    Returns dict with id, address, entityId, name if found, else None.
    """
    wallet_id = (wallet_id or "").strip()
    if not wallet_id:
        return None
    query = (
        "query GetWalletById($id: ID!) { wallet(id: $id) { id entityId name address } }"
    )
    try:
        data = _post_graphql(pay_service_url, jwt_token, query, {"id": wallet_id})
        if not isinstance(data, dict):
            return None
        data_obj = data.get("data")
        if not isinstance(data_obj, dict):
            return None
        wallet = data_obj.get("wallet")
        if isinstance(wallet, dict) and wallet.get("id") and wallet.get("address"):
            return wallet
        return None
    except Exception:
        return None


def deploy_issuer_account(
    auth_service_url: str,
    issuer_email: str,
    issuer_password: str,
) -> dict:
    """
    Deploy the on-chain wallet account for the ISSUER_EMAIL entity.
    Logs in as issuer, resolves user_id from /auth/users/me, then calls deploy-account.
    """
    echo_with_color(CYAN, "🔐 Deploying issuer account (wallet)...", file=sys.stderr)
    token = login_user(auth_service_url, issuer_email, issuer_password)
    if not token:
        return {"success": False, "error": "Failed to login as issuer"}
    user_id = get_user_id_from_profile(auth_service_url, token)
    if not user_id:
        return {"success": False, "error": "Could not get issuer user_id from /auth/users/me"}
    return deploy_user_account(auth_service_url, token, user_id)


def login_user(auth_service_url: str, email: str, password: str) -> Optional[str]:
    """Login user and return JWT token"""
    echo_with_color(BLUE, f"  🔐 Logging in user: {email}", file=sys.stderr)
    
    services_json = ["vault", "payments"]
    payload = {
        "email": email,
        "password": password,
        "services": services_json
    }
    
    try:
        response = requests.post(
            f"{auth_service_url}/auth/login/with-services",
            json=payload,
            timeout=30
        )
        
        echo_with_color(BLUE, "    📡 Login response received", file=sys.stderr)
        
        if response.status_code == 200:
            data = response.json()
            token = data.get('token') or data.get('access_token') or data.get('jwt')
            
            if token and token != "null":
                echo_with_color(GREEN, "    ✅ Login successful", file=sys.stderr)
                return token
            else:
                echo_with_color(RED, "    ❌ No token in response", file=sys.stderr)
                echo_with_color(YELLOW, f"    Response: {response.text}", file=sys.stderr)
                return None
        else:
            echo_with_color(RED, f"    ❌ Login failed: HTTP {response.status_code}", file=sys.stderr)
            echo_with_color(YELLOW, f"    Response: {response.text}", file=sys.stderr)
            return None
    except Exception as e:
        echo_with_color(RED, f"    ❌ Login failed: {e}", file=sys.stderr)
        return None


def _issue_composed_contract_workflow(
    pay_service_url: str,
    jwt_token: str,
    name: str,
    description: str,
    obligations_json: list,
    path: str,
    request_body_extra: Optional[dict] = None,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """Shared workflow POST: build body, log, and call _post_workflow_json."""
    request_body = {
        "name": name,
        "description": description,
        "obligations": obligations_json,
    }
    if request_body_extra:
        request_body.update(request_body_extra)
    echo_with_color(BLUE, "  📋 Request body:", file=sys.stderr)
    print(json.dumps(request_body, indent=2), file=sys.stderr)
    echo_with_color(BLUE, f"  🌐 Making REST API request to: {pay_service_url.rstrip('/')}{path}", file=sys.stderr)
    return _post_workflow_json(
        pay_service_url, path, request_body, jwt_token,
        account_address=account_address, wallet_id=wallet_id,
    )


def issue_composed_contract_workflow(
    pay_service_url: str,
    jwt_token: str,
    name: str,
    description: str,
    obligations_json: list,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """Issue a composed contract workflow (obligations only, no swap)."""
    echo_with_color(CYAN, "🏦 Starting composed contract issuance workflow...", file=sys.stderr)
    return _issue_composed_contract_workflow(
        pay_service_url, jwt_token, name, description, obligations_json,
        "/api/composed_contract/issue_workflow",
        account_address=account_address, wallet_id=wallet_id,
    )


def issue_composed_contract_issue_swap_workflow(
    pay_service_url: str,
    jwt_token: str,
    name: str,
    description: str,
    obligations_json: list,
    counterparty: str,
    payment_amount: str,
    payment_denomination: str,
    deadline: Optional[str] = None,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
) -> dict:
    """Issue a composed contract and create a swap with the given counterparty."""
    echo_with_color(CYAN, "🏦 Starting composed contract issue + swap workflow...", file=sys.stderr)
    extra = {
        "counterparty": counterparty,
        "payment_amount": payment_amount,
        "payment_denomination": payment_denomination,
    }
    if deadline is not None:
        extra["deadline"] = deadline
    return _issue_composed_contract_workflow(
        pay_service_url, jwt_token, name, description, obligations_json,
        "/api/composed_contract/issue_swap_workflow",
        request_body_extra=extra,
        account_address=account_address, wallet_id=wallet_id,
    )


def accept_obligation_graphql(
    pay_service_url: str,
    jwt_token: str,
    contract_id: str,
    account_address: Optional[str] = None,
    wallet_id: Optional[str] = None,
    max_retries: int = 12,
    retry_delay_seconds: float = 2.0,
) -> dict:
    """Call acceptObligation GraphQL mutation. Uses the same sub-account that issued the loan:
    sends X-Account-Address and X-Wallet-Id headers and walletId in input so the backend accepts as that wallet.
    Call only when wallet_id is the obligor (issuing) sub-account so issue and accept use the same wallet.
    Retries on 'Contract not found' to handle MQ consumer race: contract records are updated asynchronously
    after the workflow returns."""
    query = (
        "mutation AcceptObligation($input: AcceptObligationInput!) {"
        " acceptObligation(input: $input) { success message messageId } }"
    )
    # Use composedContractId for composed contracts; contractId for single obligation contracts
    if contract_id and contract_id.startswith("COMPOSED-CONTRACT-"):
        input_payload = {"contractReference": {"composedContractId": contract_id}}
    else:
        input_payload = {"contractId": contract_id}
    if wallet_id and wallet_id.strip():
        input_payload["walletId"] = wallet_id.strip()
    variables = {"input": input_payload}
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            if attempt > 1:
                echo_with_color(BLUE, f"    ⏳ Retry {attempt}/{max_retries} for acceptObligation (contract record may not be ready yet)...", file=sys.stderr)
            data = _post_graphql(
                pay_service_url, jwt_token, query, variables,
                account_address=account_address, wallet_id=wallet_id,
            )
            if data.get("error") and "data" not in data:
                return {"success": False, "error": data.get("error", "Empty response from acceptObligation")}
            data_obj = data.get("data") if isinstance(data, dict) else None
            if isinstance(data_obj, dict) and "acceptObligation" in data_obj:
                ao = data_obj["acceptObligation"]
                result = {
                    "success": ao.get("success", False),
                    "message": ao.get("message"),
                    "messageId": ao.get("messageId"),
                    "raw": ao,
                }
                if result.get("success"):
                    return result
                err = (result.get("message") or "").lower()
                if "contract not found" in err or "not found" in err:
                    last_error = result.get("message", "Contract not found")
                    if attempt < max_retries:
                        if attempt == 1:
                            echo_with_color(BLUE, "    ⏳ Contract record not ready yet (MQ consumer race), retrying...", file=sys.stderr)
                        time.sleep(retry_delay_seconds)
                        continue
                    return {"success": False, "error": last_error}
                return result
            msg = _graphql_errors_message(data)
            if msg:
                err_lower = (msg or "").lower()
                if ("contract not found" in err_lower or "not found" in err_lower) and attempt < max_retries:
                    last_error = msg
                    if attempt == 1:
                        echo_with_color(BLUE, "    ⏳ Contract record not ready yet (MQ consumer race), retrying...", file=sys.stderr)
                    time.sleep(retry_delay_seconds)
                    continue
                return {"success": False, "error": msg}
            return {"success": False, "error": data.get("error", "Unknown acceptObligation failure")}
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)
                continue
            return {"success": False, "error": last_error}
    return {"success": False, "error": last_error or "Contract not found after retries"}


def complete_swap(
    pay_service_url: str,
    auth_service_url: str,
    acceptor_email: str,
    acceptor_password: str,
    swap_id: str,
    max_retries: int = 12,
    retry_delay_seconds: float = 2.0,
) -> dict:
    """Login as acceptor and call completeSwap GraphQL mutation (counterparty accepts the swap).
    Retries on 'Swap not found' to handle MQ consumer race: the swap record is created asynchronously
    after the workflow returns, so the first loan may succeed by timing luck while later loans fail."""
    echo_with_color(CYAN, f"  🤝 Accepting swap as counterparty ({acceptor_email})...", file=sys.stderr)
    acceptor_token = login_user(auth_service_url, acceptor_email, acceptor_password)
    if not acceptor_token:
        return {"error": f"Failed to login as acceptor {acceptor_email}", "success": False}
    for attempt in range(1, max_retries + 1):
        idempotency_key = f"complete-swap-{swap_id}-{int(time.time())}-{attempt}"
        query = (
            "mutation($input: CompleteSwapInput!) { completeSwap(input: $input) { success message "
            "accountAddress swapId completeResult messageId transactionId signature timestamp } }"
        )
        variables = {
            "input": {
                "swapId": swap_id,
                "idempotencyKey": idempotency_key,
            }
        }
        try:
            if attempt > 1:
                echo_with_color(BLUE, f"    ⏳ Retry {attempt}/{max_retries} for completeSwap (swap record may not be ready yet)...", file=sys.stderr)
            data = _post_graphql(pay_service_url, acceptor_token, query, variables)
            if data.get("error") and "data" not in data:
                return {"error": data.get("error", "Empty response from completeSwap"), "success": False}
            # GraphQL may return {"data": null, "errors": [...]} on failure; avoid "x in None"
            data_obj = data.get("data") if isinstance(data, dict) else None
            if isinstance(data_obj, dict) and "completeSwap" in data_obj:
                cs = data_obj["completeSwap"]
                result = {
                    "success": cs.get("success", False),
                    "message": cs.get("message"),
                    "messageId": cs.get("messageId"),
                    "transactionId": cs.get("transactionId"),
                    "raw": cs,
                }
                if result.get("success"):
                    return result
                # Non-success: check if retryable (swap record not yet in store)
                err = (result.get("message") or result.get("error") or "").lower()
                if "swap not found" in err or "not found" in err:
                    if attempt < max_retries:
                        time.sleep(retry_delay_seconds)
                        continue
                    return {"error": result.get("message", "Swap not found"), "success": False}
                return result
            msg = _graphql_errors_message(data)
            if msg:
                err_lower = (msg or "").lower()
                if ("swap not found" in err_lower or "not found" in err_lower) and attempt < max_retries:
                    if attempt == 1:
                        echo_with_color(BLUE, "    ⏳ Swap record not ready yet (MQ consumer race), retrying...", file=sys.stderr)
                    time.sleep(retry_delay_seconds)
                    continue
                return {"error": msg, "success": False}
            return {"error": data.get("error", "Unknown completeSwap failure"), "success": False}
        except Exception as e:
            if attempt < max_retries:
                time.sleep(retry_delay_seconds)
                continue
            return {"error": str(e), "success": False}
    return {"error": "Swap not found after retries", "success": False}


def query_swap_status(
    pay_service_url: str,
    jwt_token: str,
    swap_id: str,
) -> Optional[dict]:
    """Query swap status via GraphQL. Returns swap dict if found, else None.
    Uses byId(id) for direct lookup by swap_id (avoids listing all swaps)."""
    query = (
        "query($id: String!) { swapFlow { coreSwaps { byId(id: $id) "
        "{ id swapId status deadline createdAt } } } }"
    )
    variables = {"id": swap_id}
    try:
        data = _post_graphql(pay_service_url, jwt_token, query, variables, timeout=15)
        if data.get("error") and "data" not in data:
            return None
        # GraphQL errors surface in data.errors
        if data.get("errors"):
            return None
        data_obj = data.get("data") if isinstance(data, dict) else None
        swap = (
            data_obj.get("swapFlow", {}).get("coreSwaps", {}).get("byId")
            if isinstance(data_obj, dict)
            else None
        )
        return swap if isinstance(swap, dict) and swap.get("swapId") else None
    except Exception:
        return None


def poll_swap_completion(
    pay_service_url: str,
    auth_service_url: str,
    acceptor_email: str,
    acceptor_password: str,
    swap_id: str,
    max_attempts: int = 60,
    delay_seconds: float = 2.0,
) -> dict:
    """Poll until swap status is COMPLETED (or terminal failure). Returns {success, swap_data?, error?}."""
    echo_with_color(CYAN, f"  🔄 Polling swap completion for: {swap_id}", file=sys.stderr)
    jwt_token = login_user(auth_service_url, acceptor_email, acceptor_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {acceptor_email}"}
    debug_shown = False
    for attempt in range(1, max_attempts + 1):
        echo_with_color(BLUE, f"    📡 Attempt {attempt}/{max_attempts}: Checking swap status...", file=sys.stderr)
        swap_data = query_swap_status(pay_service_url, jwt_token, swap_id)
        if swap_data is None:
            if not debug_shown:
                debug_shown = True
                echo_with_color(YELLOW, "    ⚠️  Swap not found yet (may still be propagating)...", file=sys.stderr)
            echo_with_color(YELLOW, "    ⏳ Waiting for swap to become visible...", file=sys.stderr)
        else:
            status = (swap_data.get("status") or "").strip()
            echo_with_color(BLUE, f"    🔎 Current swap status: {status or 'unknown'}", file=sys.stderr)
            if status == "COMPLETED":
                echo_with_color(GREEN, "    ✅ Swap completed successfully!", file=sys.stderr)
                return {"success": True, "swap_data": swap_data}
            if status in ("CANCELLED", "EXPIRED", "FORFEITED"):
                echo_with_color(RED, f"    ❌ Swap ended in status: {status}", file=sys.stderr)
                return {"success": False, "error": f"Swap status: {status}", "swap_data": swap_data}
        if attempt < max_attempts:
            time.sleep(delay_seconds)
    echo_with_color(RED, f"    ❌ Swap did not complete within {max_attempts} attempts", file=sys.stderr)
    return {"success": False, "error": f"Timeout after {max_attempts} attempts"}


def mint_tokens(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    denomination: str,
    amount: str,
    policy_secret: str,
) -> dict:
    """Mint tokens via REST API (mirrors executors.sh execute_mint).
    POST /mint?asset_id=...&amount=...&policy_secret=...
    """
    echo_with_color(CYAN, f"  🪙 Minting {amount} {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/mint"
    params = {"asset_id": denomination, "amount": amount, "policy_secret": policy_secret}
    try:
        response = requests.post(
            url,
            params=params,
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=60,
        )
        data = response.json() if response.text else {}
        if data.get("status") == "success":
            mint_result = data.get("mint_result", {})
            echo_with_color(GREEN, f"    ✅ Mint successful (message_id: {mint_result.get('message_id', 'N/A')})", file=sys.stderr)
            return {"success": True, "data": data}
        err = data.get("error", response.text or "Unknown error")
        echo_with_color(RED, f"    ❌ Mint failed: {err}", file=sys.stderr)
        return {"success": False, "error": err}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Mint failed: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def burn_tokens(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    denomination: str,
    amount: str,
    policy_secret: str,
) -> dict:
    """Burn tokens via REST API (mirrors executors.sh execute_burn).
    POST /burn?asset_id=...&amount=...&policy_secret=...
    """
    echo_with_color(CYAN, f"  🔥 Burning {amount} {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/burn"
    params = {"asset_id": denomination, "amount": amount, "policy_secret": policy_secret}
    try:
        response = requests.post(
            url,
            params=params,
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=60,
        )
        data = response.json() if response.text else {}
        if data.get("status") == "success":
            burn_result = data.get("burn_result", {})
            echo_with_color(GREEN, f"    ✅ Burn successful (message_id: {burn_result.get('message_id', 'N/A')})", file=sys.stderr)
            return {"success": True, "data": data}
        err = data.get("error", response.text or "Unknown error")
        echo_with_color(RED, f"    ❌ Burn failed: {err}", file=sys.stderr)
        return {"success": False, "error": err}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Burn failed: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def deposit_tokens(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    denomination: str,
    amount: str,
    idempotency_key: str,
) -> dict:
    """Deposit tokens via GraphQL (mirrors nc_acacia.yaml / executors.sh execute_deposit).
    User credits their account with the given amount of the asset.
    """
    echo_with_color(CYAN, f"  🏦 Depositing {amount} {denomination}...")
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    query = (
        "mutation Deposit($input: DepositInput!) {"
        " deposit(input: $input) { success message accountAddress depositResult messageId timestamp } }"
    )
    variables = {
        "input": {
            "assetId": denomination,
            "amount": amount,
            "idempotencyKey": idempotency_key,
        }
    }
    try:
        data = _post_graphql(pay_service_url, jwt_token, query, variables, timeout=60)
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "deposit" in data_obj:
            dep = data_obj["deposit"]
            if dep.get("success"):
                echo_with_color(GREEN, f"    ✅ Deposit successful (message_id: {dep.get('messageId', 'N/A')})")
                return {"success": True, "data": dep}
            return {"success": False, "error": dep.get("message", "Deposit failed")}
        msg = _graphql_errors_message(data)
        return {"success": False, "error": msg or data.get("error", "Unknown deposit failure")}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Deposit failed: {e}")
        return {"success": False, "error": str(e)}


def accept_all_tokens(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    denomination: str,
    idempotency_key: str,
    obligor: Optional[str] = None,
    wallet_id: Optional[str] = None,
    account_address: Optional[str] = None,
) -> dict:
    """Accept all pending payables via GraphQL (mirrors nc_acacia.yaml payer_accept_1 pattern).
    Call as the loan account to accept payments from the investor after complete_swap.
    wallet_id: when set, ONLY accept payables for this specific account (e.g. loan wallet).
    account_address: when set with wallet_id, send as header for signing.
    """
    echo_with_color(CYAN, f"  ✅ Accepting all payables for {denomination}" + (f" (wallet {wallet_id})" if wallet_id else "") + "...")
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    query = (
        "mutation AcceptAll($input: AcceptAllInput!) {"
        " acceptAll(input: $input) { success message totalPayments acceptedCount failedCount timestamp } }"
    )
    inp: dict = {"denomination": denomination, "idempotencyKey": idempotency_key}
    if obligor:
        inp["obligor"] = obligor
    if wallet_id:
        inp["walletId"] = wallet_id
    variables = {"input": inp}
    try:
        data = _post_graphql(
            pay_service_url, jwt_token, query, variables,
            account_address=account_address, wallet_id=wallet_id,
            timeout=90,
        )
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "acceptAll" in data_obj:
            aa = data_obj["acceptAll"]
            if aa.get("success"):
                acc = aa.get("acceptedCount", 0)
                fail = aa.get("failedCount", 0)
                echo_with_color(GREEN, f"    ✅ Accept all successful (accepted: {acc}, failed: {fail})")
                return {"success": True, "data": aa}
            return {"success": False, "error": aa.get("message", "Accept all failed")}
        msg = _graphql_errors_message(data)
        return {"success": False, "error": msg or data.get("error", "Unknown accept all failure")}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Accept all failed: {e}")
        return {"success": False, "error": str(e)}


def instant_send(
    pay_service_url: str,
    auth_service_url: str,
    sender_email: str,
    sender_password: str,
    denomination: str,
    amount: str,
    destination_id: str,
) -> dict:
    """Send tokens to a destination via GraphQL instant mutation (mirrors executors.sh execute_instant).
    destination_id: entity email (e.g. investor@yieldfabric.com).
    """
    echo_with_color(CYAN, f"  ⚡ Sending {amount} {denomination} to {destination_id}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, sender_email, sender_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {sender_email}"}
    query = (
        "mutation Instant($input: InstantSendInput!) {"
        " instant(input: $input) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    )
    variables = {
        "input": {
            "assetId": denomination,
            "amount": amount,
            "destinationId": destination_id,
        }
    }
    try:
        data = _post_graphql(pay_service_url, jwt_token, query, variables, timeout=60)
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "instant" in data_obj:
            inst = data_obj["instant"]
            if inst.get("success"):
                echo_with_color(GREEN, f"    ✅ Instant send successful (message_id: {inst.get('messageId', 'N/A')})", file=sys.stderr)
                return {"success": True, "data": inst}
            return {"success": False, "error": inst.get("message", "Instant send failed")}
        msg = _graphql_errors_message(data)
        return {"success": False, "error": msg or data.get("error", "Unknown instant send failure")}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Instant send failed: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def get_total_supply(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    denomination: str,
) -> dict:
    """Get total supply via REST API (mirrors executors.sh execute_total_supply).
    GET /total_supply?asset_id=...
    """
    echo_with_color(CYAN, f"  💰 Fetching total supply for {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/total_supply"
    params = {"asset_id": denomination}
    try:
        response = requests.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {jwt_token}"},
            timeout=30,
        )
        data = response.json() if response.text else {}
        if data.get("status") == "success":
            total = data.get("total_supply", "N/A")
            echo_with_color(GREEN, f"    ✅ Total supply: {total}", file=sys.stderr)
            return {"success": True, "total_supply": total, "data": data}
        err = data.get("error", response.text or "Unknown error")
        echo_with_color(RED, f"    ❌ Total supply failed: {err}", file=sys.stderr)
        return {"success": False, "error": err}
    except Exception as e:
        echo_with_color(RED, f"    ❌ Total supply failed: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def poll_workflow_status(
    pay_service_url: str,
    workflow_id: str,
    max_attempts: int = 120,
    delay_seconds: int = 1
) -> Optional[dict]:
    """Poll workflow status until completion"""
    echo_with_color(CYAN, f"🔄 Polling workflow status for ID: {workflow_id}", file=sys.stderr)
    
    url = f"{pay_service_url.rstrip('/')}/api/workflows/{workflow_id}"
    
    for attempt in range(1, max_attempts + 1):
        echo_with_color(BLUE, f"  📡 Attempt {attempt}/{max_attempts}: GET {url}", file=sys.stderr)
        
        try:
            response = requests.get(url, timeout=30)
            
            if not response.text:
                echo_with_color(YELLOW, "  ⚠️  Empty response from status endpoint", file=sys.stderr)
            else:
                try:
                    data = response.json()
                    workflow_status = data.get('workflow_status', '')
                    current_step = data.get('current_step', '')
                    workflow_type = data.get('workflow_type', '')
                    
                    echo_with_color(BLUE, f"  🔎 Current workflow_status: {workflow_status or 'unknown'}", file=sys.stderr)
                    
                    if workflow_type and workflow_type != "null":
                        echo_with_color(CYAN, f"  📋 Workflow type: {workflow_type}", file=sys.stderr)
                    
                    if current_step and current_step != "unknown":
                        echo_with_color(CYAN, f"  📍 Current step: {current_step}", file=sys.stderr)
                    
                    if workflow_status in ("completed", "failed", "cancelled"):
                        return data
                except Exception:
                    echo_with_color(YELLOW, f"  ⚠️  Could not parse response: {response.text}", file=sys.stderr)
            
            if attempt < max_attempts:
                time.sleep(delay_seconds)
        except Exception as e:
            echo_with_color(YELLOW, f"  ⚠️  Error polling: {e}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(delay_seconds)
    
    echo_with_color(RED, f"  ❌ Workflow did not complete within {max_attempts} attempts", file=sys.stderr)
    return None


def convert_currency_to_wei(currency_str: str) -> str:
    """Convert currency string to wei-like format (18 decimals)
    Input: "$31,817.59" -> Output: "31817590000000000000000"
    """
    # Remove $ and commas
    cleaned = re.sub(r'[\$,]', '', currency_str)
    # Convert to float, multiply by 10^18, convert to int, then string
    amount = float(cleaned)
    wei_amount = int(amount * 10**18)
    return str(wei_amount)


def convert_date_to_iso(date_str: str) -> str:
    """Convert date from M/D/YY format to ISO format
    Input: "2/12/32" -> Output: "2032-02-12T23:59:59Z"
    Assumes 2-digit years are in 2000-2099 range for loan maturity dates
    """
    parts = date_str.split('/')
    if len(parts) != 3:
        raise ValueError(f"Invalid date format: {date_str}")
    
    month, day, year = parts
    
    # Convert 2-digit year to 4-digit
    year_int = int(year)
    if len(year) == 1:
        year = f"200{year_int}"
    elif len(year) == 2:
        year = f"20{year_int}"
    
    # Format with leading zeros
    month = f"{int(month):02d}"
    day = f"{int(day):02d}"
    
    return f"{year}-{month}-{day}T23:59:59Z"


def safe_get(row: list, index: int, default: str = "") -> str:
    """Safely get a value from a CSV row, stripping quotes"""
    if index < len(row):
        return row[index].strip('"')
    return default


def extract_loan_data(row: list) -> dict:
    """Extract all loan data from CSV row into a dictionary
    CSV column indices based on header:
    0: Loan ID, 1: Initial Amount, 2: Rate, 3: Settlement, 4: Maturity, 5: Term, 6: # PMT left,
    7: Prin. Out, 8: Accrued, 9: Fee, 10: Unpaid Int, 11: Current Value, 12: Arrears, 13: Arrears Bal,
    14: # days late, 15: State, 16: Secured, 17: SecurityType, 18: VedaCreditScore,
    19: IncomeAmount, 20: MortgageAmount, 21: MortgageFrequency, 22: RentAmount, 23: RentFrequency,
    24: OtherLoanAmount, 25: OtherLoanFrequency, 26: TotalAssets, 27: TotalLiabilities,
    28: EmploymentMonths, 29: EmploymentStatus, 30: PreviousEmploymentMonths,
    31: CurrentAddressState, 32: CurrentAddressPostcode, 33: ResidencyMonths, 34: ResidencyStatus,
    35: MaritalStatus, 36: Age, 37: LoanPurpose, 38: IsJointApplication, 39: Credit Sense Supplied,
    40: BrokerId, 41: AddedDateLocal, 42: ApprovedDateLocal, 43: Occupation, 44: Date Of Birth,
    45: Net Surplus Ratio, 46: Surplus, 47: Loan Amount Requested, 48: Term Requested,
    49: Rate Discount, 50: Assignment Date, 51: Next Pay Date, 52: Payment Frequency,
    53: PMT, 54: Referrer/Broker, 55: Asset Code, 56: Vehicle Category, 57: Residual,
    58: Vehicle Age (years), 59: Manufacturer, 60: LVR, 61: Hardship, 62: Extension Receivable,
    63: Remaining loan term, 64: Updated Maturity Date, 65: Total Term
    """
    data = {
        # Basic loan information (required fields)
        "loanId": safe_get(row, 0),
        "initialAmount": safe_get(row, 1),
        "rate": safe_get(row, 2),
        "settlement": safe_get(row, 3),
        "maturity": safe_get(row, 4),
        "term": safe_get(row, 5),
        "pmtLeft": safe_get(row, 6),
        "principalOutstanding": safe_get(row, 7),
        "accrued": safe_get(row, 8),
        "fee": safe_get(row, 9),
        "unpaidInt": safe_get(row, 10),
        "currentValue": safe_get(row, 11),
        "arrears": safe_get(row, 12),
        "arrearsBal": safe_get(row, 13),
        "daysLate": safe_get(row, 14),
        
        # Location and address data
        "state": safe_get(row, 15),
        "currentAddressState": safe_get(row, 31),
        "currentAddressPostcode": safe_get(row, 32),
        "residencyMonths": safe_get(row, 33),
        "residencyStatus": safe_get(row, 34),
        
        # Credit information
        "vedaCreditScore": safe_get(row, 18),
        "incomeAmount": safe_get(row, 19),
        "mortgageAmount": safe_get(row, 20),
        "mortgageFrequency": safe_get(row, 21),
        "rentAmount": safe_get(row, 22),
        "rentFrequency": safe_get(row, 23),
        "otherLoanAmount": safe_get(row, 24),
        "otherLoanFrequency": safe_get(row, 25),
        "totalAssets": safe_get(row, 26),
        "totalLiabilities": safe_get(row, 27),
        "employmentMonths": safe_get(row, 28),
        "employmentStatus": safe_get(row, 29),
        "previousEmploymentMonths": safe_get(row, 30),
        "maritalStatus": safe_get(row, 35),
        "age": safe_get(row, 36),
        "loanPurpose": safe_get(row, 37),
        "isJointApplication": safe_get(row, 38),
        "creditSenseSupplied": safe_get(row, 39),
        
        # Additional loan details
        "secured": safe_get(row, 16),
        "securityType": safe_get(row, 17),
        "brokerId": safe_get(row, 40),
        "addedDateLocal": safe_get(row, 41),
        "approvedDateLocal": safe_get(row, 42),
        "occupation": safe_get(row, 43),
        "dateOfBirth": safe_get(row, 44),
        "netSurplusRatio": safe_get(row, 45),
        "surplus": safe_get(row, 46),
        "loanAmountRequested": safe_get(row, 47),
        "termRequested": safe_get(row, 48),
        "rateDiscount": safe_get(row, 49),
        "assignmentDate": safe_get(row, 50),
        "nextPayDate": safe_get(row, 51),
        "paymentFrequency": safe_get(row, 52),
        "pmt": safe_get(row, 53),
        "referrerBroker": safe_get(row, 54),
        "assetCode": safe_get(row, 55),
        "vehicleCategory": safe_get(row, 56),
        "residual": safe_get(row, 57),
        "vehicleAge": safe_get(row, 58),
        "manufacturer": safe_get(row, 59),
        "lvr": safe_get(row, 60),
        "hardship": safe_get(row, 61),
        "extensionReceivable": safe_get(row, 62),
        "remainingLoanTerm": safe_get(row, 63),
        "updatedMaturityDate": safe_get(row, 64),
        "totalTerm": safe_get(row, 65),
    }
    
    # Remove empty values to keep JSON clean
    return {k: v for k, v in data.items() if v}


def _print_usage() -> None:
    """Print help text for the script."""
    print("Usage: issue_workflow.py [username] [password] [csv_file] [action_mode]")
    print("   or: issue_workflow.py [csv_file]")
    print()
    print("Arguments:")
    print("  username     User email for authentication (default: issuer@yieldfabric.com)")
    print("  password     User password for authentication (default: issuer_password)")
    print("  csv_file     Path to CSV file with loan data (default: wisr_loans_20250831.csv)")
    print("  action_mode  One of: issue_only | issue_swap | issue_swap_complete (default: issue_only)")
    print("                issue_only           - Create composed contract with obligations only")
    print("                issue_swap           - Create contract then create swap with SWAP_COUNTERPARTY")
    print("                issue_swap_complete  - Same as issue_swap then acceptor completes each swap (requires ACCEPTOR_EMAIL/PASSWORD)")
    print()
    print("Note: If the first argument is a CSV file (ends with .csv or exists as a file),")
    print("      it will be treated as the CSV file path, and username/password will use")
    print("      environment variables or defaults.")
    print()
    print("Environment variables (used as fallback if arguments not provided):")
    print("  ISSUER_EMAIL        Issuer email for authentication (alias: USER_EMAIL)")
    print("  ISSUER_PASSWORD     Issuer password for authentication (alias: PASSWORD)")
    print("  PAY_SERVICE_URL     Payments service URL (default: https://pay.yieldfabric.com)")
    print("  AUTH_SERVICE_URL    Auth service URL (default: https://auth.yieldfabric.com)")
    print("  DENOMINATION        Token denomination (default: aud-token-asset)")
    print("  COUNTERPART         Obligation counterparty email (default: issuer@yieldfabric.com)")
    print("  LOAN_COUNT          Max number of loans to process from CSV (default: 10)")
    print("  ACTION_MODE         issue_only | issue_swap | issue_swap_complete (default: issue_only)")
    print("  SWAP_COUNTERPARTY   Swap counterparty when action_mode=issue_swap (default: originator@yieldfabric.com)")
    print("  PAYMENT_AMOUNT      Expected payment from swap counterparty (default: obligation notional)")
    print("  PAYMENT_DENOMINATION Payment denomination for swap (default: DENOMINATION)")
    print("  DEADLINE            Swap deadline ISO date (default: obligation maturity)")
    print("  ACCEPTOR_EMAIL      If set with issue_swap: user that accepts/completes the swap (counterparty)")
    print("  ACCEPTOR_PASSWORD   Password for ACCEPTOR_EMAIL")
    print("  DEPLOY_ISSUER_ACCOUNT   If set (true/1/yes): deploy issuer's on-chain wallet. With issue_swap_complete, defaults to true unless set to false.")
    print("  DEPLOY_ACCEPTOR_ACCOUNT If set (true/1/yes): deploy acceptor's on-chain wallet. With issue_swap_complete, defaults to true unless set to false.")
    print("  DEPLOY_ACCOUNT_PER_LOAN If set (true/1/yes): deploy one new wallet per loan under the issuer entity (same issuer, additional wallets). Defaults to true for issue_swap / issue_swap_complete.")
    print("  MINT_BEFORE_LOANS      If set (true/1/yes): mint loan amount as ACCEPTOR_EMAIL (investor) per loan. Requires ACCEPTOR_EMAIL, ACCEPTOR_PASSWORD, POLICY_SECRET (issue_swap flows only).")
    print("  BURN_AFTER_LOANS       If set (true/1/yes) with POLICY_SECRET and BURN_AMOUNT: burn tokens after processing loans.")
    print("  BURN_AMOUNT            Amount to burn when BURN_AFTER_LOANS=true (e.g. 5).")
    print("  POLICY_SECRET          Policy secret for mint/burn (required for MINT_BEFORE_LOANS or BURN_AFTER_LOANS).")
    print()
    print("Description:")
    print("  Processes up to LOAN_COUNT loans from the CSV file (default 10) and creates a composed contract")
    print("  for each loan with a single obligation containing:")
    print("    - Loan ID as contract identifier")
    print("    - Principal Outstanding as payment amount")
    print("    - Maturity date as payment due date")
    print("    - Issuer as obligor")
    print("  With action_mode=issue_swap, also creates a swap with SWAP_COUNTERPARTY (e.g. originator).")
    print("  If ACCEPTOR_EMAIL is set with issue_swap, that user will accept/complete each swap.")
    print("  With action_mode=issue_swap_complete, each swap is created and then accepted (ACCEPTOR_EMAIL/PASSWORD required).")
    print("  With DEPLOY_ISSUER_ACCOUNT=true, the issuer's on-chain wallet is deployed via auth service before running workflows.")
    print("  With DEPLOY_ACCEPTOR_ACCOUNT=true, the acceptor's (counterparty) wallet is deployed so completeSwap can succeed.")
    print("  With DEPLOY_ACCOUNT_PER_LOAN=true, one new wallet is deployed under the issuer entity before each loan (issuer gets multiple wallets, one per loan).")
    print()
    print("Examples:")
    print("  python3 issue_workflow.py")
    print("  python3 issue_workflow.py wisr_loans_20250831.csv")
    print("  python3 issue_workflow.py user@example.com mypassword")
    print("  python3 issue_workflow.py user@example.com mypassword /path/to/loans.csv issue_swap")
    print("  ACTION_MODE=issue_swap SWAP_COUNTERPARTY=originator@yieldfabric.com python3 issue_workflow.py")
    print("  ACTION_MODE=issue_swap ACCEPTOR_EMAIL=originator@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py")
    print("  ACTION_MODE=issue_swap_complete ACCEPTOR_EMAIL=originator@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py")
    print("  ISSUER_EMAIL=issuer@yieldfabric.com ISSUER_PASSWORD=secret python3 issue_workflow.py")
    print("  DEPLOY_ISSUER_ACCOUNT=true python3 issue_workflow.py   # deploy issuer wallet first")
    print("  DEPLOY_ACCEPTOR_ACCOUNT=true python3 issue_workflow.py   # deploy acceptor (investor) wallet for completeSwap")
    print("  DEPLOY_ACCOUNT_PER_LOAN=false python3 issue_workflow.py   # disable one wallet per loan under issuer (default: on for issue_swap)")
    print("  MINT_BEFORE_LOANS=true ACCEPTOR_EMAIL=... ACCEPTOR_PASSWORD=... POLICY_SECRET=xxx python3 issue_workflow.py   # mint as investor per loan")
    print("  BURN_AFTER_LOANS=true BURN_AMOUNT=5 POLICY_SECRET=xxx python3 issue_workflow.py   # burn after processing")


def _parse_cli_args(script_dir: Path) -> tuple:
    """Parse argv and env into (user_email, password, csv_file, action_mode)."""
    args = sys.argv[1:]
    env_user_email = (
        os.environ.get("ISSUER_EMAIL", "").strip() or os.environ.get("USER_EMAIL", "").strip()
    )
    env_password = (
        os.environ.get("ISSUER_PASSWORD", "").strip() or os.environ.get("PASSWORD", "").strip()
    )
    env_action_mode = os.environ.get("ACTION_MODE", "").strip().lower() or ACTION_ISSUE_ONLY

    csv_file = None
    user_email = None
    password = None
    action_mode = None

    if len(args) >= 1:
        first_arg = args[0]
        csv_path = Path(first_arg)
        if first_arg.endswith(".csv") or csv_path.exists():
            csv_file = first_arg
            if len(args) >= 2:
                action_mode = args[1].strip().lower()
        elif "@" in first_arg:
            user_email = first_arg
            if len(args) >= 2:
                password = args[1]
            if len(args) >= 3:
                csv_file = args[2]
            if len(args) >= 4:
                action_mode = args[3].strip().lower()
        else:
            user_email = first_arg
            if len(args) >= 2:
                password = args[1]
            if len(args) >= 3:
                csv_file = args[2]
            if len(args) >= 4:
                action_mode = args[3].strip().lower()

    user_email = user_email or env_user_email or "none"
    password = password or env_password or "none"
    if not action_mode or action_mode not in VALID_ACTION_MODES:
        action_mode = env_action_mode if env_action_mode in VALID_ACTION_MODES else ACTION_ISSUE_ONLY
    if not csv_file:
        csv_file = str(script_dir / "wisr_loans_20250831.csv")
    csv_path = Path(csv_file)
    if not csv_path.is_absolute():
        if (script_dir / csv_path).exists():
            csv_file = str(script_dir / csv_path)
        elif csv_path.exists():
            csv_file = str(csv_path.resolve())
    return (user_email, password, csv_file, action_mode)


def main():
    """Main entry: load env, parse args, run preflight, process loans."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        _print_usage()
        return 0

    user_email, password, csv_file, action_mode = _parse_cli_args(script_dir)

    if not Path(csv_file).exists():
        echo_with_color(RED, f"❌ CSV file not found: {csv_file}")
        return 1

    # --- Configuration ---
    pay_service_url = os.environ.get("PAY_SERVICE_URL", "https://pay.yieldfabric.com")
    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "https://auth.yieldfabric.com")
    denomination = os.environ.get("DENOMINATION", "aud-token-asset")
    counterpart = os.environ.get("COUNTERPART", "issuer@yieldfabric.com")
    swap_counterparty = os.environ.get("SWAP_COUNTERPARTY", "originator@yieldfabric.com")
    payment_denomination = os.environ.get("PAYMENT_DENOMINATION", denomination)
    env_payment_amount = os.environ.get("PAYMENT_AMOUNT", "")
    env_deadline = os.environ.get("DEADLINE", "")
    # Optional: user that accepts/completes the swap (counterparty); when set, we call completeSwap after each issue_swap
    acceptor_email = os.environ.get('ACCEPTOR_EMAIL', '').strip()
    acceptor_password = os.environ.get('ACCEPTOR_PASSWORD', '').strip()
    try:
        max_loans = int(os.environ.get('LOAN_COUNT', '10').strip())
        if max_loans < 1:
            max_loans = 10
    except ValueError:
        max_loans = 10
    
    echo_with_color(CYAN, "🚀 Starting Issue Composed Contract WorkFlow API Test - Processing Loans from CSV")
    print()
    
    echo_with_color(BLUE, "📋 Configuration:")
    echo_with_color(BLUE, f"  API Base URL: {pay_service_url}")
    echo_with_color(BLUE, f"  Auth Service: {auth_service_url}")
    echo_with_color(BLUE, f"  User (Initiator): {user_email}")
    echo_with_color(BLUE, f"  Obligation counterpart: {counterpart}")
    echo_with_color(BLUE, f"  Denomination: {denomination}")
    echo_with_color(BLUE, f"  CSV File: {csv_file}")
    echo_with_color(BLUE, f"  Max loans to process: {max_loans}")
    echo_with_color(PURPLE, f"  Action mode: {action_mode}")
    deploy_issuer = _parse_bool_env("DEPLOY_ISSUER_ACCOUNT") or _parse_bool_env_with_mode_default(
        "DEPLOY_ISSUER_ACCOUNT", action_mode, default_for_swap_complete=True
    )
    deploy_acceptor = (_parse_bool_env("DEPLOY_ACCEPTOR_ACCOUNT") or _parse_bool_env_with_mode_default(
        "DEPLOY_ACCEPTOR_ACCOUNT", action_mode, default_for_swap_complete=True
    )) and bool(acceptor_email and acceptor_password)
    deploy_per_loan = _parse_bool_env("DEPLOY_ACCOUNT_PER_LOAN") or (
        action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE)
        and os.environ.get("DEPLOY_ACCOUNT_PER_LOAN", "").strip().lower() not in ("false", "0", "no")
    )
    if deploy_issuer:
        echo_with_color(CYAN, "  Deploy issuer account: yes (before workflows)" + (" [default for issue_swap_complete]" if not _parse_bool_env("DEPLOY_ISSUER_ACCOUNT") else ""))
    if deploy_acceptor:
        echo_with_color(CYAN, "  Deploy acceptor account: yes (before workflows)" + (" [default for issue_swap_complete]" if not _parse_bool_env("DEPLOY_ACCEPTOR_ACCOUNT") else ""))
    if deploy_per_loan:
        echo_with_color(CYAN, "  Deploy one wallet per loan under issuer entity: yes" + (" [default for issue_swap/issue_swap_complete]" if not _parse_bool_env("DEPLOY_ACCOUNT_PER_LOAN") else ""))
    if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
        if action_mode == ACTION_ISSUE_SWAP_COMPLETE and (not acceptor_email or not acceptor_password):
            echo_with_color(RED, "❌ ACTION_MODE=issue_swap_complete requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD")
            return 1
        echo_with_color(BLUE, f"  Swap counterparty: {swap_counterparty}")
        echo_with_color(BLUE, f"  Payment denomination (swap): {payment_denomination}")
        if env_payment_amount:
            echo_with_color(BLUE, f"  Payment amount (swap, from env): {env_payment_amount}")
        else:
            echo_with_color(BLUE, "  Payment amount (swap): obligation notional (per loan)")
        if env_deadline:
            echo_with_color(BLUE, f"  Deadline (swap, from env): {env_deadline}")
        else:
            echo_with_color(BLUE, "  Deadline (swap): obligation maturity (per loan)")
        if acceptor_email:
            echo_with_color(BLUE, f"  Acceptor (will complete swap): {acceptor_email}")
        else:
            echo_with_color(BLUE, "  Acceptor: (none - swap will remain pending)")
    mint_before_env = _parse_bool_env("MINT_BEFORE_LOANS")
    burn_after_env = _parse_bool_env("BURN_AFTER_LOANS")
    policy_secret = os.environ.get("POLICY_SECRET", "").strip()
    burn_amount = os.environ.get("BURN_AMOUNT", "").strip()
    if mint_before_env:
        if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE) and policy_secret and acceptor_email and acceptor_password:
            echo_with_color(CYAN, f"  Mint before loans: yes (as investor {acceptor_email}, per loan)")
        elif action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE) and (not acceptor_email or not acceptor_password):
            echo_with_color(RED, "  MINT_BEFORE_LOANS requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD (mint runs as investor)")
            return 1
        elif action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
            echo_with_color(YELLOW, "  Mint before loans: yes but POLICY_SECRET missing; will skip mint")
        else:
            echo_with_color(YELLOW, "  Mint before loans: yes but only applies to issue_swap/issue_swap_complete; will skip")
    if burn_after_env:
        echo_with_color(CYAN, f"  Burn after loans: yes (amount: {burn_amount or 'N/A'})")
    print()
    
    # --- Preflight ---
    if not check_service_running("Auth Service", auth_service_url):
        echo_with_color(RED, f"❌ Auth service is not reachable at {auth_service_url}")
        return 1
    
    if not check_service_running("Payments Service", pay_service_url):
        echo_with_color(RED, f"❌ Payments service is not reachable at {pay_service_url}")
        echo_with_color(YELLOW, "Please start the payments service:")
        print("   Local: cd ../yieldfabric-payments && cargo run")
        echo_with_color(BLUE, f"   REST API endpoint will be available at: {pay_service_url}/api/composed_contract/issue_workflow")
        return 1
    
    # Check if the endpoint exists (basic check)
    try:
        response = requests.post(
            f"{pay_service_url.rstrip('/')}/api/composed_contract/issue_workflow",
            json={},
            timeout=5
        )
        if response.status_code == 404:
            echo_with_color(YELLOW, "⚠️  Warning: Endpoint returned 404. The server may need to be restarted to pick up the new routes.")
            echo_with_color(YELLOW, "   Make sure the server was built with the latest code including composed_contract_issue workflow.")
            print()
    except Exception:
        pass  # Ignore errors in endpoint check
    
    print()
    
    # --- Auth & deploy ---
    echo_with_color(CYAN, "🔐 Authenticating...")
    jwt_token = login_user(auth_service_url, user_email, password)
    if not jwt_token:
        echo_with_color(RED, f"❌ Failed to get JWT token for user: {user_email}")
        return 1
    
    echo_with_color(GREEN, f"  ✅ JWT token obtained (first 50 chars): {jwt_token[:50]}...")
    print()
    
    # Deploy issuer's on-chain wallet when requested (flags already parsed above)
    if deploy_issuer:
        deploy_result = deploy_issuer_account(auth_service_url, user_email, password)
        if deploy_result.get("success"):
            addr = deploy_result.get("new_account_address") or "N/A"
            echo_with_color(GREEN, f"  ✅ Issuer account deployed: {addr}")
        else:
            echo_with_color(RED, f"  ❌ Issuer account deployment failed: {deploy_result.get('error', 'Unknown error')}")
            return 1
        print()
    
    # Deploy acceptor's on-chain wallet when requested (flags already parsed above)
    if deploy_acceptor:
        echo_with_color(CYAN, "🔐 Deploying acceptor account (wallet)...", file=sys.stderr)
        deploy_result = deploy_issuer_account(auth_service_url, acceptor_email, acceptor_password)
        if deploy_result.get("success"):
            addr = deploy_result.get("new_account_address") or "N/A"
            echo_with_color(GREEN, f"  ✅ Acceptor account deployed: {addr}")
        else:
            echo_with_color(RED, f"  ❌ Acceptor account deployment failed: {deploy_result.get('error', 'Unknown error')}")
            return 1
        print()
    
    # Resolve issuer entity for loan wallet ids (WLT-LOAN-{entity_id}-{loan_id}) and for per-loan deploy when enabled
    issuer_user_id = get_user_id_from_profile(auth_service_url, jwt_token)
    issuer_entity_id_raw = (issuer_user_id or "").replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "").strip()
    if deploy_per_loan:
        if not issuer_user_id:
            echo_with_color(YELLOW, "  ⚠️  DEPLOY_ACCOUNT_PER_LOAN enabled but could not get issuer user_id; skipping per-loan deploy")
            deploy_per_loan = False
        else:
            echo_with_color(CYAN, f"  📌 Deploy one new wallet per loan under issuer entity (issuer user_id: {issuer_user_id[:8]}...)")
            print()
    
    # --- Process loans ---
    echo_with_color(CYAN, f"📖 Reading loans from CSV file (max {max_loans})...")
    loan_count = 0
    success_count = 0
    fail_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            # Skip header
            next(reader, None)
            
            for row in reader:
                if loan_count >= max_loans:
                    break
                
                loan_count += 1
                
                # Parse loan data
                if len(row) < 8:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping loan {loan_count}: insufficient columns")
                    fail_count += 1
                    continue
                
                # Extract basic required fields
                loan_id = safe_get(row, 0)
                prin_out = safe_get(row, 7)
                maturity = safe_get(row, 4)
                
                if not loan_id or not prin_out or not maturity:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping loan {loan_count}: missing required data")
                    fail_count += 1
                    continue
                
                # Extract all loan data for the data field
                loan_data = extract_loan_data(row)
                
                print()
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                echo_with_color(CYAN, f"📦 Processing Loan {loan_count}/{max_loans}: ID={loan_id}")
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                print()
                
                # Convert currency to wei format
                try:
                    amount_wei = convert_currency_to_wei(prin_out)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ Error converting currency: {e}")
                    fail_count += 1
                    continue
                
                # Convert date to ISO format
                try:
                    maturity_iso = convert_date_to_iso(maturity)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ Error converting date: {e}")
                    fail_count += 1
                    continue
                
                echo_with_color(BLUE, "  Loan Details:")
                echo_with_color(BLUE, f"    ID: {loan_id}")
                echo_with_color(BLUE, f"    Initial Amount: {loan_data.get('initialAmount', 'N/A')}")
                echo_with_color(BLUE, f"    Rate: {loan_data.get('rate', 'N/A')}%")
                echo_with_color(BLUE, f"    Principal Outstanding: {prin_out} ({amount_wei} wei)")
                echo_with_color(BLUE, f"    Maturity Date: {maturity} -> {maturity_iso}")
                echo_with_color(BLUE, f"    Term: {loan_data.get('term', 'N/A')} months")
                echo_with_color(BLUE, f"    PMT Left: {loan_data.get('pmtLeft', 'N/A')}")
                print()
                
                # Mint and deposit loan amount as acceptor (investor) for each loan when MINT_BEFORE_LOANS=true (issue_swap flows only)
                # Mint runs as ACCEPTOR_EMAIL; then same user deposits the same amount (per nc_acacia.yaml investor_deposit pattern).
                if mint_before_env and policy_secret and action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                    if not acceptor_email or not acceptor_password:
                        echo_with_color(RED, f"  ❌ MINT_BEFORE_LOANS requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD (mint runs as investor)")
                        fail_count += 1
                        continue
                    echo_with_color(CYAN, f"  🪙 Minting loan amount as investor ({acceptor_email}) for loan {loan_id}...")
                    mint_res = mint_tokens(
                        pay_service_url, auth_service_url, acceptor_email, acceptor_password,
                        denomination, amount_wei, policy_secret,
                    )
                    if not mint_res.get("success"):
                        echo_with_color(RED, f"  ❌ Mint failed for loan {loan_id}: {mint_res.get('error', 'Unknown error')}")
                        fail_count += 1
                        continue
                    echo_with_color(GREEN, f"  ✅ Minted {prin_out} to {acceptor_email}")
                    echo_with_color(CYAN, f"  🏦 Depositing {prin_out} as {acceptor_email}...")
                    idemp_key = f"deposit-loan-{loan_id}-{int(time.time() * 1000)}"
                    dep_res = deposit_tokens(
                        pay_service_url, auth_service_url, acceptor_email, acceptor_password,
                        denomination, amount_wei, idemp_key,
                    )
                    if not dep_res.get("success"):
                        echo_with_color(RED, f"  ❌ Deposit failed for loan {loan_id}: {dep_res.get('error', 'Unknown error')}")
                        fail_count += 1
                        continue
                    echo_with_color(GREEN, f"  ✅ Deposited {prin_out} as {acceptor_email}")
                    print()
                
                # Use wallet WLT-LOAN-{entity_id}-{loan_id}: create only if it doesn't exist, then use it to issue the loan
                obligor_wallet_id_for_loan = None
                obligor_address_for_loan = None
                if issuer_entity_id_raw:
                    sanitized_loan_id = re.sub(r"[^a-zA-Z0-9-]", "-", str(loan_id)).strip("-") or "loan"
                    loan_wallet_id = f"WLT-LOAN-{issuer_entity_id_raw}-{sanitized_loan_id}"
                    existing_wallet = get_wallet_by_id(pay_service_url, jwt_token, loan_wallet_id)
                    if existing_wallet:
                        echo_with_color(GREEN, f"  ✅ Using existing wallet for loan {loan_id}: {loan_wallet_id}")
                        obligor_wallet_id_for_loan = loan_wallet_id
                        obligor_address_for_loan = (existing_wallet.get("address") or "").strip()
                    elif deploy_per_loan and issuer_user_id:
                        echo_with_color(CYAN, f"  🔐 Creating new wallet for loan {loan_id}: {loan_wallet_id}...", file=sys.stderr)
                        per_loan_result = deploy_user_account(auth_service_url, jwt_token, issuer_user_id)
                        if per_loan_result.get("success"):
                            addr = (per_loan_result.get("new_account_address") or "").strip()
                            if not addr or addr == "N/A" or not addr.startswith("0x"):
                                echo_with_color(YELLOW, f"  ⚠️  Deploy succeeded but no valid address for loan {loan_id}; skipping wallet registration")
                            else:
                                echo_with_color(GREEN, f"  ✅ New wallet for loan {loan_id}: {addr}")
                                create_result = create_wallet_in_payments(
                                    pay_service_url,
                                    jwt_token,
                                    issuer_entity_id_raw,
                                    addr,
                                    loan_wallet_id,
                                    name=f"Loan {loan_id}",
                                    description=f"Wallet for loan ID {loan_id}",
                                )
                                if create_result.get("success"):
                                    echo_with_color(GREEN, f"  ✅ Registered wallet in payments: {loan_wallet_id}")
                                    obligor_wallet_id_for_loan = loan_wallet_id
                                    obligor_address_for_loan = addr
                                else:
                                    err_msg = create_result.get("error", "Unknown")
                                    echo_with_color(YELLOW, f"  ⚠️  Could not register wallet in payments: {err_msg}")
                        else:
                            echo_with_color(YELLOW, f"  ⚠️  Per-loan deploy failed for loan {loan_id}: {per_loan_result.get('error', 'Unknown error')} (continuing)")
                    else:
                        echo_with_color(YELLOW, f"  ⚠️  No existing wallet {loan_wallet_id}; deploy_per_loan disabled — obligor must be sub-account, skipping loan")
                if not obligor_wallet_id_for_loan:
                    fail_count += 1
                    continue
                if not obligor_address_for_loan:
                    obligor_wallet = get_wallet_by_id(pay_service_url, jwt_token, obligor_wallet_id_for_loan)
                    obligor_address_for_loan = (obligor_wallet.get("address") or "").strip() if obligor_wallet else ""
                print()
                
                # Build comprehensive data object with all loan information (obligor = sub-account wallet only)
                obligation_data = {
                    "name": f"Loan {loan_id}",
                    "description": f"Loan obligation for loan ID {loan_id}",
                    **loan_data  # Include all extracted loan data
                }
                
                # Build single obligation JSON for this loan; obligor and counterpart both use sub-account (loan wallet)
                # Use counterpartWalletId = obligor wallet so message counterpart = obligor address (same as obligor)
                obligation = {
                    "counterpartWalletId": obligor_wallet_id_for_loan,
                    "denomination": denomination,
                    "obligorWalletId": obligor_wallet_id_for_loan,
                    "notional": amount_wei,
                    "expiry": maturity_iso,
                    "data": obligation_data,
                    "initialPayments": {
                        "amount": amount_wei,
                        "denomination": denomination,
                        "payments": [{
                            "oracleAddress": None,
                            "oracleOwner": None,
                            "oracleKeySender": None,
                            "oracleValueSenderSecret": None,
                            "oracleKeyRecipient": None,
                            "oracleValueRecipientSecret": None,
                            "unlockSender": maturity_iso,
                            "unlockReceiver": maturity_iso,
                            "linearVesting": None
                        }]
                    }
                }
                obligations_array = [obligation]
                contract_name = f"Loan Contract {loan_id}"
                contract_description = f"Composed contract for loan ID {loan_id}"
                
                if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                    payment_amount = env_payment_amount if env_payment_amount else amount_wei
                    deadline = env_deadline if env_deadline else maturity_iso
                    echo_with_color(CYAN, "📤 Calling issue + swap composed contract workflow endpoint...")
                    start_response = issue_composed_contract_issue_swap_workflow(
                        pay_service_url,
                        jwt_token,
                        contract_name,
                        contract_description,
                        obligations_array,
                        counterparty=swap_counterparty,
                        payment_amount=payment_amount,
                        payment_denomination=payment_denomination,
                        deadline=deadline if deadline else None,
                        account_address=obligor_address_for_loan or None,
                        wallet_id=obligor_wallet_id_for_loan,
                    )
                else:
                    echo_with_color(CYAN, "📤 Calling issue composed contract workflow endpoint...")
                    start_response = issue_composed_contract_workflow(
                        pay_service_url,
                        jwt_token,
                        contract_name,
                        contract_description,
                        obligations_array,
                        account_address=obligor_address_for_loan or None,
                        wallet_id=obligor_wallet_id_for_loan,
                    )
                
                workflow_id = start_response.get('workflow_id') if isinstance(start_response, dict) else None
                
                if not workflow_id or workflow_id == "null":
                    echo_with_color(RED, f"  ❌ Failed to start workflow for loan {loan_id}")
                    if isinstance(start_response, dict):
                        error_msg = start_response.get('error', 'Unknown error')
                        echo_with_color(RED, f"    Error: {error_msg}")
                    fail_count += 1
                    continue
                
                echo_with_color(GREEN, f"  ✅ Workflow started with ID: {workflow_id}")
                print()
                
                # Poll for completion
                final_response = poll_workflow_status(pay_service_url, workflow_id)
                
                if not final_response:
                    echo_with_color(RED, f"  ❌ Workflow did not complete for loan {loan_id}")
                    fail_count += 1
                    continue
                
                workflow_status = final_response.get('workflow_status', '')
                
                if workflow_status == "completed":
                    echo_with_color(GREEN, f"  ✅ Loan {loan_id} contract created successfully!")
                    result = final_response.get('result') or {}
                    # Backend may return result with swap_id "pending" or missing if status was read
                    # before the create_swap context was persisted; re-fetch once after a short delay.
                    if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                        swap_id_raw = result.get('swap_id') if isinstance(result, dict) else None
                        if swap_id_raw is None or swap_id_raw in ('', 'pending'):
                            echo_with_color(BLUE, "    ⏳ Re-fetching workflow result for swap_id...", file=sys.stderr)
                            time.sleep(2)
                            retry_response = requests.get(
                                f"{pay_service_url}/api/workflows/{workflow_id}",
                                timeout=30
                            )
                            if retry_response.ok:
                                try:
                                    retry_data = retry_response.json()
                                    retry_result = retry_data.get('result')
                                    if isinstance(retry_result, dict) and retry_result.get('swap_id') not in (None, '', 'pending'):
                                        result = retry_result
                                        echo_with_color(GREEN, "    ✅ Got swap_id from re-fetch", file=sys.stderr)
                                except Exception:
                                    pass
                    if not isinstance(result, dict):
                        result = {}
                    contract_id = result.get('composed_contract_id', 'N/A')
                    echo_with_color(BLUE, f"    Composed Contract ID: {contract_id}")
                    # Only accept when we have the same sub-account that issued (obligor_wallet_id_for_loan).
                    # We require obligor_wallet_id_for_loan so accept is always as the issuing sub-account.
                    if contract_id and contract_id != 'N/A' and obligor_wallet_id_for_loan:
                        echo_with_color(CYAN, "    📤 Requesting accept obligation as same sub-account that issued...", file=sys.stderr)
                        accept_res = accept_obligation_graphql(
                            pay_service_url,
                            jwt_token,
                            contract_id,
                            account_address=obligor_address_for_loan,
                            wallet_id=obligor_wallet_id_for_loan,
                        )
                        if accept_res.get("success"):
                            echo_with_color(GREEN, "    ✅ Accept (as sub-account) succeeded", file=sys.stderr)
                            if accept_res.get("messageId"):
                                echo_with_color(BLUE, f"       Message ID: {accept_res.get('messageId')}", file=sys.stderr)
                        elif "already accepted" in (accept_res.get("error") or accept_res.get("message") or "").lower():
                            echo_with_color(BLUE, "    ℹ️  Obligation already accepted (workflow may have accepted)", file=sys.stderr)
                        else:
                            echo_with_color(YELLOW, f"    ⚠️  Accept request: {accept_res.get('error', accept_res.get('message', 'Unknown'))}", file=sys.stderr)
                    elif contract_id and contract_id != 'N/A' and not obligor_wallet_id_for_loan:
                        echo_with_color(YELLOW, "    ⚠️  Skipping accept: no obligor wallet id (accept only when same sub-account that issued can accept)", file=sys.stderr)
                    if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                        swap_id_val = result.get('swap_id')
                        if swap_id_val is not None:
                            swap_id_val = str(swap_id_val).strip() if swap_id_val else ""
                        else:
                            swap_id_val = ""
                        # Backend may return "pending" when result was serialized before swap_id was set
                        if swap_id_val == "pending":
                            swap_id_val = ""
                        swap_message_id = result.get('swap_message_id') or 'N/A'
                        if swap_id_val:
                            echo_with_color(BLUE, f"    Swap ID: {swap_id_val}")
                            if swap_message_id != 'N/A':
                                echo_with_color(BLUE, f"    Swap Message ID: {swap_message_id}")
                            # Acceptor (counterparty) accepts/completes the swap when credentials set or mode is issue_swap_complete
                            run_accept = (action_mode == ACTION_ISSUE_SWAP_COMPLETE) or (acceptor_email and acceptor_password)
                            if run_accept and swap_id_val:
                                if not acceptor_email or not acceptor_password:
                                    echo_with_color(RED, "    ❌ issue_swap_complete requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD")
                                else:
                                    accept_result = complete_swap(
                                        pay_service_url,
                                        auth_service_url,
                                        acceptor_email,
                                        acceptor_password,
                                        str(swap_id_val),
                                    )
                                    if accept_result.get("success"):
                                        echo_with_color(GREEN, f"    ✅ Swap accepted by {acceptor_email}")
                                        if accept_result.get("messageId"):
                                            echo_with_color(BLUE, f"       Message ID: {accept_result.get('messageId')}")
                                        # Poll until swap status is COMPLETED before accept_all (avoids race)
                                        poll_result = poll_swap_completion(
                                            pay_service_url,
                                            auth_service_url,
                                            acceptor_email,
                                            acceptor_password,
                                            str(swap_id_val),
                                        )
                                        if not poll_result.get("success"):
                                            echo_with_color(YELLOW, f"    ⚠️  Swap polling failed: {poll_result.get('error', 'Unknown')}")
                                        # Loan account accepts all resulting payments (per nc_acacia.yaml payer_accept_1)
                                        # wallet_id scopes to ONLY this loan's wallet - no other entity wallets
                                        if poll_result.get("success") and obligor_wallet_id_for_loan and obligor_address_for_loan:
                                            acc_idem = f"accept-loan-{loan_id}-{int(time.time() * 1000)}"
                                            acc_res = accept_all_tokens(
                                                pay_service_url,
                                                auth_service_url,
                                                user_email,
                                                password,
                                                payment_denomination,
                                                acc_idem,
                                                obligor=None,
                                                wallet_id=obligor_wallet_id_for_loan,
                                                account_address=obligor_address_for_loan,
                                            )
                                            if not acc_res.get("success"):
                                                echo_with_color(YELLOW, f"    ⚠️  Accept all (loan account): {acc_res.get('error', 'Unknown')}")
                                    else:
                                        echo_with_color(RED, f"    ❌ Swap acceptance failed: {accept_result.get('error', 'Unknown error')}")
                            elif acceptor_email and swap_id_val and not acceptor_password:
                                echo_with_color(YELLOW, "    ⚠️  ACCEPTOR_EMAIL set but ACCEPTOR_PASSWORD missing; skipping swap acceptance")
                    success_count += 1
                else:
                    echo_with_color(RED, f"  ❌ Loan {loan_id} workflow ended in status: {workflow_status}")
                    error_msg = final_response.get('error', 'Unknown error')
                    if error_msg:
                        echo_with_color(RED, f"    Error: {error_msg}")
                    fail_count += 1
    except Exception as e:
        echo_with_color(RED, f"❌ Error reading CSV file: {e}")
        return 1
    
    # --- Summary ---
    print()
    echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    echo_with_color(CYAN, "📊 Summary")
    echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    echo_with_color(BLUE, f"  Total loans processed: {loan_count}")
    echo_with_color(GREEN, f"  Successful: {success_count}")
    echo_with_color(RED, f"  Failed: {fail_count}")
    print()
    
    if success_count > 0:
        echo_with_color(GREEN, f"🎉 Successfully created {success_count} composed contract(s)! ✨")
    
    # Burn tokens after loans when requested (mirrors treasury.yaml burn command)
    if burn_after_env and policy_secret and burn_amount:
        print()
        echo_with_color(CYAN, "🔥 Burning tokens after loan processing...")
        burn_res = burn_tokens(
            pay_service_url, auth_service_url, user_email, password,
            denomination, burn_amount, policy_secret,
        )
        if not burn_res.get("success"):
            echo_with_color(RED, f"❌ Burn failed: {burn_res.get('error', 'Unknown error')}")
            if success_count > 0:
                echo_with_color(YELLOW, "  (Loans were created successfully; only burn failed)")
        print()
    elif burn_after_env and (not policy_secret or not burn_amount):
        echo_with_color(YELLOW, "  ⚠️  BURN_AFTER_LOANS=true but POLICY_SECRET or BURN_AMOUNT missing; skipping burn")
    
    if success_count > 0:
        return 0
    else:
        echo_with_color(RED, "❌ No contracts were created successfully")
        return 1


if __name__ == "__main__":
    sys.exit(main())
