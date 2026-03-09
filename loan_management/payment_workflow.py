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
import threading
import time
from pathlib import Path
from typing import Callable, Optional

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
    query_swap_status,
    safe_get,
)
from modules.console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW
from modules.loan_wallet import loan_wallet_id, sanitize_loan_id
from modules.messages import (
    get_messages_awaiting_signature,
    poll_until_sign_and_submit_manual_message,
    sign_and_submit_manual_message,
)
from modules.payment_cli import parse_payment_cli_args, print_payment_usage
# Manual for a single message is controlled by require_manual_signature on the API only; do not set wallet-level policy.
from modules.runner import payment_auth_context
from modules.workflow_common import (
    BANNER_LINE,
    print_workflow_summary,
    run_preflight_checks,
)
from modules.workflow_config import PaymentWorkflowConfig

# Optional: ensure issuer external key and register with loan wallets / investor account
try:
    from modules.register_external_key import (
        address_from_private_key,
        ensure_issuer_external_key,
        get_key_id_by_address,
        register_external_key,
        register_key_with_specific_wallet,
        sign_ownership_message,
        verify_external_key_ownership,
    )
    _HAS_ENSURE_ISSUER_KEY = True
except ImportError:
    _HAS_ENSURE_ISSUER_KEY = False


def _trace(msg: str) -> None:
    """Log a trace line so we can follow the flow (prefix [TRACE])."""
    echo_with_color(BLUE, f"  [TRACE] {msg}")


