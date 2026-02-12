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


def get_entity_wallets(
    pay_service_url: str,
    jwt_token: str,
) -> dict:
    """Query wallets for the current user (entity from JWT). Returns { success, wallets: [ { id, entityId, name, address } ], error }."""
    query = (
        "query EntityWallets {"
        "  entityWallets { id entityId name address }"
        "}"
    )
    try:
        data = post_graphql(pay_service_url, jwt_token, query, {}, timeout=30)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "wallets": []}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "entityWallets" in data_obj:
            wallets = data_obj["entityWallets"]
            if isinstance(wallets, list):
                return {"success": True, "wallets": wallets}
        return {"success": True, "wallets": []}
    except Exception as e:
        return {"success": False, "error": str(e), "wallets": []}


def get_default_wallet_id(
    pay_service_url: str,
    jwt_token: str,
    entity_id: Optional[str] = None,
) -> Optional[str]:
    """
    Return the default wallet id for the current user (JWT).
    Matches backend logic: prefer WLT-USER-{entity_id}, else first wallet.
    entity_id can be from get_user_id_from_profile (user id UUID); if omitted, first wallet is used.
    """
    res = get_entity_wallets(pay_service_url, jwt_token)
    if not res.get("success") or not res.get("wallets"):
        return None
    wallets = res["wallets"]
    entity_id = (entity_id or "").strip().replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "")
    if entity_id:
        default_id = f"WLT-USER-{entity_id}"
        for w in wallets:
            if isinstance(w, dict) and w.get("id") == default_id:
                return default_id
    # Fallback: first wallet
    first = wallets[0] if wallets else None
    if isinstance(first, dict) and first.get("id"):
        return first["id"]
    return None


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


def query_payments_by_wallet(
    pay_service_url: str,
    jwt_token: str,
    wallet_id: str,
    account_address: Optional[str] = None,
) -> dict:
    """Query payments that involve the given wallet (payer or payee). Returns list of { id, amount, status, payeeWalletId, payerWalletId, contractId }."""
    query = (
        "query PaymentsByWallet($walletId: String!) {"
        "  payments { byWallet(walletId: $walletId) { id amount status payeeWalletId payerWalletId contractId } }"
        "}"
    )
    variables = {"walletId": wallet_id}
    try:
        data = post_graphql(
            pay_service_url, jwt_token, query, variables,
            account_address=account_address, wallet_id=wallet_id,
            timeout=30,
        )
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "payments": []}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "payments" in data_obj:
            pay_obj = data_obj["payments"]
            if isinstance(pay_obj, dict) and "byWallet" in pay_obj:
                payments = pay_obj["byWallet"] if isinstance(pay_obj["byWallet"], list) else []
                return {"success": True, "payments": payments}
        return {"success": True, "payments": []}
    except Exception as e:
        return {"success": False, "error": str(e), "payments": []}


def query_payments_by_entity(
    pay_service_url: str,
    jwt_token: str,
    entity_id: str,
) -> dict:
    """Query payments where the entity is involved (payer or payee). Returns list of payment dicts with id, amount, status, payeeWalletId, payerWalletId, contractId."""
    query = (
        "query PaymentsByEntity($currentEntityId: String!) {"
        "  payments { paymentsByEntity(currentEntityId: $currentEntityId) { id amount status payeeWalletId payerWalletId contractId } }"
        "}"
    )
    variables = {"currentEntityId": entity_id}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=30)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "payments": []}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "payments" in data_obj:
            pay_obj = data_obj["payments"]
            if isinstance(pay_obj, dict) and "paymentsByEntity" in pay_obj:
                payments = pay_obj["paymentsByEntity"] if isinstance(pay_obj["paymentsByEntity"], list) else []
                return {"success": True, "payments": payments}
        return {"success": True, "payments": []}
    except Exception as e:
        return {"success": False, "error": str(e), "payments": []}


