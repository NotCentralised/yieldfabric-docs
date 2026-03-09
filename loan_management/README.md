# Wisr Loan Issue Workflow Scripts

Scripts for processing loans from a CSV file and creating composed contracts with obligations and swaps in YieldFabric. Supports the full flow: issue, swap, and completion with mint/deposit and accept.

## What is this?

These scripts automate the **onboarding of loans** and **processing of payments** into YieldFabric, a platform for tokenised real-world assets. In practice:

1. **Issue workflow** — Reads a loans CSV (e.g. from Wisr), creates composed contracts (obligations), optionally mints tokens, and sets up swaps so an investor can fund the loans.
2. **Payment workflow** — Reads a payments CSV (e.g. principal/interest payments), finds the corresponding obligation, accepts the payment, creates a payment swap, and settles it against the loan wallet.

**Order of operations:** Run the issue workflow first to create the loans and swap structure. Then run the payment workflow when you have payment data to settle against those loans.

**Prerequisites:**
- Auth and Payments services running (locally or hosted)
- User accounts (issuer, investor) registered in the auth service
- CSV files with loan and payment data in the expected formats (see below)

**First run: private key creation and registration**

When you run `ensure_issuer_key.py` or use `ENSURE_ISSUER_EXTERNAL_KEY=true` (or `REQUIRE_MANUAL_SIGNATURE=true` in the payment workflow), the scripts will **create a new Ethereum private key and register it** on first run:

1. **First run:** If the key file (default `issuer_external_key.txt`) does not exist, a new private key is generated, saved to that file, and registered as an external key for the issuer in YieldFabric. This key is used to sign operations (e.g. completing swaps) on behalf of the issuer.
2. **Later runs:** If the key file already exists, the script loads the existing key and does not create or register a new one.

