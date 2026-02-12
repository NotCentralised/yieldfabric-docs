# Wisr Loan Issue Workflow Scripts

Scripts for processing loans from a CSV file and creating composed contracts with obligations and swaps in YieldFabric. Supports the full flow: issue, swap, and completion with mint/deposit and accept.

## Module layout (reusability)

Reusable logic lives in the **`wisr`** package so other scripts or tools can import it without duplicating code.

| Module | Purpose |
|--------|--------|
| `wisr/console.py` | Colored terminal output (`echo_with_color`, color constants). |
| `wisr/http_client.py` | GraphQL/REST helpers: `auth_headers`, `post_graphql`, `post_workflow_json`, `graphql_errors_message`. |
| `wisr/config.py` | Action modes, `load_env_files`, `parse_bool_env`, `parse_bool_env_with_mode_default`. |
| `wisr/auth.py` | Auth service: `login_user`, `get_user_id_from_profile`, `deploy_user_account`, `deploy_issuer_account`, `check_service_running`. |
| `wisr/payments.py` | Payments API: wallets, issue/accept workflows, swap, mint/burn/deposit, `poll_workflow_status`, etc. |
| `wisr/loan_csv.py` | CSV/loan parsing: `convert_currency_to_wei`, `convert_date_to_iso`, `safe_get`, `extract_loan_data`. |
| `wisr/cli.py` | CLI: `print_usage`, `parse_cli_args`. |
| `wisr/register_external_key.py` | External key registration: generate Ethereum key, sign ownership message, register via `/keys/external`. |
| `wisr/messages.py` | Messages API: `get_message`, `get_messages_awaiting_signature`, `wait_for_message_completion` (link Python to manual signing). |
| `wisr/wallet_preferences.py` | Wallet execution mode: `set_wallet_execution_mode_preference`, `get_wallet_execution_mode_preferences` (Manual vs Automatic per message type). |

**Entry point:** `issue_workflow.py` is a thin script that imports from `wisr` and runs the main loan-processing loop.

**Example – use in another script:**

```python
from wisr import load_env_files, login_user, issue_composed_contract_workflow
from wisr.loan_csv import extract_loan_data, convert_currency_to_wei
from pathlib import Path
# ...
```

Run the script from the `wisr` directory so the package is found: `python3 issue_workflow.py [options]`.

## Overview

The `issue_workflow.py` script processes loans from a CSV and creates composed contracts. In `issue_swap_complete` mode, it orchestrates the full lifecycle: minting tokens as the investor, issuing the obligation as the issuer (loan sub-account), accepting the obligation, completing the swap as the investor, polling for swap completion, and accepting resulting payables as the loan account.

## Workflow Steps (issue_swap_complete)

| Step | Account | Operation |
|------|---------|-----------|
| 1 | issuer | Authenticate (login) |
| 2 | issuer | Deploy issuer on-chain account |
| 3 | acceptor (investor) | Deploy acceptor on-chain account |
| 4 | acceptor (investor) | Mint tokens (per loan, when `MINT_BEFORE_LOANS`) |
| 5 | acceptor (investor) | Deposit tokens (per loan, after mint) |
| 6 | issuer | Create/ensure loan wallet `WLT-LOAN-{entity}-{loan_id}` |
| 7 | issuer | Call issue + swap workflow (as obligor sub-account) |
| 8 | — | Poll workflow until completed |
| 9 | issuer (loan sub-account) | Accept obligation (X-Account-Address, X-Wallet-Id = loan wallet) |
| 10 | acceptor (investor) | Complete swap (counterparty accepts swap) |
| 11 | acceptor (investor) | Poll swap until status = COMPLETED |
| 12 | issuer (loan sub-account) | Accept all payables (X-Account-Address, X-Wallet-Id = loan wallet) |
| 13 | issuer | Burn tokens (when `BURN_AFTER_LOANS`) |

## Process Explanation

### Roles

- **Issuer** (`ISSUER_EMAIL`): The originator/lender entity. Creates the obligation and acts as obligor. Uses a **loan sub-account** per loan (`WLT-LOAN-{entity_id}-{loan_id}`) so each loan has its own wallet.
- **Investor** (`ACCEPTOR_EMAIL`): The counterparty who mints, deposits, completes the swap, and receives the obligation. Also called the "acceptor" because they accept/complete the swap.

### Flow Summary

1. **Setup (once per run)**  
   Issuer and investor authenticate. Their on-chain accounts are deployed if `DEPLOY_ISSUER_ACCOUNT` / `DEPLOY_ACCEPTOR_ACCOUNT` are set.