def query_loan_by_id(
    pay_service_url: str,
    jwt_token: str,
    loan_id: str,
) -> dict:
    """
    Get loan by ID using the loans query (contract_flow / loan structure).
    Returns { success, loan_id, main_contract_id, error }.
    """
    query = (
        "query LoanById($loanId: String) {"
        "  loans(loanId: $loanId) { loanId mainContractId status }"
        "}"
    )
    variables = {"loanId": str(loan_id).strip()}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=30)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "main_contract_id": None}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "loans" in data_obj:
            loans = data_obj["loans"] if isinstance(data_obj["loans"], list) else []
            if loans and len(loans) > 0:
                loan = loans[0] if isinstance(loans[0], dict) else None
                if loan:
                    main = loan.get("mainContractId") or loan.get("main_contract_id")
                    return {
                        "success": True,
                        "loan_id": loan.get("loanId") or loan.get("loan_id") or loan_id,
                        "main_contract_id": main,
                        "status": loan.get("status"),
                    }
        return {"success": False, "error": "Loan not found", "main_contract_id": None}
    except Exception as e:
        return {"success": False, "error": str(e), "main_contract_id": None}


def query_acceptor_contracts(
    pay_service_url: str,
    jwt_token: str,
) -> dict:
    """
    Get all contracts and composed contracts for the current user (acceptor).
    Uses contract_flow.unifiedByEntityId() — no args; entity from JWT.
    Returns { success, contracts: [ { id, name, child_contracts: [ { id, name } ] } ], error }.
    Flattened: we also return flat_contracts: [ { id, name } ] for all leaf contracts.
    """
    query = (
        "query AcceptorContracts {"
        "  contractFlow {"
        "    unifiedByEntityId {"
        "      __typename"
        "      ... on Contract { id name }"
        "      ... on ComposedContract { id name contracts { id name } }"
        "    }"
        "  }"
        "}"
    )
    try:
        data = post_graphql(pay_service_url, jwt_token, query, {}, timeout=30)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "flat_contracts": []}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if not isinstance(data_obj, dict) or "contractFlow" not in data_obj:
            return {"success": False, "error": "No contractFlow in response", "flat_contracts": []}
        unions = (
            data_obj.get("contractFlow", {}).get("unifiedByEntityId")
            if isinstance(data_obj.get("contractFlow"), dict) else None
        )
        if not isinstance(unions, list):
            return {"success": True, "flat_contracts": []}
        flat_contracts: list = []
        for u in unions:
            if not isinstance(u, dict):
                continue
            tid = u.get("__typename")
            if tid == "Contract":
                cid = u.get("id")
                name = u.get("name") or ""
                if cid:
                    flat_contracts.append({"id": cid, "name": name})
            elif tid == "ComposedContract":
                comp_name = u.get("name") or ""
                for c in u.get("contracts") or []:
                    if isinstance(c, dict) and c.get("id"):
                        flat_contracts.append({
                            "id": c["id"],
                            "name": (c.get("name") or comp_name or ""),
                        })
        return {"success": True, "flat_contracts": flat_contracts}
    except Exception as e:
        return {"success": False, "error": str(e), "flat_contracts": []}


def _find_contract_id_for_loan(flat_contracts: list, loan_id: str) -> Optional[str]:
    """From acceptor's flat contracts, return the contract id that relates to this loan (name contains loan_id)."""
    loan_id_str = str(loan_id).strip()
    if not loan_id_str:
        return None
    for c in flat_contracts:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        # Match "Loan 824246", "Loan Contract 824246", or any name containing the loan id
        if loan_id_str in name or name.endswith(" " + loan_id_str):
            return c.get("id")
    return None


