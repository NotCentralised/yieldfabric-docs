"""Payments service: wallets, composed contract workflows, accept obligation, swap, mint/burn/deposit."""

import json
import sys
import time
from typing import Optional

import requests

from .auth import login_user
from .console import BLUE, CYAN, GREEN, RED, YELLOW, echo_with_color
from .http_client import graphql_errors_message, post_graphql, post_workflow_json


def create_wallet_in_payments(
    pay_service_url: str,
    jwt_token: str,
    entity_id: str,
    address: str,
    wallet_id: str,
    name: str = "Sub-Account",
    description: str = "Additional blockchain account",
) -> dict:
    """Create a wallet record in the payments graph store. Returns dict with success, wallet, or error."""
    entity_id = (entity_id or "").strip().replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "")
    address = (address or "").strip()
    wallet_id = (wallet_id or "").strip()
    if not entity_id or not address or not wallet_id:
        return {"success": False, "error": "entity_id, address and wallet_id are required"}
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
        data = post_graphql(pay_service_url, jwt_token, query, variables)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error", "Empty response from createWallet")}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict):
            wallets_obj = data_obj.get("wallets")
            if isinstance(wallets_obj, dict):
                w = wallets_obj.get("createWallet")
                if w is not None:
                    return {"success": True, "wallet": w if isinstance(w, dict) else {"id": wallet_id}}
        msg = graphql_errors_message(data)
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
    """Fetch a wallet by ID from the payments GraphQL API. Returns dict or None."""
    wallet_id = (wallet_id or "").strip()
    if not wallet_id:
        return None
    query = "query GetWalletById($id: ID!) { wallet(id: $id) { id entityId name address } }"
    try:
        data = post_graphql(pay_service_url, jwt_token, query, {"id": wallet_id})
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
    """Shared workflow POST: build body, log, and call post_workflow_json."""
    request_body = {"name": name, "description": description, "obligations": obligations_json}
    if request_body_extra:
        request_body.update(request_body_extra)
    echo_with_color(BLUE, "  📋 Request body:", file=sys.stderr)
    print(json.dumps(request_body, indent=2), file=sys.stderr)
    echo_with_color(BLUE, f"  🌐 Making REST API request to: {pay_service_url.rstrip('/')}{path}", file=sys.stderr)
    return post_workflow_json(
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
    """Call acceptObligation GraphQL mutation. Retries on 'Contract not found'."""
    query = (
        "mutation AcceptObligation($input: AcceptObligationInput!) {"
        " acceptObligation(input: $input) { success message messageId } }"
    )
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
                echo_with_color(BLUE, f"    ⏳ Retry {attempt}/{max_retries} for acceptObligation...", file=sys.stderr)
            data = post_graphql(
                pay_service_url, jwt_token, query, variables,
                account_address=account_address, wallet_id=wallet_id,
            )
            if data.get("error") and "data" not in data:
                return {"success": False, "error": data.get("error", "Empty response from acceptObligation")}
            data_obj = data.get("data") if isinstance(data, dict) else None
            if isinstance(data_obj, dict) and "acceptObligation" in data_obj:
                ao = data_obj["acceptObligation"]
                result = {"success": ao.get("success", False), "message": ao.get("message"), "messageId": ao.get("messageId"), "raw": ao}
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
            msg = graphql_errors_message(data)
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
    """Login as acceptor and call completeSwap GraphQL mutation. Retries on 'Swap not found'."""
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
        variables = {"input": {"swapId": swap_id, "idempotencyKey": idempotency_key}}
        try:
            if attempt > 1:
                echo_with_color(BLUE, f"    ⏳ Retry {attempt}/{max_retries} for completeSwap...", file=sys.stderr)
            data = post_graphql(pay_service_url, acceptor_token, query, variables)
            if data.get("error") and "data" not in data:
                return {"error": data.get("error", "Empty response from completeSwap"), "success": False}
            data_obj = data.get("data") if isinstance(data, dict) else None
            if isinstance(data_obj, dict) and "completeSwap" in data_obj:
                cs = data_obj["completeSwap"]
                result = {"success": cs.get("success", False), "message": cs.get("message"), "messageId": cs.get("messageId"), "transactionId": cs.get("transactionId"), "raw": cs}
                if result.get("success"):
                    return result
                err = (result.get("message") or result.get("error") or "").lower()
                if "swap not found" in err or "not found" in err:
                    if attempt < max_retries:
                        time.sleep(retry_delay_seconds)
                        continue
                    return {"error": result.get("message", "Swap not found"), "success": False}
                return result
            msg = graphql_errors_message(data)
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
    """Query swap status via GraphQL. Returns swap dict if found, else None."""
    query = (
        "query($id: String!) { swapFlow { coreSwaps { byId(id: $id) "
        "{ id swapId status deadline createdAt } } } }"
    )
    variables = {"id": swap_id}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=15)
        if data.get("error") and "data" not in data:
            return None
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
    """Poll until swap status is COMPLETED (or terminal failure)."""
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
    """Mint tokens via REST API. POST /mint?asset_id=...&amount=...&policy_secret=..."""
    echo_with_color(CYAN, f"  🪙 Minting {amount} {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/mint"
    params = {"asset_id": denomination, "amount": amount, "policy_secret": policy_secret}
    try:
        response = requests.post(url, params=params, headers={"Authorization": f"Bearer {jwt_token}"}, timeout=60)
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
    """Burn tokens via REST API. POST /burn?asset_id=...&amount=...&policy_secret=..."""
    echo_with_color(CYAN, f"  🔥 Burning {amount} {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/burn"
    params = {"asset_id": denomination, "amount": amount, "policy_secret": policy_secret}
    try:
        response = requests.post(url, params=params, headers={"Authorization": f"Bearer {jwt_token}"}, timeout=60)
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
    """Deposit tokens via GraphQL. User credits their account with the given amount."""
    echo_with_color(CYAN, f"  🏦 Depositing {amount} {denomination}...")
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    query = (
        "mutation Deposit($input: DepositInput!) {"
        " deposit(input: $input) { success message accountAddress depositResult messageId timestamp } }"
    )
    variables = {"input": {"assetId": denomination, "amount": amount, "idempotencyKey": idempotency_key}}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=60)
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "deposit" in data_obj:
            dep = data_obj["deposit"]
            if dep.get("success"):
                echo_with_color(GREEN, f"    ✅ Deposit successful (message_id: {dep.get('messageId', 'N/A')})")
                return {"success": True, "data": dep}
            return {"success": False, "error": dep.get("message", "Deposit failed")}
        msg = graphql_errors_message(data)
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
    """Accept all pending payables via GraphQL. wallet_id scopes to a specific account."""
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
        data = post_graphql(
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
        msg = graphql_errors_message(data)
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
    """Send tokens to a destination via GraphQL instant mutation. destination_id: entity email."""
    echo_with_color(CYAN, f"  ⚡ Sending {amount} {denomination} to {destination_id}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, sender_email, sender_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {sender_email}"}
    query = (
        "mutation Instant($input: InstantSendInput!) {"
        " instant(input: $input) { success message accountAddress destinationId idHash messageId paymentId sendResult timestamp } }"
    )
    variables = {"input": {"assetId": denomination, "amount": amount, "destinationId": destination_id}}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=60)
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "instant" in data_obj:
            inst = data_obj["instant"]
            if inst.get("success"):
                echo_with_color(GREEN, f"    ✅ Instant send successful (message_id: {inst.get('messageId', 'N/A')})", file=sys.stderr)
                return {"success": True, "data": inst}
            return {"success": False, "error": inst.get("message", "Instant send failed")}
        msg = graphql_errors_message(data)
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
    """Get total supply via REST API. GET /total_supply?asset_id=..."""
    echo_with_color(CYAN, f"  💰 Fetching total supply for {denomination}...", file=sys.stderr)
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    url = f"{pay_service_url.rstrip('/')}/total_supply"
    params = {"asset_id": denomination}
    try:
        response = requests.get(url, params=params, headers={"Authorization": f"Bearer {jwt_token}"}, timeout=30)
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
    delay_seconds: int = 1,
) -> Optional[dict]:
    """Poll workflow status until completion. Returns final workflow data or None."""
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
                    workflow_status = data.get("workflow_status", "")
                    current_step = data.get("current_step", "")
                    workflow_type = data.get("workflow_type", "")
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