def _wait_accept_all_signatures(
    pay_service_url: str,
    ctx: dict,
    has_issuer: bool,
    has_acceptor: bool,
    trace_cb: Optional[Callable[[str], None]],
    max_wait_sec: float = 30.0,
    poll_interval_sec: float = 2.0,
) -> None:
    """After accept_all, wait for listener to sign any new messages (e.g. Retrieve, Send) until none awaiting or timeout."""
    start = time.monotonic()
    total_pending = 0
    echo_with_color(CYAN, "  Waiting for post-accept_all signatures (listener will sign Retrieve/Send if any)...")
    while (time.monotonic() - start) < max_wait_sec:
        total_pending = 0
        try:
            if has_acceptor and ctx.get("acceptor_token") and ctx.get("acceptor_user_id"):
                acc_msgs = get_messages_awaiting_signature(
                    pay_service_url, ctx["acceptor_token"], ctx["acceptor_user_id"]
                )
                total_pending += len(acc_msgs or [])
            if has_issuer and ctx.get("issuer_token") and ctx.get("issuer_user_id"):
                iss_msgs = get_messages_awaiting_signature(
                    pay_service_url, ctx["issuer_token"], ctx["issuer_user_id"]
                )
                total_pending += len(iss_msgs or [])
        except Exception as e:
            if trace_cb:
                trace_cb(f"Awaiting-signature check failed: {e}")
        if total_pending == 0:
            echo_with_color(GREEN, "  ✅ No messages awaiting signature.")
            return
        if trace_cb:
            trace_cb(f"Messages awaiting signature: {total_pending}, waiting...")
        time.sleep(poll_interval_sec)
    echo_with_color(YELLOW, f"  ⚠️  Still {total_pending} message(s) awaiting signature after {max_wait_sec:.0f}s (listener may sign shortly).")


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
    if config.require_manual_signature:
        echo_with_color(CYAN, "  Require manual signature: yes (complete-swap step will wait for UX or script signing)")
    if config.ensure_issuer_key:
        echo_with_color(CYAN, "  Ensure issuer external key: yes (create + save to file if first run)")
    if config.issuer_email:
        echo_with_color(BLUE, f"  Issuer external key file: {config.issuer_external_key_file}")
    if config.require_manual_signature:
        echo_with_color(BLUE, f"  Investor external key file: {config.investor_external_key_file}")
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

    # Optional: ensure issuer has an external key (create + save to file on first run); capture key_id and address
    issuer_external_key_id = None
    issuer_key_address = None
    run_ensure = config.ensure_issuer_key or config.require_manual_signature
    if run_ensure and ctx.get("issuer_user_id") and ctx.get("issuer_token"):
        if _HAS_ENSURE_ISSUER_KEY:
            key_path_ensure = (
                Path(config.issuer_external_key_file)
                if Path(config.issuer_external_key_file).is_absolute()
                else (config.script_dir / config.issuer_external_key_file).resolve()
            )
            echo_with_color(CYAN, "🔑 Ensuring issuer external key (create + save to file if first time)...")
            try:
                issuer_key_address, _pk, _kp, issuer_external_key_id = ensure_issuer_external_key(
                    auth_service_url=config.auth_service_url,
                    jwt_token=ctx["issuer_token"],
                    user_id=ctx["issuer_user_id"],
                    key_file_path=key_path_ensure,
                    key_name=config.issuer_external_key_name,
                    register_with_wallet=False,
                    verify_ownership=True,
                )
                if _kp is not None:
                    echo_with_color(GREEN, f"  ✅ Issuer external key created and registered: {issuer_key_address}")
                else:
                    echo_with_color(GREEN, f"  ✅ Issuer external key loaded from file: {issuer_key_address}")
                if not issuer_external_key_id and config.require_manual_signature:
                    echo_with_color(YELLOW, "  ⚠️  Could not resolve issuer key id; will not register with loan wallets")
            except Exception as e:
                echo_with_color(RED, f"  ❌ Ensure issuer key failed: {e}")
                return 1
            print()
        else:
            echo_with_color(YELLOW, "  ⚠️  ENSURE_ISSUER_EXTERNAL_KEY set but eth_account not installed; pip install eth-account")
            print()

    # Ensure investor (acceptor) has their own external key (separate from issuer key) and register it with acceptor wallet.
    # Same-entity flow: investor key + investor account + investor wallet → no auth UNIQUE or AddOwner cross-entity issues.
    investor_external_key_id = None
    if config.require_manual_signature and ctx.get("acceptor_token") and ctx.get("acceptor_user_id") and ctx.get("acceptor_default_wallet_id"):
        if _HAS_ENSURE_ISSUER_KEY:
            investor_key_path = (
                Path(config.investor_external_key_file)
                if Path(config.investor_external_key_file).is_absolute()
                else (config.script_dir / config.investor_external_key_file).resolve()
            )
            echo_with_color(CYAN, "🔑 Ensuring investor (acceptor) external key (create + save to file if first time)...")
            try:
                _inv_addr, _inv_pk, _inv_kp, investor_external_key_id = ensure_issuer_external_key(
                    auth_service_url=config.auth_service_url,
                    jwt_token=ctx["acceptor_token"],
                    user_id=ctx["acceptor_user_id"],
                    key_file_path=investor_key_path,
                    key_name=config.investor_external_key_name,
                    register_with_wallet=False,
                    verify_ownership=True,
                )
                if _inv_kp is not None:
                    echo_with_color(GREEN, f"  ✅ Investor external key created and registered: {_inv_addr}")
                else:
                    echo_with_color(GREEN, f"  ✅ Investor external key loaded from file: {_inv_addr}")
            except Exception as e:
                echo_with_color(RED, f"  ❌ Ensure investor key failed: {e}")
                return 1
            # Register investor key with acceptor's wallet (same entity → AddOwner succeeds)
            try:
                acceptor_wallet = get_wallet_by_id(
                    config.pay_service_url,
                    ctx["acceptor_token"],
                    ctx["acceptor_default_wallet_id"],
                )
                acceptor_wallet_address = (acceptor_wallet.get("address") or "").strip() if acceptor_wallet else ""
                if acceptor_wallet_address and acceptor_wallet_address.startswith("0x") and investor_external_key_id:
                    register_key_with_specific_wallet(
                        config.auth_service_url,
                        ctx["acceptor_token"],
                        investor_external_key_id,
                        acceptor_wallet_address,
                    )
                    echo_with_color(GREEN, "  ✅ Investor key registered with investor (acceptor) wallet for manual signing")
            except Exception as reg_err:
                echo_with_color(YELLOW, f"  ⚠️  Register investor key with wallet failed (continuing): {reg_err}")
            print()
        print()

    # --- Start manual signature listener: issuer key for issuer messages, investor key for acceptor messages ---
    listener_stop = threading.Event()
    listener_thread = None
    has_issuer = ctx.get("issuer_user_id") and ctx.get("issuer_token")
    has_acceptor = ctx.get("acceptor_user_id") and ctx.get("acceptor_token")
    if config.require_manual_signature and (has_issuer or has_acceptor):
        def _resolve_key_path(cfg_path: str) -> Path:
            p = Path(cfg_path)
            return p if p.is_absolute() else (config.script_dir / cfg_path).resolve()

        issuer_key_path = _resolve_key_path(config.issuer_external_key_file)
        investor_key_path = _resolve_key_path(config.investor_external_key_file)
        participants: list[tuple[str, str, str, str]] = []  # (label, jwt_token, user_id, private_key_hex)
        if has_issuer and issuer_key_path.exists():
            try:
                pk = issuer_key_path.read_text().strip().removeprefix("0x").strip()
                if pk:
                    participants.append(("issuer", ctx["issuer_token"], ctx["issuer_user_id"], pk))
            except Exception:
                pass
        if has_acceptor and investor_key_path.exists():
            try:
                pk = investor_key_path.read_text().strip().removeprefix("0x").strip()
                if pk:
                    participants.append(("acceptor", ctx["acceptor_token"], ctx["acceptor_user_id"], pk))
            except Exception:
                pass
        if participants:
            try:
                signed_ids: set[str] = set()

                def _listen_and_sign():
                    poll_interval = 3.0
                    while True:
                        try:
                            for label, jwt_token, user_id, private_key_hex in participants:
                                messages = get_messages_awaiting_signature(
                                    config.pay_service_url, jwt_token, user_id
                                )
                                new_messages = [m for m in messages if m.get("id") and str(m["id"]) not in signed_ids]
                                for m in new_messages:
                                    mid = str(m["id"])
                                    signed_ids.add(mid)
                                    try:
                                        sign_and_submit_manual_message(
                                            config.pay_service_url,
                                            jwt_token,
                                            user_id,
                                            mid,
                                            private_key_hex,
                                        )
                                        echo_with_color(GREEN, f"  ✅ [Listener] Signed and submitted message {mid} ({label})")
                                    except Exception as e:
                                        echo_with_color(RED, f"  ❌ [Listener] Failed to sign {mid}: {e}")
                                        signed_ids.discard(mid)
                        except Exception as e:
                            echo_with_color(RED, f"  ❌ [Listener] Poll error: {e}")
                        if listener_stop.wait(timeout=poll_interval):
                            break

                listener_thread = threading.Thread(target=_listen_and_sign, daemon=True)
                listener_thread.start()
                echo_with_color(GREEN, "  ✅ Manual signature listener started (issuer key for issuer, investor key for acceptor)")
            except Exception as e:
                echo_with_color(YELLOW, f"  ⚠️  Could not start manual signature listener: {e}. Run manual_signature_flow.py listen in another terminal.")
        else:
            missing = []
            if has_issuer and not (issuer_key_path.exists() and issuer_key_path.read_text().strip()):
                missing.append(str(issuer_key_path))
            if has_acceptor and not (investor_key_path.exists() and investor_key_path.read_text().strip()):
                missing.append(str(investor_key_path))
            echo_with_color(YELLOW, f"  ⚠️  Missing or empty key file(s): {missing}; manual signature listener not started.")
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
                # Register issuer external key with this loan wallet so manual signature can sign for it
                if config.require_manual_signature and issuer_external_key_id and loan_wallet_address.startswith("0x") and ctx.get("issuer_token"):
                    if _HAS_ENSURE_ISSUER_KEY:
                        try:
                            register_key_with_specific_wallet(
                                config.auth_service_url,
                                ctx["issuer_token"],
                                issuer_external_key_id,
                                loan_wallet_address,
                            )
                            echo_with_color(GREEN, f"  ✅ Issuer external key registered with loan wallet {wlt_id}")
                        except Exception as reg_err:
                            echo_with_color(YELLOW, f"  ⚠️  Register key with loan wallet failed (continuing): {reg_err}")
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
                    require_manual_signature=config.require_manual_signature,
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
                    require_manual_signature=config.require_manual_signature,
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
                    require_manual_signature=config.require_manual_signature,
                )
                if not complete_res.get("success"):
                    _trace(f"Complete swap failed: {complete_res.get('error', 'Unknown error')!r}")
                    echo_with_color(RED, f"  ❌ Complete swap failed: {complete_res.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                # When require_manual_signature is True, the API returns success as soon as the message is
                # submitted (not when the swap is completed). We must sign that message with the issuer key
                # and then poll until the swap is COMPLETED.
                message_id = complete_res.get("messageId")
                if config.require_manual_signature and message_id and ctx.get("issuer_user_id") and ctx.get("issuer_token"):
                    key_path = (
                        Path(config.issuer_external_key_file)
                        if Path(config.issuer_external_key_file).is_absolute()
                        else (config.script_dir / config.issuer_external_key_file).resolve()
                    )
                    if key_path.exists():
                        try:
                            private_key_hex = key_path.read_text().strip().removeprefix("0x").strip()
                            if private_key_hex:
                                echo_with_color(CYAN, f"  Signing completeSwap message {message_id} with issuer key...")
                                try:
                                    poll_until_sign_and_submit_manual_message(
                                        config.pay_service_url,
                                        ctx["issuer_token"],
                                        ctx["issuer_user_id"],
                                        message_id,
                                        private_key_hex,
                                        poll_interval_seconds=2.0,
                                        max_wait_seconds=120.0,
                                    )
                                    echo_with_color(GREEN, f"  ✅ Signed and submitted completeSwap message (manual signature).")
                                except Exception as sign_err:
                                    echo_with_color(RED, f"  ❌ Manual signature failed: {sign_err}")
                                    fail_count += 1
                                    continue
                            else:
                                echo_with_color(YELLOW, "  ⚠️  Key file empty; swap message may remain awaiting signature.")
                        except Exception as e:
                            echo_with_color(RED, f"  ❌ Could not read issuer key for manual signature: {e}")
                            fail_count += 1
                            continue
                    else:
                        echo_with_color(YELLOW, f"  ⚠️  Issuer key file not found: {key_path}; swap message may remain awaiting signature.")
                # Poll until swap status is COMPLETED (backend returns success when message is submitted, not when swap is done)
                echo_with_color(CYAN, f"  Polling swap status until COMPLETED (timeout 120s)...")
                swap_complete_timeout = 120.0
                swap_poll_interval = 2.0
                swap_start = time.monotonic()
                swap_completed = False
                while (time.monotonic() - swap_start) < swap_complete_timeout:
                    swap_data = query_swap_status(
                        config.pay_service_url, ctx["issuer_token"], swap_id_created
                    )
                    if swap_data:
                        status = (swap_data.get("status") or "").strip()
                        _trace(f"Swap status: {status}")
                        if status == "COMPLETED":
                            swap_completed = True
                            break
                        if status in ("CANCELLED", "EXPIRED", "FORFEITED"):
                            echo_with_color(RED, f"  ❌ Swap ended in status: {status}")
                            break
                    time.sleep(swap_poll_interval)
                if not swap_completed:
                    echo_with_color(RED, f"  ❌ Swap did not complete within {swap_complete_timeout:.0f}s")
                    fail_count += 1
                    continue
                _trace("Swap completed.")
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
                # Wait for listener to sign any post-accept_all messages (e.g. Retrieve, Send) so "last" signatures complete
                if config.require_manual_signature and listener_thread is not None:
                    _wait_accept_all_signatures(
                        config.pay_service_url,
                        ctx,
                        has_issuer,
                        has_acceptor,
                        _trace,
                        max_wait_sec=30.0,
                        poll_interval_sec=2.0,
                    )
                success_count += 1

    except Exception as e:
        echo_with_color(RED, f"❌ Error reading CSV: {e}")
        return 1

    if listener_thread is not None:
        listener_stop.set()

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