2. **Per loan**  
   - **Mint & deposit**: Investor mints the loan amount and deposits it (when `MINT_BEFORE_LOANS=true`).  
   - **Loan wallet**: A dedicated wallet `WLT-LOAN-{entity_id}-{loan_id}` is used or created for this loan.  
   - **Issue + swap**: Issuer calls the composed contract issue + swap workflow as the obligor sub-account. The workflow creates the obligation and swap.  
   - **Accept obligation**: The same loan sub-account accepts the obligation (obligor accepts).  
   - **Complete swap**: Investor completes the swap as counterparty.  
   - **Poll swap**: Script polls swap status until `COMPLETED` to avoid race conditions.  
   - **Accept payables**: The loan sub-account accepts all resulting payables (e.g. from the swap).

3. **Post-processing**  
   If `BURN_AFTER_LOANS=true`, the issuer burns the specified amount.

### Why Poll for Swap Completion?

`completeSwap` is asynchronous: the mutation returns before the swap processor has finished. Payments are created only after the swap is marked `COMPLETED`. Without polling, `accept_all` can run too early and see 0 payables. The script polls `swapFlow.coreSwaps.byId(id)` until status is `COMPLETED` before calling `accept_all`.

### Loan Sub-Account

Each loan uses a sub-account wallet (`WLT-LOAN-{entity_id}-{loan_id}`). Obligations are issued and accepted as this sub-account, not the main issuer wallet. This keeps exposure per loan isolated. The `X-Account-Address` and `X-Wallet-Id` headers identify the loan sub-account when accepting obligations and payables.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ISSUER_EMAIL` / `USER_EMAIL` | Issuer (lender) email | `issuer@yieldfabric.com` |
| `ISSUER_PASSWORD` / `PASSWORD` | Issuer password | — |
| `ACCEPTOR_EMAIL` | Investor (swap counterparty) email | — |
| `ACCEPTOR_PASSWORD` | Investor password | — |
| `PAY_SERVICE_URL` | Payments service URL | `https://pay.yieldfabric.com` |
| `AUTH_SERVICE_URL` | Auth service URL | `https://auth.yieldfabric.com` |
| `ACTION_MODE` | `issue_only` \| `issue_swap` \| `issue_swap_complete` | `issue_only` |
| `SWAP_COUNTERPARTY` | Swap counterparty email | `originator@yieldfabric.com` |
| `LOAN_COUNT` | Max loans to process | `10` |
| `MINT_BEFORE_LOANS` | Mint as investor per loan | `false` |
| `BURN_AFTER_LOANS` | Burn after processing | `false` |
| `POLICY_SECRET` | Required for mint/burn | — |
| `DEPLOY_ISSUER_ACCOUNT` | Deploy issuer wallet | `true` for issue_swap_complete |
| `DEPLOY_ACCEPTOR_ACCOUNT` | Deploy investor wallet | `true` for issue_swap_complete |
| `DEPLOY_ACCOUNT_PER_LOAN` | One wallet per loan | `true` for issue_swap |
| `ENSURE_ISSUER_EXTERNAL_KEY` | In issue_workflow: create/load issuer external key from file before loans | `false` |
| `ISSUER_EXTERNAL_KEY_FILE` | Path to issuer private key file (create if missing) | `issuer_external_key.txt` (in wisr dir) |
| `ISSUER_EXTERNAL_KEY_NAME` | Display name for the issuer external key | `Issuer script external key` |

## Run locally (self-contained pip / venv)

From the `wisr` folder, use the included runner so all dependencies (including `eth-account`) are installed in a local `.venv`:

```bash
cd yieldfabric-docs/scripts/wisr
./run.sh
```

This creates `.venv` if needed, runs `pip install -r requirements.txt`, and executes `issue_workflow.py`. To run another script:

```bash
./run.sh ensure_issuer_key.py
./run.sh register_external_key_cli.py --key-name "My key"
```

Manual venv setup (optional):

```bash
cd yieldfabric-docs/scripts/wisr
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python issue_workflow.py
```

## Usage

```bash
# Run with defaults (reads .env) — use ./run.sh for self-contained deps
python3 issue_workflow.py

# Full flow with swap completion (investor completes each swap)
ACTION_MODE=issue_swap_complete ACCEPTOR_EMAIL=investor@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py

# Mint before each loan (investor mints and deposits)
MINT_BEFORE_LOANS=true POLICY_SECRET=xxx ACTION_MODE=issue_swap_complete ACCEPTOR_EMAIL=investor@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py

# Local development
PAY_SERVICE_URL=http://localhost:3002 AUTH_SERVICE_URL=http://localhost:3000 python3 issue_workflow.py
```

## Payment workflow (payment_workflow.py)

`payment_workflow.py` processes a **payment CSV** (e.g. `wisr_payment_test.csv`) and, per row:

