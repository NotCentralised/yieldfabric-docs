#!/usr/bin/env python3

"""
Issue workflow: process loans from a CSV and create composed contracts (obligations + optional swap).

Flow per loan (same idea as nc_acacia.yaml command list — explicit steps):
  1) mint_and_deposit    — Optional: mint then deposit loan amount as investor (when MINT_BEFORE_LOANS)
  2) resolve_loan_wallet  — Use or create loan wallet WLT-LOAN-{entity_id}-{loan_id}
  3) register_key        — Optional: register issuer external key with loan wallet
  4) issue_workflow      — Call issue or issue+swap composed contract workflow
  5) poll_workflow        — Poll until workflow completed
  6) complete_swap       — Optional: acceptor completes swap (issue_swap_complete)
  7) accept_all_loan     — Optional: loan account accepts resulting payables

Each loan uses a dedicated sub-account wallet (WLT-LOAN-{entity_id}-{loan_id}); obligor and
counterpart in the contract are that sub-account. X-Account-Address and X-Wallet-Id are
passed when calling the workflow and when accepting the obligation.

This script is a thin entry point; reusable logic lives in the modules package.
"""

import csv
import sys
import threading
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

from modules import (
    ACTION_ISSUE_SWAP,
    ACTION_ISSUE_SWAP_COMPLETE,
    accept_all_tokens,
    burn_tokens,
    complete_swap,
    convert_currency_to_wei,
    convert_date_to_iso,
    create_wallet_in_payments,
    deploy_user_account,
    deposit_tokens,
    echo_with_color,
    extract_loan_data,
    get_wallet_by_id,
    issue_composed_contract_issue_swap_workflow,
    issue_composed_contract_workflow,
    load_env_files,
    mint_tokens,
    parse_bool_env,
    poll_swap_completion,
    poll_workflow_status,
    safe_get,
)
from modules.messages import get_messages_awaiting_signature, sign_and_submit_manual_message
from modules.cli import parse_cli_args, print_usage
from modules.console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW
from modules.loan_wallet import loan_wallet_id, sanitize_loan_id
from modules.runner import issue_auth_context
# Manual for a single message is controlled by require_manual_signature on the API only; do not set wallet-level policy.
from modules.workflow_common import (
    BANNER_LINE,
    print_workflow_summary,
    run_preflight_checks,
)
from modules.workflow_config import IssueWorkflowConfig

# Optional: ensure issuer external key (create + register on first run) and register with loan wallet
try:
    from modules.register_external_key import (
        ensure_issuer_external_key,
        register_key_with_specific_wallet,
    )
    _HAS_ENSURE_ISSUER_KEY = True
except ImportError:
    _HAS_ENSURE_ISSUER_KEY = False


