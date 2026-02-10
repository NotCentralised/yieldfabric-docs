# Wisr Loan Issue Workflow Scripts

Scripts for processing loans from a CSV file and creating composed contracts with obligations and swaps in YieldFabric. Supports the full flow: issue, swap, and completion with mint/deposit and accept.

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

## Usage

```bash
# Run with defaults (reads .env)
python3 issue_workflow.py

# Full flow with swap completion (investor completes each swap)
ACTION_MODE=issue_swap_complete ACCEPTOR_EMAIL=investor@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py

# Mint before each loan (investor mints and deposits)
MINT_BEFORE_LOANS=true POLICY_SECRET=xxx ACTION_MODE=issue_swap_complete ACCEPTOR_EMAIL=investor@yieldfabric.com ACCEPTOR_PASSWORD=secret python3 issue_workflow.py

# Local development
PAY_SERVICE_URL=http://localhost:3002 AUTH_SERVICE_URL=http://localhost:3000 python3 issue_workflow.py
```

## Files

| File | Description |
|------|-------------|
| `issue_workflow.py` | Main script: issue, swap, complete, accept |
| `issue_workflow_fire_and_forget.py` | Fire-and-forget variant (no polling) |
| `issue_workflow.sh` | Bash wrapper for the workflow |
| `.env` | Local environment overrides (loads from wisr/, repo root, .env.local) |
