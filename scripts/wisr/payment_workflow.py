#!/usr/bin/env python3

"""
Payment workflow: process rows from a payment CSV (e.g. wisr_payment_test.csv).

For each row:
  1) Find the obligation initial payment for the loan (acceptor's contracts → contract for loan → payments).
  2) Accept that payment for the CSV amount only (DWH_PRINCIPAL in wei), not the payment's fill/full amount.
  3) Create a payment swap: the same user (acceptor) swaps the partial credit amount (with obligor = loan
     account) vs a cash payment of the same amount (obligor=null), where the counterparty is the
     respective loan account (loan wallet).
  4) The loan account (issuer acting as that loan wallet) completes the swap. Requires ISSUER_EMAIL
     and ISSUER_PASSWORD; if not set, the swap is created but remains pending.
  5) Accept all pending payables by both parties: acceptor (default wallet), then loan account (loan wallet).

CSV columns (header row): MAMBU_LOANID, MAMBU_PAYMENTDATE, MAMBU_TRANSACTION, DWH_PRINCIPAL,
  DWH_INTEREST, DWH_FEE, MAMBU_TOTAL_AMOUNT, MAMBU_ISDISHONOURED.

Events are logged with [TRACE] so you can follow the flow.
"""

import csv
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

from modules import (
    accept_all_tokens,
    accept_payment,
    check_service_running,
    complete_swap_as_wallet,
    create_payment_swap,
    convert_currency_to_wei,
    echo_with_color,
    find_obligation_initial_payment_from_loan,
    get_default_wallet_id,
    get_user_id_from_profile,
    get_wallet_by_id,
    load_env_files,
    login_user,
    safe_get,
)
from modules.console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW


def _trace(msg: str) -> None:
    """Log a trace line so we can follow the flow (prefix [TRACE])."""
    echo_with_color(BLUE, f"  [TRACE] {msg}")