def main() -> int:
    """Main entry: load env, parse args, run preflight, process loans."""
    script_dir = Path(__file__).parent.resolve()
    repo_root = script_dir.parent.parent
    load_env_files(script_dir, repo_root)

    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help"):
        print_usage()
        return 0

    user_email, password, csv_file, action_mode = parse_cli_args(script_dir)

    if not Path(csv_file).exists():
        echo_with_color(RED, f"❌ CSV file not found: {csv_file}")
        return 1

    config = IssueWorkflowConfig.from_env(
        script_dir, csv_file,
        user_email_override=user_email,
        password_override=password,
        action_mode_override=action_mode,
    )
    echo_with_color(CYAN, "🚀 Starting Issue Composed Contract WorkFlow API Test - Processing Loans from CSV")
    print()
    echo_with_color(BLUE, "📋 Configuration:")
    echo_with_color(BLUE, f"  API Base URL: {config.pay_service_url}")
    echo_with_color(BLUE, f"  Auth Service: {config.auth_service_url}")
    echo_with_color(BLUE, f"  User (Initiator): {config.user_email}")
    echo_with_color(BLUE, f"  Obligation counterpart: {config.counterpart}")
    echo_with_color(BLUE, f"  Denomination: {config.denomination}")
    echo_with_color(BLUE, f"  CSV File: {config.csv_file}")
    echo_with_color(BLUE, f"  Max loans to process: {config.max_loans}")
    echo_with_color(PURPLE, f"  Action mode: {config.action_mode}")
    if config.deploy_issuer:
        echo_with_color(CYAN, "  Deploy issuer account: yes (before workflows)" + (" [default for issue_swap_complete]" if not parse_bool_env("DEPLOY_ISSUER_ACCOUNT") else ""))
    if config.deploy_acceptor:
        echo_with_color(CYAN, "  Deploy acceptor account: yes (before workflows)" + (" [default for issue_swap_complete]" if not parse_bool_env("DEPLOY_ACCEPTOR_ACCOUNT") else ""))
    if config.deploy_per_loan:
        echo_with_color(CYAN, "  Deploy one wallet per loan under issuer entity: yes" + (" [default for issue_swap/issue_swap_complete]" if not parse_bool_env("DEPLOY_ACCOUNT_PER_LOAN") else ""))
    if config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
        if config.action_mode == ACTION_ISSUE_SWAP_COMPLETE and (not config.acceptor_email or not config.acceptor_password):
            echo_with_color(RED, "❌ ACTION_MODE=issue_swap_complete requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD")
            return 1
        echo_with_color(BLUE, f"  Swap counterparty: {config.swap_counterparty}")
        echo_with_color(BLUE, f"  Payment denomination (swap): {config.payment_denomination}")
        if config.env_payment_amount:
            echo_with_color(BLUE, f"  Payment amount (swap, from env): {config.env_payment_amount}")
        else:
            echo_with_color(BLUE, "  Payment amount (swap): obligation notional (per loan)")
        if config.env_deadline:
            echo_with_color(BLUE, f"  Deadline (swap, from env): {config.env_deadline}")
        else:
            echo_with_color(BLUE, "  Deadline (swap): obligation maturity (per loan)")
        echo_with_color(BLUE, f"  Acceptor (will complete swap): {config.acceptor_email}" if config.acceptor_email else "  Acceptor: (none - swap will remain pending)")
    if config.mint_before_env:
        if config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE) and config.policy_secret and config.acceptor_email and config.acceptor_password:
            echo_with_color(CYAN, f"  Mint before loans: yes (as investor {config.acceptor_email}, per loan)")
        elif config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE) and (not config.acceptor_email or not config.acceptor_password):
            echo_with_color(RED, "  MINT_BEFORE_LOANS requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD (mint runs as investor)")
            return 1
        elif config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
            echo_with_color(YELLOW, "  Mint before loans: yes but POLICY_SECRET missing; will skip mint")
        else:
            echo_with_color(YELLOW, "  Mint before loans: yes but only applies to issue_swap/issue_swap_complete; will skip")
    if config.burn_after_env:
        echo_with_color(CYAN, f"  Burn after loans: yes (amount: {config.burn_amount or 'N/A'})")
    if config.require_manual_signature:
        echo_with_color(CYAN, "  Require manual signature: yes (messages will wait for UX signing)")
    print()

    # --- Preflight ---
    pay_extra = [
        (YELLOW, "Please start the payments service:"),
        (BLUE, "   Local: cd ../yieldfabric-payments && cargo run"),
        (BLUE, f"   REST API endpoint will be available at: {config.pay_service_url}/api/composed_contract/issue_workflow"),
    ]
    if not run_preflight_checks(config.auth_service_url, config.pay_service_url, pay_extra_lines=pay_extra):
        return 1
    try:
        response = requests.post(
            f"{config.pay_service_url.rstrip('/')}/api/composed_contract/issue_workflow",
            json={},
            timeout=5,
        )
        if response.status_code == 404:
            echo_with_color(YELLOW, "⚠️  Warning: Endpoint returned 404. The server may need to be restarted to pick up the new routes.")
            echo_with_color(YELLOW, "   Make sure the server was built with the latest code including composed_contract_issue workflow.")
            print()
    except Exception:
        pass
    print()

    # --- Auth & deploy (runner) ---
    echo_with_color(CYAN, "🔐 Authenticating...")
    ctx = issue_auth_context(config)
    if not ctx.get("jwt_token"):
        echo_with_color(RED, f"❌ Failed to get JWT token for user: {config.user_email}")
        return 1
    if ctx.get("_deploy_issuer_error"):
        echo_with_color(RED, f"  ❌ Issuer account deployment failed: {ctx['_deploy_issuer_error']}")
        return 1
    if ctx.get("_deploy_acceptor_error"):
        echo_with_color(RED, f"  ❌ Acceptor account deployment failed: {ctx['_deploy_acceptor_error']}")
        return 1
    jwt_token = ctx["jwt_token"]
    issuer_user_id = ctx.get("issuer_user_id")
    issuer_entity_id_raw = ctx.get("issuer_entity_id_raw") or ""
    echo_with_color(GREEN, f"  ✅ JWT token obtained (first 50 chars): {jwt_token[:50]}...")
    if config.deploy_issuer:
        echo_with_color(GREEN, "  ✅ Issuer account deployed")
    if config.deploy_acceptor:
        echo_with_color(GREEN, "  ✅ Acceptor account deployed")
    print()

    # Optional: ensure issuer has an external key (create + save to file + register on first run)
    issuer_external_key_id = None
    if config.ensure_issuer_key and issuer_user_id:
        if _HAS_ENSURE_ISSUER_KEY:
            key_path = (
                Path(config.issuer_external_key_file)
                if Path(config.issuer_external_key_file).is_absolute()
                else (config.script_dir / config.issuer_external_key_file).resolve()
            )
            echo_with_color(CYAN, "🔑 Ensuring issuer external key (create + register if first time)...")
            try:
                _addr, _pk, _kp, issuer_external_key_id = ensure_issuer_external_key(
                    auth_service_url=config.auth_service_url,
                    jwt_token=jwt_token,
                    user_id=issuer_user_id,
                    key_file_path=key_path,
                    key_name=config.issuer_external_key_name,
                    register_with_wallet=False,
                    verify_ownership=True,
                )
                if _kp is not None:
                    echo_with_color(GREEN, f"  ✅ Issuer external key created and registered: {_addr}")
                else:
                    echo_with_color(GREEN, f"  ✅ Issuer external key loaded from file: {_addr}")
                if not issuer_external_key_id:
                    echo_with_color(YELLOW, "  ⚠️  Could not resolve issuer key id; will not register with loan wallets")
            except Exception as e:
                echo_with_color(RED, f"  ❌ Ensure issuer key failed: {e}")
                return 1
            print()
        else:
            echo_with_color(YELLOW, "  ⚠️  ENSURE_ISSUER_EXTERNAL_KEY set but eth_account not installed; pip install eth-account")
            print()

    deploy_per_loan = config.deploy_per_loan
    if deploy_per_loan and not issuer_user_id:
        echo_with_color(YELLOW, "  ⚠️  DEPLOY_ACCOUNT_PER_LOAN enabled but could not get issuer user_id; skipping per-loan deploy")
        deploy_per_loan = False
    elif deploy_per_loan:
        echo_with_color(CYAN, f"  📌 Deploy one new wallet per loan under issuer entity (issuer user_id: {issuer_user_id[:8]}...)")
        print()

    # --- Start manual signature listener in background when require_manual_signature is True ---
    listener_stop = threading.Event()
    listener_thread = None
    if config.require_manual_signature and issuer_user_id:
        key_path = (
            Path(config.issuer_external_key_file)
            if Path(config.issuer_external_key_file).is_absolute()
            else (config.script_dir / config.issuer_external_key_file).resolve()
        )
        if key_path.exists():
            try:
                private_key_hex = key_path.read_text().strip().removeprefix("0x").strip()
                if private_key_hex:
                    signed_ids = set()

                    def _listen_and_sign():
                        poll_interval = 3.0
                        while True:
                            try:
                                messages = get_messages_awaiting_signature(
                                    config.pay_service_url, jwt_token, issuer_user_id
                                )
                                new_messages = [m for m in messages if m.get("id") and str(m["id"]) not in signed_ids]
                                for m in new_messages:
                                    mid = str(m["id"])
                                    signed_ids.add(mid)
                                    try:
                                        sign_and_submit_manual_message(
                                            config.pay_service_url,
                                            jwt_token,
                                            issuer_user_id,
                                            mid,
                                            private_key_hex,
                                        )
                                        echo_with_color(GREEN, f"  ✅ [Listener] Signed and submitted message {mid}")
                                    except Exception as e:
                                        echo_with_color(RED, f"  ❌ [Listener] Failed to sign {mid}: {e}")
                                        signed_ids.discard(mid)
                            except Exception as e:
                                echo_with_color(RED, f"  ❌ [Listener] Poll error: {e}")
                            if listener_stop.wait(timeout=poll_interval):
                                break

                    listener_thread = threading.Thread(target=_listen_and_sign, daemon=True)
                    listener_thread.start()
                    echo_with_color(GREEN, "  ✅ Manual signature listener started in background (will sign messages as they appear)")
                else:
                    echo_with_color(YELLOW, "  ⚠️  Key file is empty; manual signature listener not started. Run manual_signature_flow.py listen in another terminal.")
            except Exception as e:
                echo_with_color(YELLOW, f"  ⚠️  Could not start manual signature listener: {e}. Run manual_signature_flow.py listen in another terminal.")
        else:
            echo_with_color(YELLOW, f"  ⚠️  Key file not found: {key_path}; manual signature listener not started. Run manual_signature_flow.py listen in another terminal.")
        print()

    # --- Process loans ---
    echo_with_color(CYAN, f"📖 Reading loans from CSV file (max {config.max_loans})...")
    loan_count = 0
    success_count = 0
    fail_count = 0

    try:
        with open(config.csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if loan_count >= config.max_loans:
                    break
                loan_count += 1
                if len(row) < 8:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping loan {loan_count}: insufficient columns")
                    fail_count += 1
                    continue
                loan_id = safe_get(row, 0)
                prin_out = safe_get(row, 7)
                maturity = safe_get(row, 4)
                if not loan_id or not prin_out or not maturity:
                    echo_with_color(YELLOW, f"  ⚠️  Skipping loan {loan_count}: missing required data")
                    fail_count += 1
                    continue
                loan_data = extract_loan_data(row)
                print()
                echo_with_color(PURPLE, BANNER_LINE)
                echo_with_color(CYAN, f"📦 Processing Loan {loan_count}/{config.max_loans}: ID={loan_id}")
                echo_with_color(PURPLE, BANNER_LINE)
                print()
                try:
                    amount_wei = convert_currency_to_wei(prin_out)
                except Exception as e:
                    echo_with_color(RED, f"  ❌ Error converting currency: {e}")
                    fail_count += 1
                    continue
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

                # --- Step 1: Optional mint and deposit (investor) ---
                if config.mint_before_env and config.policy_secret and config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                    if not config.acceptor_email or not config.acceptor_password:
                        echo_with_color(RED, "  ❌ MINT_BEFORE_LOANS requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD (mint runs as investor)")
                        fail_count += 1
                        continue
                    echo_with_color(CYAN, f"  🪙 Minting loan amount as investor ({config.acceptor_email}) for loan {loan_id}...")
                    mint_res = mint_tokens(
                        config.pay_service_url, config.auth_service_url, config.acceptor_email, config.acceptor_password,
                        config.denomination, amount_wei, config.policy_secret,
                    )
                    if not mint_res.get("success"):
                        echo_with_color(RED, f"  ❌ Mint failed for loan {loan_id}: {mint_res.get('error', 'Unknown error')}")
                        fail_count += 1
                        continue
                    echo_with_color(GREEN, f"  ✅ Minted {prin_out} to {config.acceptor_email}")
                    echo_with_color(CYAN, f"  🏦 Depositing {prin_out} as {config.acceptor_email}...")
                    idemp_key = f"deposit-loan-{loan_id}-{int(time.time() * 1000)}"
                    dep_res = deposit_tokens(
                        config.pay_service_url, config.auth_service_url, config.acceptor_email, config.acceptor_password,
                        config.denomination, amount_wei, idemp_key,
                    )
                    if not dep_res.get("success"):
                        echo_with_color(RED, f"  ❌ Deposit failed for loan {loan_id}: {dep_res.get('error', 'Unknown error')}")
                        fail_count += 1
                        continue
                    echo_with_color(GREEN, f"  ✅ Deposited {prin_out} as {config.acceptor_email}")
                    print()

                # --- Step 2: Resolve or create loan wallet ---
                obligor_wallet_id_for_loan = None
                obligor_address_for_loan = None
                if issuer_entity_id_raw:
                    sanitized_loan_id = sanitize_loan_id(loan_id)
                    wlt_id = loan_wallet_id(issuer_entity_id_raw, loan_id)
                    existing_wallet = get_wallet_by_id(config.pay_service_url, jwt_token, wlt_id)
                    if existing_wallet:
                        echo_with_color(GREEN, f"  ✅ Using existing wallet for loan {loan_id}: {wlt_id}")
                        obligor_wallet_id_for_loan = wlt_id
                        obligor_address_for_loan = (existing_wallet.get("address") or "").strip()
                    elif deploy_per_loan and issuer_user_id:
                        echo_with_color(CYAN, f"  🔐 Creating new wallet for loan {loan_id}: {wlt_id}...", file=sys.stderr)
                        per_loan_result = deploy_user_account(config.auth_service_url, jwt_token, issuer_user_id)
                        if per_loan_result.get("success"):
                            addr = (per_loan_result.get("new_account_address") or "").strip()
                            if not addr or addr == "N/A" or not addr.startswith("0x"):
                                echo_with_color(YELLOW, f"  ⚠️  Deploy succeeded but no valid address for loan {loan_id}; skipping wallet registration")
                            else:
                                echo_with_color(GREEN, f"  ✅ New wallet for loan {loan_id}: {addr}")
                                create_result = create_wallet_in_payments(
                                    config.pay_service_url,
                                    jwt_token,
                                    issuer_entity_id_raw,
                                    addr,
                                    wlt_id,
                                    name=f"Loan {loan_id}",
                                    description=f"Wallet for loan ID {loan_id}",
                                )
                                if create_result.get("success"):
                                    echo_with_color(GREEN, f"  ✅ Registered wallet in payments: {wlt_id}")
                                    obligor_wallet_id_for_loan = wlt_id
                                    obligor_address_for_loan = addr
                                else:
                                    echo_with_color(YELLOW, f"  ⚠️  Could not register wallet in payments: {create_result.get('error', 'Unknown')}")
                        else:
                            echo_with_color(YELLOW, f"  ⚠️  Per-loan deploy failed for loan {loan_id}: {per_loan_result.get('error', 'Unknown error')} (continuing)")
                    else:
                        echo_with_color(YELLOW, f"  ⚠️  No existing wallet {wlt_id}; deploy_per_loan disabled — obligor must be sub-account, skipping loan")
                if not obligor_wallet_id_for_loan:
                    fail_count += 1
                    continue
                if not obligor_address_for_loan:
                    obligor_wallet = get_wallet_by_id(config.pay_service_url, jwt_token, obligor_wallet_id_for_loan)
                    obligor_address_for_loan = (obligor_wallet.get("address") or "").strip() if obligor_wallet else ""
                # --- Step 3: Optional register issuer external key with loan wallet ---
                if issuer_external_key_id and obligor_address_for_loan and obligor_address_for_loan.startswith("0x"):
                    try:
                        register_key_with_specific_wallet(
                            config.auth_service_url, jwt_token, issuer_external_key_id, obligor_address_for_loan
                        )
                        echo_with_color(GREEN, f"  ✅ Issuer external key registered with loan wallet {obligor_wallet_id_for_loan}")
                    except Exception as reg_err:
                        echo_with_color(YELLOW, f"  ⚠️  Register key with loan wallet failed (continuing): {reg_err}")
                print()

                # --- Step 4: Issue workflow (issue or issue+swap) ---
                obligation_data = {"name": f"Loan {loan_id}", "description": f"Loan obligation for loan ID {loan_id}", **loan_data}
                obligation = {
                    "counterpartWalletId": obligor_wallet_id_for_loan,
                    "denomination": config.denomination,
                    "obligorWalletId": obligor_wallet_id_for_loan,
                    "notional": amount_wei,
                    "expiry": maturity_iso,
                    "data": obligation_data,
                    "initialPayments": {
                        "amount": amount_wei,
                        "denomination": config.denomination,
                        "payments": [{
                            "oracleAddress": None,
                            "oracleOwner": None,
                            "oracleKeySender": None,
                            "oracleValueSenderSecret": None,
                            "oracleKeyRecipient": None,
                            "oracleValueRecipientSecret": None,
                            "unlockSender": None, #maturity_iso,
                            "unlockReceiver": None, #maturity_iso,
                            "linearVesting": None,
                        }],
                    },
                }
                obligations_array = [obligation]
                contract_name = f"Loan Contract {loan_id}"
                contract_description = f"Composed contract for loan ID {loan_id}"

                if config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                    payment_amount = config.env_payment_amount if config.env_payment_amount else amount_wei
                    deadline = config.env_deadline if config.env_deadline else maturity_iso
                    echo_with_color(CYAN, "📤 Calling issue + swap composed contract workflow endpoint...")
                    start_response = issue_composed_contract_issue_swap_workflow(
                        config.pay_service_url,
                        jwt_token,
                        contract_name,
                        contract_description,
                        obligations_array,
                        counterparty=config.swap_counterparty,
                        payment_amount=payment_amount,
                        payment_denomination=config.payment_denomination,
                        deadline=deadline if deadline else None,
                        account_address=obligor_address_for_loan or None,
                        wallet_id=obligor_wallet_id_for_loan,
                        require_manual_signature=config.require_manual_signature,
                    )
                else:
                    echo_with_color(CYAN, "📤 Calling issue composed contract workflow endpoint...")
                    start_response = issue_composed_contract_workflow(
                        config.pay_service_url,
                        jwt_token,
                        contract_name,
                        contract_description,
                        obligations_array,
                        account_address=obligor_address_for_loan or None,
                        wallet_id=obligor_wallet_id_for_loan,
                        require_manual_signature=config.require_manual_signature,
                    )

                workflow_id = start_response.get("workflow_id") if isinstance(start_response, dict) else None
                if not workflow_id or workflow_id == "null":
                    echo_with_color(RED, f"  ❌ Failed to start workflow for loan {loan_id}")
                    if isinstance(start_response, dict):
                        echo_with_color(RED, f"    Error: {start_response.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, f"  ✅ Workflow started with ID: {workflow_id}")
                print()

                # --- Step 5: Poll workflow until completed (event-driven: stop on terminal or timeout) ---
                final_response = poll_workflow_status(
                    config.pay_service_url,
                    workflow_id,
                    timeout_sec=config.workflow_poll_timeout_sec,
                    poll_interval_sec=config.workflow_poll_interval_sec,
                )
                if not final_response:
                    echo_with_color(RED, f"  ❌ Workflow did not complete for loan {loan_id}")
                    fail_count += 1
                    continue
                workflow_status = final_response.get("workflow_status", "")
                if workflow_status == "completed":
                    echo_with_color(GREEN, f"  ✅ Loan {loan_id} contract created successfully!")
                    result = final_response.get("result") or {}
                    if config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                        swap_id_raw = result.get("swap_id") if isinstance(result, dict) else None
                        if swap_id_raw is None or swap_id_raw in ("", "pending"):
                            echo_with_color(BLUE, "    ⏳ Re-fetching workflow result for swap_id...", file=sys.stderr)
                            time.sleep(2)
                            retry_response = requests.get(f"{config.pay_service_url}/api/workflows/{workflow_id}", timeout=30)
                            if retry_response.ok:
                                try:
                                    retry_data = retry_response.json()
                                    retry_result = retry_data.get("result")
                                    if isinstance(retry_result, dict) and retry_result.get("swap_id") not in (None, "", "pending"):
                                        result = retry_result
                                        echo_with_color(GREEN, "    ✅ Got swap_id from re-fetch", file=sys.stderr)
                                except Exception:
                                    pass
                    if not isinstance(result, dict):
                        result = {}
                    contract_id = result.get("composed_contract_id", "N/A")
                    echo_with_color(BLUE, f"    Composed Contract ID: {contract_id}")
                    # Do not call accept_obligation_graphql here: issue_workflow and issue_swap_workflow
                    # already run accept_obligation + wait_for_obligation_acceptance. A second accept
                    # would fail on-chain with "idHash already exists" and the failed path never
                    # creates the payment token, so payment_workflow would then get "token not found".
                    if contract_id and contract_id != "N/A":
                        echo_with_color(BLUE, "    ℹ️  Obligation accepted by workflow (accept_obligation + wait step); payment tokens ready for payment_workflow.", file=sys.stderr)
                    # --- Step 6 & 7: Optional complete swap (acceptor) and accept_all (loan account) ---
                    if config.action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                        swap_id_val = result.get("swap_id")
                        if swap_id_val is not None:
                            swap_id_val = str(swap_id_val).strip() if swap_id_val else ""
                        else:
                            swap_id_val = ""
                        if swap_id_val == "pending":
                            swap_id_val = ""
                        swap_message_id = result.get("swap_message_id") or "N/A"
                        if swap_id_val:
                            echo_with_color(BLUE, f"    Swap ID: {swap_id_val}")
                            if swap_message_id != "N/A":
                                echo_with_color(BLUE, f"    Swap Message ID: {swap_message_id}")
                            run_accept = (config.action_mode == ACTION_ISSUE_SWAP_COMPLETE) or (config.acceptor_email and config.acceptor_password)
                            if run_accept and swap_id_val:
                                if not config.acceptor_email or not config.acceptor_password:
                                    echo_with_color(RED, "    ❌ issue_swap_complete requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD")
                                else:
                                    accept_result = complete_swap(
                                        config.pay_service_url,
                                        config.auth_service_url,
                                        config.acceptor_email,
                                        config.acceptor_password,
                                        str(swap_id_val),
                                    )
                                    if accept_result.get("success"):
                                        echo_with_color(GREEN, f"    ✅ Swap accepted by {config.acceptor_email}")
                                        if accept_result.get("messageId"):
                                            echo_with_color(BLUE, f"       Message ID: {accept_result.get('messageId')}")
                                        poll_result = poll_swap_completion(
                                            config.pay_service_url,
                                            config.auth_service_url,
                                            config.acceptor_email,
                                            config.acceptor_password,
                                            str(swap_id_val),
                                            timeout_sec=config.swap_poll_timeout_sec,
                                            poll_interval_sec=config.swap_poll_interval_sec,
                                        )
                                        if not poll_result.get("success"):
                                            echo_with_color(YELLOW, f"    ⚠️  Swap polling failed: {poll_result.get('error', 'Unknown')}")
                                        if poll_result.get("success") and obligor_wallet_id_for_loan and obligor_address_for_loan:
                                            acc_idem = f"accept-loan-{loan_id}-{int(time.time() * 1000)}"
                                            acc_res = accept_all_tokens(
                                                config.pay_service_url,
                                                config.auth_service_url,
                                                config.user_email,
                                                config.password,
                                                config.payment_denomination,
                                                acc_idem,
                                                obligor=None,
                                                wallet_id=obligor_wallet_id_for_loan,
                                                account_address=obligor_address_for_loan,
                                            )
                                            if not acc_res.get("success"):
                                                echo_with_color(YELLOW, f"    ⚠️  Accept all (loan account): {acc_res.get('error', 'Unknown')}")
                                    else:
                                        echo_with_color(RED, f"    ❌ Swap acceptance failed: {accept_result.get('error', 'Unknown error')}")
                            elif config.acceptor_email and swap_id_val and not config.acceptor_password:
                                echo_with_color(YELLOW, "    ⚠️  ACCEPTOR_EMAIL set but ACCEPTOR_PASSWORD missing; skipping swap acceptance")
                    success_count += 1
                else:
                    echo_with_color(RED, f"  ❌ Loan {loan_id} workflow ended in status: {workflow_status}")
                    error_msg = final_response.get("error", "Unknown error")
                    if error_msg:
                        echo_with_color(RED, f"    Error: {error_msg}")
                    fail_count += 1
    except Exception as e:
        echo_with_color(RED, f"❌ Error reading CSV file: {e}")
        return 1

    # --- Summary ---
    print_workflow_summary(
        loan_count,
        success_count,
        fail_count,
        total_label="Total loans processed",
        success_label="Successful",
        fail_label="Failed",
        success_message=f"🎉 Successfully created {success_count} composed contract(s)! ✨" if success_count > 0 else None,
        failure_message="❌ No contracts were created successfully",
    )
    if config.burn_after_env and config.policy_secret and config.burn_amount:
        print()
        echo_with_color(CYAN, "🔥 Burning tokens after loan processing...")
        burn_res = burn_tokens(
            config.pay_service_url, config.auth_service_url, config.user_email, config.password,
            config.denomination, config.burn_amount, config.policy_secret,
        )
        if not burn_res.get("success"):
            echo_with_color(RED, f"❌ Burn failed: {burn_res.get('error', 'Unknown error')}")
            if success_count > 0:
                echo_with_color(YELLOW, "  (Loans were created successfully; only burn failed)")
        print()
    elif config.burn_after_env and (not config.policy_secret or not config.burn_amount):
        echo_with_color(YELLOW, "  ⚠️  BURN_AFTER_LOANS=true but POLICY_SECRET or BURN_AMOUNT missing; skipping burn")
    if listener_thread is not None:
        listener_stop.set()
    return 0 if success_count > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