def query_contract_with_payments(
    pay_service_url: str,
    jwt_token: str,
    contract_id: str,
) -> dict:
    """
    Get contract (or composed contract) with its payments using contract_flow.unifiedById.
    Returns { success, contract_id, payments: [ { id, amount, status, payeeWalletId, payerWalletId, contractId } ], error }.
    Uses the same structure as contract_flow / composed_flow (no ID prefix logic).
    """
    # Payment type in schema may use snake_case (payee_wallet_id not always exposed); request only id, amount, status, contract_id
    query = (
        "query ContractWithPayments($id: String!) {"
        "  contractFlow {"
        "    unifiedById(id: $id) {"
        "      __typename"
        "      ... on Contract { id payments { id amount status contractId } }"
        "      ... on ComposedContract { id contracts { id payments { id amount status contractId } } }"
        "    }"
        "  }"
        "}"
    )
    variables = {"id": str(contract_id).strip()}
    try:
        data = post_graphql(pay_service_url, jwt_token, query, variables, timeout=30)
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error"), "payments": []}
        errors_msg = graphql_errors_message(data) if isinstance(data, dict) else None
        data_obj = data.get("data") if isinstance(data, dict) else None
        if not isinstance(data_obj, dict):
            return {
                "success": False,
                "error": errors_msg or "No data in response",
                "payments": [],
            }
        cf = data_obj.get("contractFlow") or data_obj.get("contract_flow")
        if not isinstance(cf, dict):
            return {
                "success": False,
                "error": errors_msg or "No contractFlow in response",
                "payments": [],
            }
        union = cf.get("unifiedById") or cf.get("unified_by_id")
        if union is None:
            return {
                "success": False,
                "error": errors_msg or "Contract not found",
                "payments": [],
            }
        payments: list = []
        cid = union.get("id") or contract_id
        if union.get("__typename") == "Contract":
            payments = union.get("payments") if isinstance(union.get("payments"), list) else []
        elif union.get("__typename") == "ComposedContract":
            for c in union.get("contracts") or []:
                if isinstance(c, dict):
                    payments.extend(c.get("payments") or [])
        return {"success": True, "contract_id": cid, "payments": payments}
    except Exception as e:
        return {"success": False, "error": str(e), "payments": []}


def _filter_pending_payments_by_amount(payments: list, amount_wei: Optional[str] = None) -> list:
    """Filter to PENDING/PROCESSING; optionally prefer exact amount_wei match. No ID prefix filter."""
    pending = [
        p for p in payments
        if isinstance(p, dict)
        and str(p.get("status", "")).upper() in ("PENDING", "PROCESSING")
    ]
    if not pending or amount_wei is None:
        return pending
    for p in pending:
        if str(p.get("amount", "")) == str(amount_wei):
            return [p]
    return pending


def find_obligation_initial_payment_from_loan(
    pay_service_url: str,
    jwt_token: str,
    loan_id: str,
    amount_wei: Optional[str] = None,
    acceptor_token: Optional[str] = None,
    loan_wallet_id: Optional[str] = None,
    loan_wallet_address: Optional[str] = None,
    debug_callback: Optional[callable] = None,
) -> Optional[dict]:
    """
    Resolve the obligation initial payment for a loan. Tries in order:
    1) Acceptor's contracts (contract_flow.unifiedByEntityId with acceptor token) → find contract
       relating to this loan (name contains loan_id) → get payments for that contract.
    2) Loan record (loans query) → main_contract_id → contract_flow.unifiedById → payments.
    3) Payments by loan wallet (when no Loan record).
    Returns the first PENDING/PROCESSING payment (optionally matching amount_wei). No ID prefix logic.
    If debug_callback is set and resolution fails, it is called with (step, info).
    """
    def _debug(step: str, info: dict) -> None:
        if debug_callback and callable(debug_callback):
            debug_callback(step, info)

    loan_id_str = str(loan_id).strip()

    # 1) Acceptor's contracts: find the contract for this loan, then get its payments
    if acceptor_token:
        acc_res = query_acceptor_contracts(pay_service_url, acceptor_token)
        if acc_res.get("success"):
            flat = acc_res.get("flat_contracts") or []
            contract_id = _find_contract_id_for_loan(flat, loan_id_str)
            if contract_id:
                contract_res = query_contract_with_payments(
                    pay_service_url, acceptor_token, contract_id
                )
                if contract_res.get("success"):
                    payments = contract_res.get("payments") or []
                    pending = _filter_pending_payments_by_amount(payments, amount_wei)
                    if pending:
                        return pending[0]
                    statuses = [str(p.get("status", "")) for p in payments[:10] if isinstance(p, dict)]
                    _debug("acceptor_contract_payments", {
                        "total": len(payments),
                        "pending_count": 0,
                        "statuses": statuses,
                        "contract_id": contract_id,
                    })
                    return None
                _debug("acceptor_contract", {
                    "success": False,
                    "contract_id": contract_id,
                    "error": contract_res.get("error"),
                })
                return None
            _debug("acceptor_contracts", {
                "contract_count": len(flat),
                "loan_id": loan_id_str,
                "error": "No contract name matching this loan_id",
            })
        else:
            _debug("acceptor_contracts", {"error": acc_res.get("error"), "contract_count": 0})

    # 2) Loan record → contract → payments (when Loan record exists)
    loan_res = query_loan_by_id(pay_service_url, jwt_token, loan_id_str)
    if loan_res.get("success") and loan_res.get("main_contract_id"):
        main_contract_id = loan_res["main_contract_id"]
        contract_res = query_contract_with_payments(pay_service_url, jwt_token, main_contract_id)
        if contract_res.get("success"):
            payments = contract_res.get("payments") or []
            pending = _filter_pending_payments_by_amount(payments, amount_wei)
            if pending:
                return pending[0]
            statuses = [str(p.get("status", "")) for p in payments[:10] if isinstance(p, dict)]
            _debug("payments", {"total": len(payments), "pending_count": 0, "statuses": statuses})
            return None
        _debug("contract", {
            "success": False,
            "contract_id": main_contract_id,
            "payment_count": 0,
            "error": contract_res.get("error"),
        })
        return None
    _debug("loan", {
        "success": loan_res.get("success"),
        "main_contract_id": loan_res.get("main_contract_id"),
        "error": loan_res.get("error"),
    })

    # 3) Fallback: payments by loan wallet
    if loan_wallet_id:
        res = query_payments_by_wallet(
            pay_service_url, jwt_token, loan_wallet_id, account_address=loan_wallet_address
        )
        if res.get("success"):
            payments = res.get("payments") or []
            pending = _filter_pending_payments_by_amount(payments, amount_wei)
            if pending:
                return pending[0]
        _debug("by_wallet", {"loan_wallet_id": loan_wallet_id, "payment_count": len(res.get("payments") or [])})
    return None