def main() -> int:
    """Main entry: load env, parse args, run preflight, process payment rows."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print_payment_usage()
        return 0

    csv_file = parse_payment_cli_args(script_dir)
    if not Path(csv_file).exists():
        echo_with_color(RED, f"❌ CSV file not found: {csv_file}")
        return 1

    # --- Configuration ---
    pay_service_url = os.environ.get("PAY_SERVICE_URL", "https://pay.yieldfabric.com")
    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "https://auth.yieldfabric.com")
    denomination = os.environ.get("DENOMINATION", "aud-token-asset")
    acceptor_email = os.environ.get("ACCEPTOR_EMAIL", "").strip()
    acceptor_password = os.environ.get("ACCEPTOR_PASSWORD", "").strip()
    issuer_email = os.environ.get("ISSUER_EMAIL", "").strip()
    issuer_password = os.environ.get("ISSUER_PASSWORD", "").strip()
    swap_counterparty = os.environ.get("SWAP_COUNTERPARTY", "").strip()
    try:
        payment_count = int(os.environ.get("PAYMENT_COUNT", "100").strip())
        if payment_count < 1:
            payment_count = 100
    except ValueError:
        payment_count = 100

    echo_with_color(CYAN, "🚀 Payment Workflow - Find payment, accept amount, then create payment swap")
    print()
    echo_with_color(BLUE, "📋 Configuration:")
    echo_with_color(BLUE, f"  API Base URL: {pay_service_url}")
    echo_with_color(BLUE, f"  Auth Service: {auth_service_url}")
    echo_with_color(BLUE, f"  Acceptor (find + accept): {acceptor_email}")
    if issuer_email:
        echo_with_color(BLUE, f"  Issuer (loan wallet lookup): {issuer_email}")
    echo_with_color(BLUE, f"  CSV File: {csv_file}")
    echo_with_color(BLUE, f"  Denomination (swap): {denomination}")
    echo_with_color(BLUE, f"  Max payment rows: {payment_count}")
    print()

    if not acceptor_email or not acceptor_password:
        echo_with_color(RED, "❌ ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD are required")
        return 1

    # --- Preflight ---
    if not check_service_running("Auth Service", auth_service_url):
        echo_with_color(RED, f"❌ Auth service is not reachable at {auth_service_url}")
        return 1
    if not check_service_running("Payments Service", pay_service_url):
        echo_with_color(RED, f"❌ Payments service is not reachable at {pay_service_url}")
        return 1
    print()

    # --- Auth: acceptor for find + accept; issuer (if set) for loan wallet lookup ---
    _trace("Authenticating as acceptor.")
    echo_with_color(CYAN, "🔐 Authenticating as acceptor...")
    acceptor_token = login_user(auth_service_url, acceptor_email, acceptor_password)
    if not acceptor_token:
        echo_with_color(RED, f"❌ Failed to get JWT for: {acceptor_email}")
        return 1
    echo_with_color(GREEN, f"  ✅ Acceptor JWT obtained (first 50 chars): {acceptor_token[:50]}...")

    # Acceptor's default wallet for accept step (accept into this wallet)
    acceptor_entity_id = get_user_id_from_profile(auth_service_url, acceptor_token)
    acceptor_default_wallet_id = get_default_wallet_id(pay_service_url, acceptor_token, entity_id=acceptor_entity_id)
    if not acceptor_default_wallet_id:
        echo_with_color(RED, "❌ Could not resolve acceptor's default wallet (entityWallets empty or failed)")
        return 1
    echo_with_color(GREEN, f"  ✅ Acceptor default wallet: {acceptor_default_wallet_id}")

    # Entity ID for loan wallet naming: use issuer when set (loan wallets are created under issuer in issue_workflow)
    issuer_token = None
    if issuer_email and issuer_password:
        echo_with_color(CYAN, "🔐 Authenticating as issuer (for loan wallet lookup)...")
        issuer_token = login_user(auth_service_url, issuer_email, issuer_password)
        if issuer_token:
            echo_with_color(GREEN, f"  ✅ Issuer JWT obtained")
        else:
            echo_with_color(YELLOW, "  ⚠️  Issuer login failed; will use acceptor entity for loan wallet naming")
    if issuer_token:
        entity_user_id = get_user_id_from_profile(auth_service_url, issuer_token)
    else:
        entity_user_id = get_user_id_from_profile(auth_service_url, acceptor_token)
    issuer_entity_id_raw = (entity_user_id or "").replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "").strip()
    if not issuer_entity_id_raw:
        echo_with_color(RED, "❌ Could not resolve entity ID for loan wallet naming (set ISSUER_EMAIL if loan wallets are under issuer)")
        return 1
    print()

    # --- Process payment rows ---
    echo_with_color(CYAN, f"📖 Reading payment rows from CSV (max {payment_count})...")
    row_count = 0
    success_count = 0
    fail_count = 0

    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row_count >= payment_count:
                    break
                if len(row) < 7:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping row {row_count + 1}: insufficient columns")
                    fail_count += 1
                    continue
                loan_id = safe_get(row, 0)
                dwh_principal = safe_get(row, 3)
                mambu_total = safe_get(row, 6)
                if not loan_id or not dwh_principal or not mambu_total:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping row: missing MAMBU_LOANID, DWH_PRINCIPAL or MAMBU_TOTAL_AMOUNT")
                    fail_count += 1
                    continue
                row_count += 1
                try:
                    dwh_principal_wei = convert_currency_to_wei(dwh_principal)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ Row: currency conversion failed for DWH_PRINCIPAL: {e}")
                    fail_count += 1
                    continue
                try:
                    mambu_total_wei = convert_currency_to_wei(mambu_total)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ Row: currency conversion failed for MAMBU_TOTAL_AMOUNT: {e}")
                    fail_count += 1
                    continue

                print()
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                echo_with_color(CYAN, f"📦 Payment row {row_count}/{payment_count}: Loan ID={loan_id}")
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                _trace(f"Row input: loan_id={loan_id!r} DWH_PRINCIPAL={dwh_principal!r} ({dwh_principal_wei} wei) MAMBU_TOTAL_AMOUNT={mambu_total!r} ({mambu_total_wei} wei)")
                print()

                # --- Resolve loan wallet (for contract/payment resolution) ---
                _trace("Resolving loan wallet (convention: WLT-LOAN-{entity}-{loan_id}).")
                sanitized_loan_id = re.sub(r"[^a-zA-Z0-9-]", "-", str(loan_id)).strip("-") or "loan"
                loan_wallet_id = f"WLT-LOAN-{issuer_entity_id_raw}-{sanitized_loan_id}"
                wallet_token = issuer_token if issuer_token else acceptor_token
                existing_wallet = get_wallet_by_id(pay_service_url, wallet_token, loan_wallet_id)
                if not existing_wallet:
                    _trace(f"Loan wallet lookup failed: {loan_wallet_id} not found.")
                    echo_with_color(RED, f"  ❌ Loan wallet not found: {loan_wallet_id} (deploy loans first via issue_workflow)")
                    fail_count += 1
                    continue
                loan_wallet_address = (existing_wallet.get("address") or "").strip()
                if not loan_wallet_address or not loan_wallet_address.startswith("0x"):
                    _trace(f"Loan wallet has no valid address: {loan_wallet_id}")
                    echo_with_color(RED, f"  ❌ Loan wallet has no valid address: {loan_wallet_id}")
                    fail_count += 1
                    continue
                _trace(f"Loan wallet resolved: id={loan_wallet_id} address={loan_wallet_address[:18]}...")
                echo_with_color(GREEN, f"  ✅ Using loan wallet: {loan_wallet_id} ({loan_wallet_address[:18]}...)")
                print()

                # --- Find obligation initial payment: acceptor's contracts → contract for this loan → payments ---
                _trace("Finding obligation initial payment: acceptor contracts → contract matching loan → payments.")
                lookup_token = issuer_token if issuer_token else acceptor_token

                def _resolution_debug(step: str, info: dict) -> None:
                    if step == "acceptor_contracts":
                        _trace(f"Acceptor contracts: count={info.get('contract_count', 0)} error={info.get('error', '')!r}")
                    elif step == "acceptor_contract":
                        _trace(f"Acceptor contract for loan: contract_id={info.get('contract_id', '')!r} error={info.get('error', '')!r}")
                    elif step == "acceptor_contract_payments":
                        _trace(f"Contract payments: total={info.get('total', 0)} pending_count={info.get('pending_count', 0)} statuses={info.get('statuses', [])!r}")
                    elif step == "loan":
                        if info.get("success"):
                            _trace(f"Loan record: main_contract_id={info.get('main_contract_id', '')!r}")
                        else:
                            _trace(f"Loan record: not found — {info.get('error', 'unknown')!r}")
                    elif step == "contract":
                        _trace(f"Contract with payments: success={info.get('success')} payment_count={info.get('payment_count', 0)} error={info.get('error', '')!r}")
                    elif step == "payments":
                        _trace(f"Payments by entity: total={info.get('total', 0)} pending_count={info.get('pending_count', 0)} statuses={info.get('statuses', [])!r}")
                    elif step == "by_wallet":
                        _trace(f"Payments by wallet: loan_wallet_id={info.get('loan_wallet_id', '')!r} payment_count={info.get('payment_count', 0)}")

                payment = find_obligation_initial_payment_from_loan(
                    pay_service_url,
                    lookup_token,
                    loan_id=str(loan_id),
                    amount_wei=dwh_principal_wei,
                    acceptor_token=acceptor_token,
                    loan_wallet_id=loan_wallet_id,
                    loan_wallet_address=loan_wallet_address,
                    debug_callback=_resolution_debug,
                )
                if not payment:
                    _trace("No PENDING/PROCESSING obligation initial payment found for this loan.")
                    echo_with_color(RED, "  ❌ No PENDING/PROCESSING payment found for this loan. Ensure the loan exists and its obligation contract has an initial payment.")
                    fail_count += 1
                    continue
                payment_id = payment.get("id") or ""
                payment_amount_wei = payment.get("amount") or ""
                if not payment_id:
                    _trace("Resolved payment has no id.")
                    echo_with_color(RED, "  ❌ Resolved payment has no id")
                    fail_count += 1
                    continue
                _trace(f"Payment found: id={payment_id!r} amount={payment_amount_wei!r} status={payment.get('status', '')!r} contractId={payment.get('contractId', '')!r}")
                echo_with_color(GREEN, "  ✅ Obligation initial payment (from contract):")
                echo_with_color(BLUE, f"     id: {payment_id}")
                echo_with_color(BLUE, f"     amount: {payment_amount_wei} (wei)")
                echo_with_color(BLUE, f"     status: {payment.get('status', '')}")
                echo_with_color(BLUE, f"     contractId: {payment.get('contractId', '')}")
                print()

                # --- Accept this payment for the CSV amount only (not fill amount) into acceptor's default wallet ---
                accept_amount_wei = dwh_principal_wei  # amount from CSV (DWH_PRINCIPAL), not payment's full balance
                _trace(f"Calling accept: payment_id={payment_id!r} amount_wei={accept_amount_wei!r} (CSV amount) wallet_id={acceptor_default_wallet_id!r}")
                echo_with_color(CYAN, f"  Accepting payment (payment_id={payment_id}, amount={accept_amount_wei} wei from CSV) into wallet {acceptor_default_wallet_id}...")
                accept_res = accept_payment(
                    pay_service_url,
                    auth_service_url,
                    acceptor_email,
                    acceptor_password,
                    payment_id=payment_id,
                    amount=accept_amount_wei,
                    wallet_id=acceptor_default_wallet_id,
                    account_address=None,
                )
                if not accept_res.get("success"):
                    _trace(f"Accept failed: {accept_res.get('error', 'Unknown error')!r}")
                    echo_with_color(RED, f"  ❌ Accept failed: {accept_res.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                _trace(f"Accept succeeded: messageId={accept_res.get('data', {}).get('messageId', 'N/A')} transactionId={accept_res.get('data', {}).get('transactionId', 'N/A')}")
                echo_with_color(GREEN, "  ✅ Payment accepted for this amount.")
                print()

                # --- Create payment swap: partial credit (with obligor) vs cash (obligor=null), counterparty = loan account ---
                swap_deadline_raw = os.environ.get("SWAP_DEADLINE", "").strip()
                if swap_deadline_raw:
                    swap_deadline = swap_deadline_raw
                else:
                    swap_deadline = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                _trace(f"Creating payment swap: amount={accept_amount_wei} wei, obligor={loan_wallet_address[:18]}..., counterparty={loan_wallet_id!r}, deadline={swap_deadline!r}")
                echo_with_color(CYAN, f"  Creating payment swap (credit with obligor ↔ cash, counterparty={loan_wallet_id})...")
                swap_res = create_payment_swap(
                    pay_service_url,
                    acceptor_token,
                    counterparty=loan_wallet_id,
                    initiator_amount_wei=accept_amount_wei,
                    counterparty_amount_wei=accept_amount_wei,
                    denomination=denomination,
                    initiator_obligor_address=loan_wallet_address,
                    deadline=swap_deadline,
                    wallet_id=acceptor_default_wallet_id,
                    account_address=None,
                    counterparty_wallet_id=loan_wallet_id,
                )
                if not swap_res.get("success"):
                    _trace(f"Create payment swap failed: {swap_res.get('error', 'Unknown error')!r}")
                    echo_with_color(RED, f"  ❌ Create payment swap failed: {swap_res.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                _trace(f"Create payment swap succeeded: swapId={swap_res.get('swap_id', 'N/A')}")
                echo_with_color(GREEN, f"  ✅ Payment swap created (swapId: {swap_res.get('swap_id', 'N/A')}).")
                print()

                # --- Loan account (counterparty) completes the swap ---
                swap_id_created = swap_res.get("swap_id") or ""
                if not swap_id_created:
                    _trace("No swap_id in create swap response; skipping complete.")
                    echo_with_color(YELLOW, "  ⚠️  No swap_id in response; cannot complete swap.")
                    fail_count += 1
                    continue
                if not issuer_token:
                    _trace("Issuer credentials not set; swap created but not completed (set ISSUER_EMAIL/ISSUER_PASSWORD to complete as loan account).")
                    echo_with_color(YELLOW, "  ⚠️  Swap created; set ISSUER_EMAIL and ISSUER_PASSWORD to complete swap as loan account.")
                    success_count += 1
                    continue
                _trace(f"Completing swap {swap_id_created!r} as loan wallet {loan_wallet_id!r} (account_address={loan_wallet_address[:18]}...).")
                echo_with_color(CYAN, f"  Completing swap as loan account ({loan_wallet_id})...")
                complete_res = complete_swap_as_wallet(
                    pay_service_url,
                    issuer_token,
                    swap_id=swap_id_created,
                    account_address=loan_wallet_address,
                    wallet_id=loan_wallet_id,
                )
                if not complete_res.get("success"):
                    _trace(f"Complete swap failed: {complete_res.get('error', 'Unknown error')!r}")
                    echo_with_color(RED, f"  ❌ Complete swap failed: {complete_res.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                _trace("Complete swap succeeded.")
                echo_with_color(GREEN, "  ✅ Swap completed by loan account.")
                print()

                # --- Wait for swap payment records to be created (async processor) ---
                accept_all_delay = 8
                try:
                    accept_all_delay = int(os.environ.get("ACCEPT_ALL_DELAY_SECONDS", "8").strip())
                    if accept_all_delay < 0:
                        accept_all_delay = 8
                except ValueError:
                    pass
                if accept_all_delay > 0:
                    _trace(f"Waiting {accept_all_delay}s for payment records to be created...")
                    echo_with_color(CYAN, f"  Waiting {accept_all_delay}s for swap payment records...")
                    time.sleep(accept_all_delay)

                # --- Accept all (pending payables) by both parties ---
                # Acceptor received cash (obligor=null) from the swap → accept payables with no obligor filter.
                # Loan account received credit with obligor=loan_wallet → accept payables matching that obligor (try address then wallet_id).
                _trace("Accept all: acceptor (denomination, obligor=null) then loan account (denomination, obligor=loan_wallet).")
                accept_all_max_retries = 3
                key_acceptor = f"accept-all-acceptor-{sanitized_loan_id}-{int(time.time() * 1000)}"
                accept_all_acceptor = None
                for attempt in range(accept_all_max_retries):
                    if attempt > 0:
                        echo_with_color(CYAN, f"  Retry {attempt + 1}/{accept_all_max_retries} accept all (acceptor)...")
                        time.sleep(5)
                    echo_with_color(CYAN, f"  Accept all payables (acceptor, denomination={denomination!r}, obligor=null)...")
                    accept_all_acceptor = accept_all_tokens(
                        pay_service_url,
                        auth_service_url,
                        acceptor_email,
                        acceptor_password,
                        denomination=denomination,
                        idempotency_key=key_acceptor,
                        obligor=None,
                        wallet_id=acceptor_default_wallet_id,
                        account_address=None,
                    )
                    if not accept_all_acceptor.get("success"):
                        break
                    if (accept_all_acceptor.get("data") or {}).get("acceptedCount", 0) > 0:
                        break
                if not accept_all_acceptor or not accept_all_acceptor.get("success"):
                    _trace(f"Accept all (acceptor) failed: {(accept_all_acceptor or {}).get('error', 'Unknown')!r}")
                    echo_with_color(RED, f"  ❌ Accept all (acceptor) failed: {(accept_all_acceptor or {}).get('error', 'Unknown')}")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, "  ✅ Accept all (acceptor) done.")
                # Loan account: try obligor=address first, then obligor=wallet_id (backend may store either)
                accept_all_loan = None
                loan_obligors_to_try = [loan_wallet_address, loan_wallet_id]
                for obligor_idx, obligor_val in enumerate(loan_obligors_to_try):
                    key_loan = f"accept-all-loan-{sanitized_loan_id}-{obligor_idx}-{int(time.time() * 1000)}"
                    for attempt in range(accept_all_max_retries):
                        if attempt > 0:
                            echo_with_color(CYAN, f"  Retry {attempt + 1}/{accept_all_max_retries} accept all (loan account)...")
                            time.sleep(5)
                        echo_with_color(CYAN, f"  Accept all payables (loan account, denomination={denomination!r}, obligor=loan wallet)...")
                        accept_all_loan = accept_all_tokens(
                            pay_service_url,
                            auth_service_url,
                            issuer_email,
                            issuer_password,
                            denomination=denomination,
                            idempotency_key=key_loan,
                            obligor=obligor_val,
                            wallet_id=loan_wallet_id,
                            account_address=loan_wallet_address,
                        )
                        if not accept_all_loan.get("success"):
                            break
                        if (accept_all_loan.get("data") or {}).get("acceptedCount", 0) > 0:
                            break
                    if accept_all_loan and accept_all_loan.get("success") and (accept_all_loan.get("data") or {}).get("acceptedCount", 0) > 0:
                        break
                if not accept_all_loan or not accept_all_loan.get("success"):
                    _trace(f"Accept all (loan account) failed: {(accept_all_loan or {}).get('error', 'Unknown')!r}")
                    echo_with_color(RED, f"  ❌ Accept all (loan account) failed: {(accept_all_loan or {}).get('error', 'Unknown')}")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, "  ✅ Accept all (loan account) done.")
                success_count += 1

    except Exception as e:
        echo_with_color(RED, f"❌ Error reading CSV: {e}")
        return 1

    # --- Summary ---
    print()
    echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    echo_with_color(CYAN, "📊 Summary")
    echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    echo_with_color(BLUE, f"  Total payment rows processed: {row_count}")
    echo_with_color(GREEN, f"  Accepted: {success_count}")
    echo_with_color(RED, f"  Failed: {fail_count}")
    print()
    if success_count > 0:
        echo_with_color(GREEN, f"🎉 Processed {success_count} row(s): accept + swap + complete + accept_all. ✨")
    if success_count > 0:
        return 0
    echo_with_color(RED, "❌ No payments were accepted")
    return 1


def print_payment_usage() -> None:
    """Print help text for the payment workflow script."""
    print("Usage: payment_workflow.py [csv_file]")
    print()
    print("Arguments:")
    print("  csv_file   Path to payment CSV (default: wisr_payment_test.csv)")
    print()
    print("CSV columns (header): MAMBU_LOANID, MAMBU_PAYMENTDATE, MAMBU_TRANSACTION,")
    print("  DWH_PRINCIPAL, DWH_INTEREST, DWH_FEE, MAMBU_TOTAL_AMOUNT, MAMBU_ISDISHONOURED")
    print()
    print("Environment variables:")
    print("  ACCEPTOR_EMAIL       Entity that finds, accepts the payment, and creates the swap")
    print("  ACCEPTOR_PASSWORD    Password for ACCEPTOR_EMAIL")
    print("  ISSUER_EMAIL         Entity that owns loan wallets; required to complete swap as loan account.")
    print("  ISSUER_PASSWORD      Password for ISSUER_EMAIL (required for step 4).")
    print("  DENOMINATION         Asset ID for the swap (default: aud-token-asset)")
    print("  SWAP_DEADLINE        Optional; ISO deadline for the swap (default: 30 days from now)")
    print("  ACCEPT_ALL_DELAY_SECONDS  Wait before accept_all to allow payment records (default: 8)")
    print("  PAY_SERVICE_URL      Payments service URL")
    print("  AUTH_SERVICE_URL     Auth service URL")
    print("  PAYMENT_COUNT        Max rows to process (default: 100)")
    print()
    print("Flow per row:")
    print("  1) Find obligation initial payment for the loan (acceptor's contracts → contract → payments)")
    print("  2) Accept that payment for the CSV amount (DWH_PRINCIPAL) only, not the fill amount")
    print("  3) Create payment swap: partial credit (with obligor=loan) vs cash (obligor=null), counterparty=loan account")
    print("  4) Loan account completes the swap (requires ISSUER_EMAIL + ISSUER_PASSWORD)")
    print("  5) Accept all payables by acceptor and by loan account")
    print()
    print("Example:")
    print("  python3 payment_workflow.py wisr_payment_test.csv")
    print("  ACCEPTOR_EMAIL=issuer@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 payment_workflow.py")


def parse_payment_cli_args(script_dir: Path) -> str:
    """Parse argv and env into csv_file path."""
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        csv_file = os.environ.get("PAYMENT_CSV", "").strip() or str(script_dir / "wisr_payment_test.csv")
        return csv_file
    csv_file = args[0]
    csv_path = Path(csv_file)
    if not csv_path.is_absolute() and (script_dir / csv_path).exists():
        csv_file = str(script_dir / csv_path)
    elif not csv_path.is_absolute() and csv_path.exists():
        csv_file = str(csv_path.resolve())
    return csv_file


if __name__ == "__main__":
    sys.exit(main())
