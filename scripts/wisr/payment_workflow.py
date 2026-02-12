#!/usr/bin/env python3

"""
Payment workflow: process rows from a payment CSV (e.g. wisr_payment_test.csv).

Flow per row (same idea as nc_acacia.yaml command list — explicit steps):
  1) resolve_loan_wallet   — Resolve loan wallet (WLT-LOAN-{entity}-{loan_id})
  2) find_payment           — Find obligation initial payment for the loan
  3) accept_payment         — Accept that payment for CSV amount (DWH_PRINCIPAL) into acceptor wallet
  4) create_swap             — Create payment swap: credit DWH_PRINCIPAL vs cash MAMBU_TOTAL, counterparty=loan
  5) complete_swap          — Loan account completes the swap (optional if ISSUER_* set)
  6) accept_all_both        — Accept all payables by acceptor then by loan account

CSV columns (header row): MAMBU_LOANID, MAMBU_PAYMENTDATE, MAMBU_TRANSACTION, DWH_PRINCIPAL,
  DWH_INTEREST, DWH_FEE, MAMBU_TOTAL_AMOUNT, MAMBU_ISDISHONOURED.

Events are logged with [TRACE] so you can follow the flow.
"""

import csv
import sys
import time
from pathlib import Path
from typing import Optional

from modules import (
    accept_payment,
    complete_swap_as_wallet,
    create_payment_swap,
    convert_currency_to_wei,
    echo_with_color,
    find_obligation_initial_payment_from_loan,
    get_wallet_by_id,
    load_env_files,
    poll_accept_all_until_ready,
    safe_get,
)
from modules.console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW
from modules.loan_wallet import loan_wallet_id, sanitize_loan_id
from modules.payment_cli import parse_payment_cli_args, print_payment_usage
from modules.runner import payment_auth_context
from modules.workflow_common import (
    BANNER_LINE,
    print_workflow_summary,
    run_preflight_checks,
)
from modules.workflow_config import PaymentWorkflowConfig


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

    config = PaymentWorkflowConfig.from_env(script_dir, csv_file)
    echo_with_color(CYAN, "🚀 Payment Workflow - Find payment, accept amount, then create payment swap")
    print()
    echo_with_color(BLUE, "📋 Configuration:")
    echo_with_color(BLUE, f"  API Base URL: {config.pay_service_url}")
    echo_with_color(BLUE, f"  Auth Service: {config.auth_service_url}")
    echo_with_color(BLUE, f"  Acceptor (find + accept): {config.acceptor_email}")
    if config.issuer_email:
        echo_with_color(BLUE, f"  Issuer (loan wallet lookup): {config.issuer_email}")
    echo_with_color(BLUE, f"  CSV File: {config.csv_file}")
    echo_with_color(BLUE, f"  Denomination (swap): {config.denomination}")
    echo_with_color(BLUE, f"  Max payment rows: {config.payment_count}")
    print()

    if not config.acceptor_email or not config.acceptor_password:
        echo_with_color(RED, "❌ ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD are required")
        return 1

    if not run_preflight_checks(config.auth_service_url, config.pay_service_url):
        return 1
    print()

    _trace("Authenticating as acceptor.")
    echo_with_color(CYAN, "🔐 Authenticating as acceptor...")
    ctx = payment_auth_context(
        config.auth_service_url,
        config.pay_service_url,
        config.acceptor_email,
        config.acceptor_password,
        config.issuer_email or None,
        config.issuer_password or None,
    )
    if not ctx.get("acceptor_token"):
        echo_with_color(RED, f"❌ Failed to get JWT for: {config.acceptor_email}")
        return 1
    echo_with_color(GREEN, f"  ✅ Acceptor JWT obtained (first 50 chars): {ctx['acceptor_token'][:50]}...")
    if not ctx.get("acceptor_default_wallet_id"):
        echo_with_color(RED, "❌ Could not resolve acceptor's default wallet (entityWallets empty or failed)")
        return 1
    echo_with_color(GREEN, f"  ✅ Acceptor default wallet: {ctx['acceptor_default_wallet_id']}")
    if ctx.get("issuer_token"):
        echo_with_color(GREEN, "  ✅ Issuer JWT obtained")
    elif config.issuer_email and config.issuer_password:
        echo_with_color(YELLOW, "  ⚠️  Issuer login failed; will use acceptor entity for loan wallet naming")
    if not ctx.get("issuer_entity_id_raw"):
        echo_with_color(RED, "❌ Could not resolve entity ID for loan wallet naming (set ISSUER_EMAIL if loan wallets are under issuer)")
        return 1
    print()

    # --- Process payment rows ---
    echo_with_color(CYAN, f"📖 Reading payment rows from CSV (max {config.payment_count})...")
    row_count = 0
    success_count = 0
    fail_count = 0

    try:
        with open(config.csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if row_count >= config.payment_count:
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
                echo_with_color(PURPLE, BANNER_LINE)
                echo_with_color(CYAN, f"📦 Payment row {row_count}/{config.payment_count}: Loan ID={loan_id}")
                echo_with_color(PURPLE, BANNER_LINE)
                _trace(f"Row input: loan_id={loan_id!r} DWH_PRINCIPAL={dwh_principal!r} ({dwh_principal_wei} wei) MAMBU_TOTAL_AMOUNT={mambu_total!r} ({mambu_total_wei} wei)")
                print()

                # --- Step 1: Resolve loan wallet ---
                _trace("Resolving loan wallet (convention: WLT-LOAN-{entity}-{loan_id}).")
                sanitized_loan_id = sanitize_loan_id(loan_id)
                wlt_id = loan_wallet_id(ctx["issuer_entity_id_raw"], loan_id)
                wallet_token = ctx.get("issuer_token") or ctx["acceptor_token"]
                existing_wallet = get_wallet_by_id(config.pay_service_url, wallet_token, wlt_id)
                if not existing_wallet:
                    _trace(f"Loan wallet lookup failed: {wlt_id} not found.")
                    echo_with_color(RED, f"  ❌ Loan wallet not found: {wlt_id} (deploy loans first via issue_workflow)")
                    fail_count += 1
                    continue
                loan_wallet_address = (existing_wallet.get("address") or "").strip()
                if not loan_wallet_address or not loan_wallet_address.startswith("0x"):
                    _trace(f"Loan wallet has no valid address: {wlt_id}")
                    echo_with_color(RED, f"  ❌ Loan wallet has no valid address: {wlt_id}")
                    fail_count += 1
                    continue
                _trace(f"Loan wallet resolved: id={wlt_id} address={loan_wallet_address[:18]}...")
                echo_with_color(GREEN, f"  ✅ Using loan wallet: {wlt_id} ({loan_wallet_address[:18]}...)")
                print()

                # --- Step 2: Find obligation initial payment ---
                _trace("Finding obligation initial payment: acceptor contracts → contract matching loan → payments.")
                lookup_token = ctx.get("issuer_token") or ctx["acceptor_token"]

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
                    config.pay_service_url,
                    lookup_token,
                    loan_id=str(loan_id),
                    amount_wei=dwh_principal_wei,
                    acceptor_token=ctx["acceptor_token"],
                    loan_wallet_id=wlt_id,
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

                # --- Step 3: Accept payment for CSV amount into acceptor wallet ---
                accept_amount_wei = dwh_principal_wei
                _trace(f"Calling accept: payment_id={payment_id!r} amount_wei={accept_amount_wei!r} (CSV amount) wallet_id={ctx['acceptor_default_wallet_id']!r}")
                echo_with_color(CYAN, f"  Accepting payment (payment_id={payment_id}, amount={accept_amount_wei} wei from CSV) into wallet {ctx['acceptor_default_wallet_id']}...")
                accept_res = accept_payment(
                    config.pay_service_url,
                    config.auth_service_url,
                    config.acceptor_email,
                    config.acceptor_password,
                    payment_id=payment_id,
                    amount=accept_amount_wei,
                    wallet_id=ctx["acceptor_default_wallet_id"],
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

                # --- Step 4: Create payment swap ---
                _trace(f"Creating payment swap: credit={accept_amount_wei} wei (DWH_PRINCIPAL), cash={mambu_total_wei} wei (MAMBU_TOTAL), obligor={loan_wallet_address[:18]}..., counterparty={wlt_id!r}, deadline={config.swap_deadline!r}")
                echo_with_color(CYAN, f"  Creating payment swap (credit DWH_PRINCIPAL ↔ cash MAMBU_TOTAL_AMOUNT, counterparty={wlt_id})...")
                swap_res = create_payment_swap(
                    config.pay_service_url,
                    ctx["acceptor_token"],
                    counterparty=wlt_id,
                    initiator_amount_wei=accept_amount_wei,
                    counterparty_amount_wei=mambu_total_wei,
                    denomination=config.denomination,
                    initiator_obligor_address=loan_wallet_address,
                    deadline=config.swap_deadline,
                    wallet_id=ctx["acceptor_default_wallet_id"],
                    account_address=None,
                    counterparty_wallet_id=wlt_id,
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
                if not ctx.get("issuer_token"):
                    _trace("Issuer credentials not set; swap created but not completed (set ISSUER_EMAIL/ISSUER_PASSWORD to complete as loan account).")
                    echo_with_color(YELLOW, "  ⚠️  Swap created; set ISSUER_EMAIL and ISSUER_PASSWORD to complete swap as loan account.")
                    success_count += 1
                    continue
                # --- Step 5: Loan account completes the swap ---
                _trace(f"Completing swap {swap_id_created!r} as loan wallet {wlt_id!r} (account_address={loan_wallet_address[:18]}...).")
                echo_with_color(CYAN, f"  Completing swap as loan account ({wlt_id})...")
                complete_res = complete_swap_as_wallet(
                    config.pay_service_url,
                    ctx["issuer_token"],
                    swap_id=swap_id_created,
                    account_address=loan_wallet_address,
                    wallet_id=wlt_id,
                )
                if not complete_res.get("success"):
                    _trace(f"Complete swap failed: {complete_res.get('error', 'Unknown error')!r}")
                    echo_with_color(RED, f"  ❌ Complete swap failed: {complete_res.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                _trace("Complete swap succeeded.")
                echo_with_color(GREEN, "  ✅ Swap completed by loan account.")
                print()

                # --- Step 6: Accept all payables (acceptor then loan account) ---
                key_acceptor = f"accept-all-acceptor-{sanitized_loan_id}-{int(time.time() * 1000)}"
                echo_with_color(CYAN, f"  Polling accept_all (acceptor) until payables ready (timeout {config.accept_all_timeout_sec:.0f}s)...")
                accept_all_acceptor, acceptor_ready = poll_accept_all_until_ready(
                    config.pay_service_url,
                    config.auth_service_url,
                    config.acceptor_email,
                    config.acceptor_password,
                    denomination=config.denomination,
                    obligor=None,
                    wallet_id=ctx["acceptor_default_wallet_id"],
                    account_address=None,
                    idempotency_key=key_acceptor,
                    label="acceptor",
                    poll_interval_sec=config.accept_all_poll_interval_sec,
                    timeout_sec=config.accept_all_timeout_sec,
                    trace_cb=_trace,
                )
                if not accept_all_acceptor.get("success"):
                    _trace(f"Accept all (acceptor) failed: {accept_all_acceptor.get('error', 'Unknown')!r}")
                    echo_with_color(RED, f"  ❌ Accept all (acceptor) failed: {accept_all_acceptor.get('error', 'Unknown')}")
                    fail_count += 1
                    continue
                if not acceptor_ready:
                    echo_with_color(RED, f"  ❌ Accept all (acceptor): no payables appeared within {config.accept_all_timeout_sec:.0f}s")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, "  ✅ Accept all (acceptor) done.")

                key_loan = f"accept-all-loan-{sanitized_loan_id}-{int(time.time() * 1000)}"
                echo_with_color(CYAN, f"  Polling accept_all (loan account) until payables ready (timeout {config.accept_all_timeout_sec:.0f}s)...")
                accept_all_loan, loan_ready = poll_accept_all_until_ready(
                    config.pay_service_url,
                    config.auth_service_url,
                    config.issuer_email,
                    config.issuer_password,
                    denomination=config.denomination,
                    obligor=loan_wallet_address,
                    wallet_id=wlt_id,
                    account_address=loan_wallet_address,
                    idempotency_key=key_loan,
                    label="loan",
                    poll_interval_sec=config.accept_all_poll_interval_sec,
                    timeout_sec=config.accept_all_timeout_sec,
                    trace_cb=_trace,
                )
                if not loan_ready and accept_all_loan.get("success"):
                    _trace("Accept all (loan): no payables with obligor=address; trying obligor=wallet_id")
                    key_loan2 = f"accept-all-loan-wlt-{sanitized_loan_id}-{int(time.time() * 1000)}"
                    accept_all_loan, loan_ready = poll_accept_all_until_ready(
                        config.pay_service_url,
                        config.auth_service_url,
                        config.issuer_email,
                        config.issuer_password,
                        denomination=config.denomination,
                        obligor=wlt_id,
                        wallet_id=wlt_id,
                        account_address=loan_wallet_address,
                        idempotency_key=key_loan2,
                        label="loan(wallet_id)",
                        poll_interval_sec=config.accept_all_poll_interval_sec,
                        timeout_sec=min(60.0, config.accept_all_timeout_sec),
                        trace_cb=_trace,
                    )
                if not accept_all_loan.get("success"):
                    _trace(f"Accept all (loan account) failed: {accept_all_loan.get('error', 'Unknown')!r}")
                    echo_with_color(RED, f"  ❌ Accept all (loan account) failed: {accept_all_loan.get('error', 'Unknown')}")
                    fail_count += 1
                    continue
                if not loan_ready:
                    echo_with_color(RED, f"  ❌ Accept all (loan account): no payables appeared within timeout")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, "  ✅ Accept all (loan account) done.")
                success_count += 1

    except Exception as e:
        echo_with_color(RED, f"❌ Error reading CSV: {e}")
        return 1

    # --- Summary ---
    print_workflow_summary(
        row_count,
        success_count,
        fail_count,
        total_label="Total payment rows processed",
        success_label="Accepted",
        fail_label="Failed",
        success_message=f"🎉 Processed {success_count} row(s): accept + swap + complete + accept_all. ✨" if success_count > 0 else None,
        failure_message="❌ No payments were accepted",
    )
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