def _filter_obligation_initial_payments(payments: list, amount_wei: Optional[str] = None) -> list:
    """
    Filter to obligation initial payments only (PAY-INITIAL-*), NOT swap payments.
    Keeps PENDING/PROCESSING; optionally prefers amount_wei match.
    """
    pending = [
        p for p in payments
        if isinstance(p, dict)
        and str(p.get("status", "")).upper() in ("PENDING", "PROCESSING")
        and str(p.get("id", "")).startswith("PAY-INITIAL-")
    ]
    if not pending or amount_wei is None:
        return pending
    for p in pending:
        if str(p.get("amount", "")) == str(amount_wei):
            return [p]
    return pending


def find_obligation_initial_payment(
    pay_service_url: str,
    jwt_token: str,
    loan_wallet_id: str,
    loan_wallet_address: Optional[str] = None,
    amount_wei: Optional[str] = None,
    acceptor_entity_id: Optional[str] = None,
    acceptor_token: Optional[str] = None,
    debug_callback: Optional[callable] = None,
) -> Optional[dict]:
    """
    Find the obligation initial payment (PAY-INITIAL-*) related to the loan — NOT a swap payment.
    Tries: (1) payments by loan wallet, (2) if provided, payments by acceptor entity (with amount match).
    Returns the full payment dict (id, amount, status, payeeWalletId, payerWalletId, contractId) or None.
    If debug_callback is set, it will be called with (source, count, payments_list) when no match is found.
    """
    def _debug(source: str, count: int, payments: list) -> None:
        if debug_callback and callable(debug_callback):
            debug_callback(source, count, payments)

    # 1) By loan wallet (payer or payee)
    res = query_payments_by_wallet(
        pay_service_url, jwt_token, loan_wallet_id, account_address=loan_wallet_address
    )
    if res.get("success"):
        payments = res.get("payments") or []
        pending = _filter_obligation_initial_payments(payments, amount_wei)
        if pending:
            return pending[0]
        _debug("by_wallet", len(payments), payments)

    # 2) Fallback: by acceptor entity (payments where acceptor is involved), then filter PAY-INITIAL-* + amount
    acceptor_entity_ids = [acceptor_entity_id] if isinstance(acceptor_entity_id, str) and acceptor_entity_id else []
    if isinstance(acceptor_entity_id, list):
        acceptor_entity_ids = [e for e in acceptor_entity_id if e]
    if acceptor_entity_ids and acceptor_token:
        for eid in acceptor_entity_ids:
            res_entity = query_payments_by_entity(pay_service_url, acceptor_token, eid)
            if res_entity.get("success"):
                payments = res_entity.get("payments") or []
                pending = _filter_obligation_initial_payments(payments, amount_wei)
                if pending:
                    return pending[0]
                _debug("by_entity", len(payments), payments)
            else:
                _debug("by_entity_error", 0, [])

    return None