1. **ACCEPTOR_EMAIL** accepts payment for **DWH_PRINCIPAL** (linked to the loan).
2. **ACCEPTOR_EMAIL** creates a payment swap: initiator = acceptor (DWH_PRINCIPAL, obligor = loan wallet), counterparty = loan wallet (MAMBU_TOTAL_AMOUNT, obligor = null).
3. **Loan wallet** (via issuer JWT + wallet context) completes the swap.

Requires **ISSUER_EMAIL** / **ISSUER_PASSWORD** when loan wallets were created by `issue_workflow` (so the script can resolve `WLT-LOAN-{issuer_entity}-{loan_id}` and complete the swap as that wallet).

```bash
./run_payment.sh
# or with CSV
./run_payment.sh wisr_payment_test.csv
```

Step 1 uses the **single-payment accept** mutation (`accept(input: { paymentId })`), not `acceptAll`. The script resolves the obligation initial payment by querying payments by loan wallet, then calls `accept` for that `payment_id`. If no PENDING/PROCESSING obligation initial payment is found for the loan wallet, Step 1 fails with a clear message.

(Backend note: if the backend reports "Token ... not found" when accepting, the obligation initial payment token may not have been created yet by accept_obligation_processor.)


## Files

| File | Description |
|------|-------------|
| `issue_workflow.py` | Main script: issue, swap, complete, accept |
| `payment_workflow.py` | Payment CSV flow: accept payment, create payment swap, complete as loan wallet |
| `issue_workflow_fire_and_forget.py` | Fire-and-forget variant (no polling) |
| `issue_workflow.sh` | Bash wrapper for the workflow |
| `run_payment.sh` | Run payment_workflow.py with .venv (optional CSV path) |
| `register_external_key_cli.py` | Generate an Ethereum key and register it as an external key (see below) |
| `ensure_issuer_key.py` | Ensure issuer has an external key: create + save to file + register on first run (see below) |
| `manual_signature_flow.py` | Set wallet to Manual (so messages require app signing), poll for message completion, list awaiting (see [LINKING_PYTHON_TO_MANUAL_SIGNATURE.md](docs/LINKING_PYTHON_TO_MANUAL_SIGNATURE.md)) |
| `requirements.txt` | Python deps: `requests`, `eth-account` (for key generation/signing) |
| `.env` | Local environment overrides (loads from wisr/, repo root, .env.local) |

### Ensure issuer external key (create once, register to issuer)

Use this flow so a **private key is created and saved in a .txt file if it doesn't exist**; **on first run** that key is **registered to the issuer account**.

```bash
# From the wisr directory; uses ISSUER_EMAIL / ISSUER_PASSWORD from .env
python3 ensure_issuer_key.py
```

- **First run:** Key file (default `./issuer_external_key.txt`) does not exist → script generates a key, saves it to the file, and registers it as an external key for the issuer.
- **Later runs:** Key file exists → script loads the key and reports the address; no registration.

Optional env: `ISSUER_EXTERNAL_KEY_FILE` (path to key file), `ISSUER_EXTERNAL_KEY_NAME`, `REGISTER_WITH_WALLET`.

You can also run this step from the main issue workflow by setting `ENSURE_ISSUER_EXTERNAL_KEY=true`; the workflow will ensure the issuer key exists (using `ISSUER_EXTERNAL_KEY_FILE`, default `issuer_external_key.txt`) before processing loans. The key is registered **only with each loan account** (not the issuer’s default account), via `POST /keys/register-with-specific-wallet` and the loan wallet address, so the key can sign for that loan’s sub-account.

### Manual signature flow (Python ↔ app)

To have Python trigger an operation (e.g. accept obligation) and have the **user sign in the app** before execution completes:

1. Set the wallet to **Manual** for that message type:  
   `./run.sh manual_signature_flow.py set-manual --wallet-id WLT-LOAN-<entity>-<loan> --message-type AcceptObligation`
2. Run your workflow from Python (e.g. `accept_obligation_graphql`); the message will appear in the app for signing.
3. User signs in the app (SignaturePreviewDrawer).
4. Optionally poll from Python:  
   `./run.sh manual_signature_flow.py wait --message-id <uuid>`  
   Or use `wait_for_message_completion` from `modules.messages`.

See [docs/LINKING_PYTHON_TO_MANUAL_SIGNATURE.md](docs/LINKING_PYTHON_TO_MANUAL_SIGNATURE.md) and the `modules.messages` / `modules.wallet_preferences` APIs.

### Register external key (script-generated key)

To generate a new Ethereum key and register it as an external key for a user (same flow as the app’s “Register MetaMask Key”):

```bash
# Install deps (optional; issue_workflow only needs requests)
pip install -r requirements.txt

# From the wisr directory; uses USER_EMAIL / USER_PASSWORD or ISSUER_EMAIL / ISSUER_PASSWORD from .env
python3 register_external_key_cli.py

# With options
python3 register_external_key_cli.py --key-name "My script key" --register-with-wallet --save-key ./my-key.txt
```