Keep the key file secure and back it up; it cannot be recovered if lost. See the [Ensure issuer external key](#ensure-issuer-external-key-create-once-register-to-issuer) section for details.

**Quick start (local):**
```bash
cd yieldfabric-docs/loan_management
# Edit .env and set ISSUER_EMAIL, ISSUER_PASSWORD, LOANS_CSV, PAYMENT_CSV, etc.
./run.sh                    # Run issue workflow (reads LOANS_CSV from .env)
./run_payment.sh            # Run payment workflow (reads PAYMENT_CSV from .env)
```

## Entry points and script flow

Two shell runners bootstrap Python and pass through arguments:

| Script | Default | What it runs | CSV handling |
|--------|---------|--------------|--------------|
| `run.sh` | `issue_workflow.py` | Any script (first arg = script name, rest = args) | Pass CSV: `./run.sh issue_workflow.py wisr_loans_20250831.csv` |
| `run_payment.sh` | `payment_workflow.py` | Payment workflow only | Optional: `./run_payment.sh wisr_payment_test.csv`; else uses `PAYMENT_CSV` from `.env` |

**Flow: `run.sh` → issue_workflow.py**

1. `run.sh` creates `.venv` if needed, runs `pip install -r requirements.txt`
2. Runs `python issue_workflow.py [args...]` (or `./run.sh payment_workflow.py [args...]` for payment)
3. Python: `main()` → `load_env_files(script_dir, repo_root)` (reads `.env` from repo root and `loan_management/`)
4. Python: `parse_cli_args(script_dir)` → `csv_file` from: CLI arg, or `LOANS_CSV` env, or default `wisr_loans_20250831.csv`
5. Python: `IssueWorkflowConfig.from_env(script_dir, csv_file, ...)` → config
6. Python: preflight → `issue_auth_context(config)` → process each loan row

**Flow: `run_payment.sh` → payment_workflow.py**

1. `run_payment.sh` same venv setup
2. If you pass a CSV: runs `python payment_workflow.py <csv>`. Else: runs `python payment_workflow.py` (no args)
3. Python: `main()` → `load_env_files(script_dir, repo_root)`
4. Python: `parse_payment_cli_args(script_dir)` → `csv_file` from: CLI arg (if given), or `PAYMENT_CSV` env, or default `wisr_payment_test.csv`
5. Python: `PaymentWorkflowConfig.from_env(script_dir, csv_file)` → config
6. Python: preflight → `payment_auth_context(config)` → process each payment row

Use `LOANS_CSV` and `PAYMENT_CSV` in `.env` to set default CSV paths when no path is passed.

## Overview

The `issue_workflow.py` script processes loans from a CSV and creates composed contracts. In `issue_swap_complete` mode, it orchestrates the full lifecycle: minting tokens as the investor, issuing the obligation as the issuer (loan sub-account), accepting the obligation, completing the swap as the investor, polling for swap completion, and accepting resulting payables as the loan account.

**Action modes (ACTION_MODE):**
- `issue_only` — Create the obligation only (no swap). Use when you want to issue contracts without an investor completing them yet.
- `issue_swap` — Create obligation and swap. The swap counterparty (SWAP_COUNTERPARTY) can accept/complete later.
- `issue_swap_complete` — Create obligation, create swap, then have the investor (ACCEPTOR_EMAIL) complete each swap in the same run. Full automated flow from CSV to settled loans.

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

- **Issuer** (`ISSUER_EMAIL`): The originator/lender entity. Creates the obligation (the promise to pay) and acts as obligor. Uses a **loan sub-account** per loan (`WLT-LOAN-{entity_id}-{loan_id}`) so each loan has its own wallet.
- **Investor** (`ACCEPTOR_EMAIL`): The counterparty who provides funding. They mint tokens, deposit them, and complete the swap to receive the obligation. Also called the "acceptor" because they accept/complete the swap.

**Terminology:**
- **Obligation** — A contract representing a promise to pay (e.g. principal + interest) by a certain date. Created per loan.
- **Swap** — An agreement to exchange assets. Here: investor gives tokens (funding) and receives the obligation (exposure to the loan).

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

### CSV formats

**Loans CSV** (e.g. `wisr_loans_20250831.csv`): Expects columns such as loan ID, principal outstanding, maturity date, currency. The script maps these into obligation amounts and due dates. The exact column names are defined in `modules/loan_csv.py` (`extract_loan_data`).

**Payments CSV** (e.g. `wisr_payment_test.csv`): Expects columns `MAMBU_LOANID`, `MAMBU_PAYMENTDATE`, `MAMBU_TRANSACTION`, `DWH_PRINCIPAL`, `DWH_INTEREST`, `DWH_FEE`, `MAMBU_TOTAL_AMOUNT`, `MAMBU_ISDISHONOURED`. Each row represents a payment against a loan; the script looks up the loan’s obligation and processes that payment.

## Run locally (self-contained pip / venv)

The shell runners (`run.sh`, `run_payment.sh`) create a local `.venv` and install dependencies so you don’t need to manage a global Python environment. They also ensure the correct working directory and pass arguments through to the Python scripts.

From the `loan_management` folder:

```bash
cd yieldfabric-docs/loan_management
./run.sh                    # runs issue_workflow.py by default
./run_payment.sh            # runs payment_workflow.py (uses PAYMENT_CSV from .env or default)
```

`run.sh` creates `.venv` if needed, runs `pip install -r requirements.txt`, and executes the first arg or `issue_workflow.py`. Use it to run any script in this dir:

```bash
./run.sh payment_workflow.py              # same as ./run_payment.sh
./run.sh issue_workflow.py wisr_loans_20250831.csv
./run.sh ensure_issuer_key.py
./run.sh register_external_key_cli.py --key-name "My key"
```

Manual venv setup (optional):

```bash
cd yieldfabric-docs/loan_management
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

After loans have been issued (via `issue_workflow.py`), the payment workflow settles **principal and interest payments** against those loans. It reads a **payment CSV** (e.g. `wisr_payment_test.csv`) and, per row:

| Step | Account | Operation |
|------|---------|-----------|
| 1 | acceptor | Resolve loan wallet `WLT-LOAN-{entity}-{loan_id}` |
| 2 | acceptor | Find obligation initial payment for the loan |
| 3 | acceptor | Accept payment for **DWH_PRINCIPAL** (single-payment accept, not acceptAll) |
| 4 | acceptor | Create payment swap: credit DWH_PRINCIPAL (obligor = loan wallet) vs cash MAMBU_TOTAL_AMOUNT (obligor = null), counterparty = loan wallet |
| 5 | loan wallet (issuer) | Complete swap (via issuer JWT + X-Wallet-Id = loan wallet) |
| 6 | acceptor, loan wallet | Accept all payables by acceptor, then by loan wallet |

Requires **ISSUER_EMAIL** / **ISSUER_PASSWORD** when loan wallets were created by `issue_workflow` (so the script can resolve `WLT-LOAN-{issuer_entity}-{loan_id}` and complete the swap as that wallet).

```bash
./run_payment.sh
# or with CSV
./run_payment.sh wisr_payment_test.csv
```

Step 3 uses the **single-payment accept** mutation (`accept(input: { paymentId })`), not `acceptAll`. The script resolves the obligation initial payment by querying payments by loan wallet, then calls `accept` for that `payment_id`. If no PENDING/PROCESSING obligation initial payment is found for the loan wallet, that step fails with a clear message.

(Backend note: if the backend reports "Token ... not found" when accepting, the obligation initial payment token may not have been created yet by accept_obligation_processor.)


## Files

| File | Description |
|------|-------------|
| `issue_workflow.py` | Main script: issue, swap, complete, accept |
| `payment_workflow.py` | Payment CSV flow: accept payment, create payment swap, complete as loan wallet |
| `issue_workflow_fire_and_forget.py` | Fire-and-forget variant (no polling) |
| `run.sh` | Generic runner: creates .venv, installs deps, runs any script (default: issue_workflow.py) |
| `run_payment.sh` | Payment-specific runner: runs payment_workflow.py; optional CSV arg or PAYMENT_CSV from .env |
| `issue_workflow.sh` | Bash-native issue workflow (alternative to Python, uses same .env) |
| `register_external_key_cli.py` | Generate an Ethereum key and register it as an external key (see below) |
| `ensure_issuer_key.py` | Ensure issuer has an external key: create + save to file + register on first run (see below) |
| `manual_signature_flow.py` | Set wallet to Manual (so messages require app signing), poll for message completion, list awaiting (see [LINKING_PYTHON_TO_MANUAL_SIGNATURE.md](docs/LINKING_PYTHON_TO_MANUAL_SIGNATURE.md)) |
| `requirements.txt` | Python deps: `requests`, `eth-account` (for key generation/signing) |
| `.env` | Local environment overrides (loads from loan_management/, repo root, .env.local) |

### Ensure issuer external key (create once, register to issuer)

Use this flow so a **private key is created and saved in a .txt file if it doesn't exist**; **on first run** that key is **registered to the issuer account**.

```bash
# From the loan_management directory; uses ISSUER_EMAIL / ISSUER_PASSWORD from .env
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

# From the loan_management directory; uses USER_EMAIL / USER_PASSWORD or ISSUER_EMAIL / ISSUER_PASSWORD from .env
python3 register_external_key_cli.py

# With options
python3 register_external_key_cli.py --key-name "My script key" --register-with-wallet --save-key ./my-key.txt
```
