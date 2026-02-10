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
  the obligor's address and wallet_id.

This script is a thin entry point; reusable logic lives in the modules package.
"""

import csv
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' library is required. Install it with: pip install requests")
    sys.exit(1)

# Reusable modules
from modules import (
    ACTION_ISSUE_SWAP,
    ACTION_ISSUE_SWAP_COMPLETE,
    accept_all_tokens,
    safe_get,
    accept_obligation_graphql,
    burn_tokens,
    check_service_running,
    complete_swap,
    convert_currency_to_wei,
    convert_date_to_iso,
    create_wallet_in_payments,
    deploy_issuer_account,
    deploy_user_account,
    deposit_tokens,
    echo_with_color,
    extract_loan_data,
    get_user_id_from_profile,
    get_wallet_by_id,
    issue_composed_contract_issue_swap_workflow,
    issue_composed_contract_workflow,
    load_env_files,
    login_user,
    mint_tokens,
    parse_bool_env,
    parse_bool_env_with_mode_default,
    parse_cli_args,
    poll_swap_completion,
    poll_workflow_status,
    print_usage,
)
from modules.console import BLUE, CYAN, GREEN, PURPLE, RED, YELLOW

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

    # --- Configuration ---
    pay_service_url = os.environ.get("PAY_SERVICE_URL", "https://pay.yieldfabric.com")
    auth_service_url = os.environ.get("AUTH_SERVICE_URL", "https://auth.yieldfabric.com")
    denomination = os.environ.get("DENOMINATION", "aud-token-asset")
    counterpart = os.environ.get("COUNTERPART", "issuer@yieldfabric.com")
    swap_counterparty = os.environ.get("SWAP_COUNTERPARTY", "originator@yieldfabric.com")
    payment_denomination = os.environ.get("PAYMENT_DENOMINATION", denomination)
    env_payment_amount = os.environ.get("PAYMENT_AMOUNT", "")
    env_deadline = os.environ.get("DEADLINE", "")
    acceptor_email = os.environ.get("ACCEPTOR_EMAIL", "").strip()
    acceptor_password = os.environ.get("ACCEPTOR_PASSWORD", "").strip()
    try:
        max_loans = int(os.environ.get("LOAN_COUNT", "10").strip())
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
    deploy_issuer = parse_bool_env("DEPLOY_ISSUER_ACCOUNT") or parse_bool_env_with_mode_default(
        "DEPLOY_ISSUER_ACCOUNT", action_mode, default_for_swap_complete=True
    )
    deploy_acceptor = (
        parse_bool_env("DEPLOY_ACCEPTOR_ACCOUNT")
        or parse_bool_env_with_mode_default("DEPLOY_ACCEPTOR_ACCOUNT", action_mode, default_for_swap_complete=True)
    ) and bool(acceptor_email and acceptor_password)
    deploy_per_loan = parse_bool_env("DEPLOY_ACCOUNT_PER_LOAN") or (
        action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE)
        and os.environ.get("DEPLOY_ACCOUNT_PER_LOAN", "").strip().lower() not in ("false", "0", "no")
    )
    if deploy_issuer:
        echo_with_color(CYAN, "  Deploy issuer account: yes (before workflows)" + (" [default for issue_swap_complete]" if not parse_bool_env("DEPLOY_ISSUER_ACCOUNT") else ""))
    if deploy_acceptor:
        echo_with_color(CYAN, "  Deploy acceptor account: yes (before workflows)" + (" [default for issue_swap_complete]" if not parse_bool_env("DEPLOY_ACCEPTOR_ACCOUNT") else ""))
    if deploy_per_loan:
        echo_with_color(CYAN, "  Deploy one wallet per loan under issuer entity: yes" + (" [default for issue_swap/issue_swap_complete]" if not parse_bool_env("DEPLOY_ACCOUNT_PER_LOAN") else ""))
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
        echo_with_color(BLUE, f"  Acceptor (will complete swap): {acceptor_email}" if acceptor_email else "  Acceptor: (none - swap will remain pending)")
    mint_before_env = parse_bool_env("MINT_BEFORE_LOANS")
    burn_after_env = parse_bool_env("BURN_AFTER_LOANS")
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
    try:
        response = requests.post(
            f"{pay_service_url.rstrip('/')}/api/composed_contract/issue_workflow",
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

    # --- Auth & deploy ---
    echo_with_color(CYAN, "🔐 Authenticating...")
    jwt_token = login_user(auth_service_url, user_email, password)
    if not jwt_token:
        echo_with_color(RED, f"❌ Failed to get JWT token for user: {user_email}")
        return 1
    echo_with_color(GREEN, f"  ✅ JWT token obtained (first 50 chars): {jwt_token[:50]}...")
    print()

    if deploy_issuer:
        deploy_result = deploy_issuer_account(auth_service_url, user_email, password)
        if deploy_result.get("success"):
            addr = deploy_result.get("new_account_address") or "N/A"
            echo_with_color(GREEN, f"  ✅ Issuer account deployed: {addr}")
        else:
            echo_with_color(RED, f"  ❌ Issuer account deployment failed: {deploy_result.get('error', 'Unknown error')}")
            return 1
        print()

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

    issuer_user_id = get_user_id_from_profile(auth_service_url, jwt_token)
    issuer_entity_id_raw = (issuer_user_id or "").replace("ENTITY-USER-", "").replace("ENTITY-GROUP-", "").strip()

    # Optional: ensure issuer has an external key (create + save to file + register on first run)
    # key_id is used later to register this key with each loan wallet
    issuer_external_key_id = None
    ensure_issuer_key = parse_bool_env("ENSURE_ISSUER_EXTERNAL_KEY")
    if ensure_issuer_key and issuer_user_id:
        if _HAS_ENSURE_ISSUER_KEY:
            key_file = os.environ.get("ISSUER_EXTERNAL_KEY_FILE", "").strip() or str(script_dir / "issuer_external_key.txt")
            key_path = Path(key_file) if Path(key_file).is_absolute() else (script_dir / key_file).resolve()
            echo_with_color(CYAN, "🔑 Ensuring issuer external key (create + register if first time)...")
            try:
                # Register key with loan wallets only (not the issuer's default account)
                _addr, _pk, _kp, issuer_external_key_id = ensure_issuer_external_key(
                    auth_service_url=auth_service_url,
                    jwt_token=jwt_token,
                    user_id=issuer_user_id,
                    key_file_path=key_path,
                    key_name=os.environ.get("ISSUER_EXTERNAL_KEY_NAME", "Issuer script external key").strip(),
                    register_with_wallet=False,  # loan accounts only; set REGISTER_WITH_WALLET=true to also add to default account
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
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)
            for row in reader:
                if loan_count >= max_loans:
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
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
                echo_with_color(CYAN, f"📦 Processing Loan {loan_count}/{max_loans}: ID={loan_id}")
                echo_with_color(PURPLE, "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
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

                if mint_before_env and policy_secret and action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                    if not acceptor_email or not acceptor_password:
                        echo_with_color(RED, "  ❌ MINT_BEFORE_LOANS requires ACCEPTOR_EMAIL and ACCEPTOR_PASSWORD (mint runs as investor)")
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
                                    echo_with_color(YELLOW, f"  ⚠️  Could not register wallet in payments: {create_result.get('error', 'Unknown')}")
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
                # Register issuer external key with this loan wallet so the key can sign for the loan
                if issuer_external_key_id and obligor_address_for_loan and obligor_address_for_loan.startswith("0x"):
                    try:
                        register_key_with_specific_wallet(
                            auth_service_url, jwt_token, issuer_external_key_id, obligor_address_for_loan
                        )
                        echo_with_color(GREEN, f"  ✅ Issuer external key registered with loan wallet {obligor_wallet_id_for_loan}")
                    except Exception as reg_err:
                        echo_with_color(YELLOW, f"  ⚠️  Register key with loan wallet failed (continuing): {reg_err}")
                print()

                obligation_data = {"name": f"Loan {loan_id}", "description": f"Loan obligation for loan ID {loan_id}", **loan_data}
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
                            "linearVesting": None,
                        }],
                    },
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

                workflow_id = start_response.get("workflow_id") if isinstance(start_response, dict) else None
                if not workflow_id or workflow_id == "null":
                    echo_with_color(RED, f"  ❌ Failed to start workflow for loan {loan_id}")
                    if isinstance(start_response, dict):
                        echo_with_color(RED, f"    Error: {start_response.get('error', 'Unknown error')}")
                    fail_count += 1
                    continue
                echo_with_color(GREEN, f"  ✅ Workflow started with ID: {workflow_id}")
                print()

                final_response = poll_workflow_status(pay_service_url, workflow_id)
                if not final_response:
                    echo_with_color(RED, f"  ❌ Workflow did not complete for loan {loan_id}")
                    fail_count += 1
                    continue
                workflow_status = final_response.get("workflow_status", "")
                if workflow_status == "completed":
                    echo_with_color(GREEN, f"  ✅ Loan {loan_id} contract created successfully!")
                    result = final_response.get("result") or {}
                    if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
                        swap_id_raw = result.get("swap_id") if isinstance(result, dict) else None
                        if swap_id_raw is None or swap_id_raw in ("", "pending"):
                            echo_with_color(BLUE, "    ⏳ Re-fetching workflow result for swap_id...", file=sys.stderr)
                            time.sleep(2)
                            retry_response = requests.get(f"{pay_service_url}/api/workflows/{workflow_id}", timeout=30)
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
                    if contract_id and contract_id != "N/A" and obligor_wallet_id_for_loan:
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
                    elif contract_id and contract_id != "N/A" and not obligor_wallet_id_for_loan:
                        echo_with_color(YELLOW, "    ⚠️  Skipping accept: no obligor wallet id", file=sys.stderr)
                    if action_mode in (ACTION_ISSUE_SWAP, ACTION_ISSUE_SWAP_COMPLETE):
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
                                        poll_result = poll_swap_completion(
                                            pay_service_url,
                                            auth_service_url,
                                            acceptor_email,
                                            acceptor_password,
                                            str(swap_id_val),
                                        )
                                        if not poll_result.get("success"):
                                            echo_with_color(YELLOW, f"    ⚠️  Swap polling failed: {poll_result.get('error', 'Unknown')}")
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
                    error_msg = final_response.get("error", "Unknown error")
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
    echo_with_color(RED, "❌ No contracts were created successfully")
    return 1


if __name__ == "__main__":
    sys.exit(main())