def find_obligation_initial_payment_id(
    pay_service_url: str,
    jwt_token: str,
    loan_wallet_id: str,
    loan_wallet_address: Optional[str] = None,
    amount_wei: Optional[str] = None,
    acceptor_entity_id: Optional[str] = None,
    acceptor_token: Optional[str] = None,
) -> Optional[str]:
    """
    Find the payment_id for the obligation's initial payment (PAY-INITIAL-*), NOT a swap payment.
    Delegates to find_obligation_initial_payment; returns the payment id or None.
    """
    payment = find_obligation_initial_payment(
        pay_service_url,
        jwt_token,
        loan_wallet_id,
        loan_wallet_address=loan_wallet_address,
        amount_wei=amount_wei,
        acceptor_entity_id=acceptor_entity_id,
        acceptor_token=acceptor_token,
    )
    return payment.get("id") if payment else None


def accept_payment(
    pay_service_url: str,
    auth_service_url: str,
    user_email: str,
    user_password: str,
    payment_id: str,
    amount: Optional[str] = None,
    wallet_id: Optional[str] = None,
    account_address: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> dict:
    """Accept a single payment by payment ID. Mirrors frontend (yieldfabric-app src/pages/wallets/[walletId].tsx):
    same mutation (accept(input: $input)) and same input shape: paymentId, walletId (optional)."""
    echo_with_color(CYAN, f"  ✅ Accepting payment {payment_id}" + (f" (wallet {wallet_id})" if wallet_id else "") + "...")
    jwt_token = login_user(auth_service_url, user_email, user_password)
    if not jwt_token:
        return {"success": False, "error": f"Failed to login as {user_email}"}
    key = idempotency_key or f"accept-{payment_id}-{int(time.time() * 1000)}"
    query = (
        "mutation Accept($input: AcceptInput!) {"
        " accept(input: $input) { success message accountAddress idHash acceptResult messageId transactionId timestamp } }"
    )
    inp: dict = {"paymentId": payment_id, "idempotencyKey": key}
    if amount is not None:
        # GraphQL expects String for input.amount (wei); backend parses to u128
        inp["amount"] = str(amount)
    if wallet_id:
        inp["walletId"] = wallet_id
    variables = {"input": inp}
    try:
        data = post_graphql(
            pay_service_url, jwt_token, query, variables,
            account_address=account_address, wallet_id=wallet_id,
            timeout=90,
        )
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error", "Empty response from accept")}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "accept" in data_obj:
            acc = data_obj["accept"]
            if acc.get("success"):
                echo_with_color(GREEN, f"    ✅ Accept successful (messageId: {acc.get('messageId', 'N/A')})")
                return {"success": True, "data": acc}
            return {"success": False, "error": acc.get("message", "Accept failed")}
        msg = graphql_errors_message(data)
        return {"success": False, "error": msg or data.get("error", "Unknown accept failure")}
    except Exception as e:
        echo_with_color(RED, f"  ❌ Accept failed: {e}")
        return {"success": False, "error": str(e)}


def create_payment_swap(
    pay_service_url: str,
    jwt_token: str,
    counterparty: str,
    initiator_amount_wei: str,
    counterparty_amount_wei: str,
    denomination: str,
    initiator_obligor_address: Optional[str],
    deadline: str,
    wallet_id: Optional[str] = None,
    account_address: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    counterparty_wallet_id: Optional[str] = None,
) -> dict:
    """Create a payment swap: initiator gives amount with obligor, counterparty gives amount with obligor=null.
    counterparty_wallet_id: optional; when counterparty is an entity, use this to specify the counterparty wallet (e.g. loan wallet)."""
    echo_with_color(CYAN, f"  🔄 Creating payment swap (initiator: {initiator_amount_wei}, counterparty: {counterparty_amount_wei})...", file=sys.stderr)
    swap_id = str(int(time.time() * 1000))
    key = idempotency_key or f"create-payment-swap-{swap_id}"
    payment_policy = {
        "oracleAddress": None,
        "oracleOwner": None,
        "oracleKeySender": None,
        "oracleValueSenderSecret": None,
        "oracleKeyRecipient": None,
        "oracleValueRecipientSecret": None,
        "unlockSender": None,
        "unlockReceiver": None,
        "linearVesting": None,
    }
    initiator_payments = {
        "amount": initiator_amount_wei,
        "denomination": denomination,
        "obligor": initiator_obligor_address,
        "payments": [payment_policy],
    }
    counterparty_payments = {
        "amount": counterparty_amount_wei,
        "denomination": denomination,
        "obligor": None,
        "payments": [payment_policy],
    }
    query = (
        "mutation CreateSwap($input: CreateSwapInput!) {"
        " createSwap(input: $input) { success message swapId messageId } }"
    )
    variables = {
        "input": {
            "swapId": swap_id,
            "counterparty": counterparty,
            "deadline": deadline,
            "initiatorExpectedPayments": initiator_payments,
            "counterpartyExpectedPayments": counterparty_payments,
            "idempotencyKey": key,
        }
    }
    if counterparty_wallet_id is not None and counterparty_wallet_id.strip():
        variables["input"]["counterpartyWalletId"] = counterparty_wallet_id.strip()
    try:
        data = post_graphql(
            pay_service_url, jwt_token, query, variables,
            account_address=account_address, wallet_id=wallet_id,
            timeout=60,
        )
        if data.get("error") and "data" not in data:
            return {"success": False, "error": data.get("error", "Empty response from createSwap")}
        data_obj = data.get("data") if isinstance(data, dict) else None
        if isinstance(data_obj, dict) and "createSwap" in data_obj:
            cs = data_obj["createSwap"]
            if cs.get("success"):
                swap_id_out = cs.get("swapId") or swap_id
                echo_with_color(GREEN, f"    ✅ Create swap successful (swapId: {swap_id_out})", file=sys.stderr)
                return {"success": True, "swap_id": swap_id_out, "message_id": cs.get("messageId"), "data": cs}
            return {"success": False, "error": cs.get("message", "Create swap failed")}
        msg = graphql_errors_message(data)
        return {"success": False, "error": msg or data.get("error", "Unknown createSwap failure")}
    except Exception as e:
        echo_with_color(RED, f"  ❌ Create payment swap failed: {e}", file=sys.stderr)
        return {"success": False, "error": str(e)}


def complete_swap_as_wallet(
    pay_service_url: str,
    jwt_token: str,
    swap_id: str,
    account_address: str,
    wallet_id: str,
    max_retries: int = 12,
    retry_delay_seconds: float = 2.0,
) -> dict:
    """Call completeSwap as a specific wallet (sub-account) using JWT + X-Account-Address + X-Wallet-Id."""
    echo_with_color(CYAN, f"  🤝 Completing swap {swap_id} as wallet {wallet_id}...", file=sys.stderr)
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
            data = post_graphql(
                pay_service_url, jwt_token, query, variables,
                account_address=account_address, wallet_id=wallet_id,
                timeout=60,
            )
            if data.get("error") and "data" not in data:
                return {"error": data.get("error", "Empty response from completeSwap"), "success": False}
            data_obj = data.get("data") if isinstance(data, dict) else None
            if isinstance(data_obj, dict) and "completeSwap" in data_obj:
                cs = data_obj["completeSwap"]
                result = {"success": cs.get("success", False), "message": cs.get("message"), "messageId": cs.get("messageId"), "transactionId": cs.get("transactionId"), "raw": cs}
                if result.get("success"):
                    echo_with_color(GREEN, f"    ✅ Swap completed as wallet {wallet_id}", file=sys.stderr)
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
