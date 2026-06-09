# YieldFabric Swap / Repo Test Suites

Functional test suites that drive the **live** runtime (Rust services + circom proofs +
Solidity contracts) through the Python harness, exercising the confidential
**swap / repo / rehypothecation** system end-to-end. Each suite is a YAML list of
commands run in order against a fresh deploy.

> **Status of this doc:** living catalog written while the suites were being authored.
> It is the source material for the eventual dev-site docs + tutorials. Code is the
> truth; if a suite and this file disagree, trust the suite header.

---

## Quick start

```bash
# from yieldfabric-docs/python  (or wherever `yieldfabric` is installed)
yieldfabric execute ../scripts/<suite>.yaml
# or:  python -m yieldfabric.cli execute ../scripts/<suite>.yaml
# add --debug for verbose dispatch
```

**Prerequisites (every suite):**

1. A **fresh deploy** of the contracts (`yieldfabric-smart-contracts/scripts/deploy_clean.ts`).
   The deploy seeds public ERC-20 to exactly three users: **payer**, **investor**, **issuer**.
2. **`setup.yaml` seeded** — `yieldfabric execute ../scripts/setup.yaml` — creates users,
   assets, and groups (incl. the per-party groups the group suite needs).
3. **Services up:** auth (:3000), agents (:3001), payments (:3002), and the test node
   (Hardhat/anvil) reachable at `ETH_RPC_URL` (default `http://localhost:8545`).

**Run each suite on its own fresh deploy.** Suites reuse swap-id ranges and advance
chain time; running two back-to-back on one node can collide or skew timestamps.

---

## The suites

| Suite | Cmds | What it proves | Status |
|---|---|---|---|
| [`swap_repo_suite`](swap_repo_suite.yaml) | 100 | Foundational A–G: atomic swap, repo (NFT + payment collateral, either side), roll, rehyp, nested collateral | baseline |
| [`swap_rehyp_forfeiture_suite`](swap_rehyp_forfeiture_suite.yaml) | 43 | Rehyp × forfeiture: forfeit-forward cascade routes to the end-lender (N, F2–F5) | ✓ (fixes in #59; #68 documented) |
| [`swap_nested_advanced_suite`](swap_nested_advanced_suite.yaml) | 80 | Rolls × rehyp, depth-3, repurchase-cascade routing (G1–G3, H1, I1, J1, K1, L) | ✓ (K1/L confirmed) |
| [`swap_lifecycle_combinations_suite`](swap_lifecycle_combinations_suite.yaml) | 93 | Roll × repurchase × forfeit on one 3–4 level chain, happy + unhappy (M1–M3, U1–U6) | ✓ (#71 as expect_failure) |
| [`swap_lifecycle_combinations_group_suite`](swap_lifecycle_combinations_group_suite.yaml) | 105 | The lifecycle suite run entirely from **group accounts** | ✓ passing |
| [`swap_exchange_conservation_suite`](swap_exchange_conservation_suite.yaml) | 51 | Every leg credits the right party by the **exact** amount — upfront, repurchase, forfeit, plain swap (E1–E4) | ✓ passing |
| [`swap_repo_transfer_matrix`](swap_repo_transfer_matrix_suite.yaml) | 39 | **Transfer the repo position** to a new counterparty, then repurchase/forfeit/roll follow the new holder (T1–T4) | T1/T2 ✓; T3 #75 fixed (re-run); T4 pending |
| [`swap_claim_gated_suite`](swap_claim_gated_suite.yaml) | 59 | Swap of an obligation in a **claim-gated** (ERC-3643/Tokeny) class: verified buyer receives via the vault/swap **exemption** (P); unverified buyer blocked at delivery (N); seller who loses KYC mid-escrow can't recover until re-verified (R); soul-bound (`transferable:false`) class can't be escrowed (S) | P/N live-proven; R/S authored |
| [`swap_claim_gated_repo_suite`](swap_claim_gated_repo_suite.yaml) | 53 | Per-class (gated) obligations through the **repo** flows: gated-collateral repurchase (A), roll (B), expiry/forfeit (C) — proves the per-class routing in `repurchase.rs`/`roll.rs` | authored; pending first run |

### `swap_repo_suite.yaml` — foundational functional gate
The original pre-deployment suite. Scenarios:
- **A** atomic swap (happy + unhappy) · **B** repo with NFT collateral + repurchase ·
  **C** repo with payment collateral + forfeiture · **D** collateral on the counterparty side ·
  **E** roll (initiate → complete → repurchase) · **F** rehypothecation (repo A → repo B → unwind) ·
  **G** nested collateral (NFT + payment on both sides).

### `swap_rehyp_forfeiture_suite.yaml` — rehyp × forfeiture
A 2-level rehyp chain (underlying → Repo A → Cont_A re-pledged → Repo B) under every default order:
- **N** single-level NFT-collateral forfeiture (baseline) · **F2** outer(B) forfeit → inner(A)
  repurchase routes to the Cont_A holder · **F3** inner(A) forfeit after outer(B) unwind ·
  **F4** double default → forfeit-forward cascade (underlying to the end-lender) ·
  **F5** direct **transfer** of the repo position, then A repurchase routes to the transferee.
- Surfaced + fixed the forfeit-forward recipient bugs (task #59). **#68** (rehyp of a
  *payment*-collateral repo) documented as an unsupported combo.

### `swap_nested_advanced_suite.yaml` — nested matrix
Rolls × rehyp, order variants, depth-3, balance-asserted routing:
- **G1** roll the outer repo of a rehyp chain, then unwind · **G2** roll the inner repo while
  pledged (exploratory) · **G3** double-default forfeit after an outer roll · **H1** inner forfeit
  first · **I1** rehyp of a payment-collateral repo is rejected at re-pledge (documents the #68
  limitation) · **J1** depth-3 triple-default cascade · **K1** repurchase-cash routing asserted at
  the balance level · **L** repurchase-cash cascade (only the outermost level's cash is freely
  claimable; inner is locked as collateral up the chain).

### `swap_lifecycle_combinations_suite.yaml` — all three ops combined
Roll, repurchase, and forfeit on the **same** nested chain (3 and 4 levels), happy + unhappy:
- **M1** roll the outer then full repurchase-unwind · **M2** repurchase the outer + forfeit the
  inner · **M3** 4-level chain, a different terminal op per level (repurchase → roll → repurchase →
  forfeit → forfeit) · **U1–U6** rejection guards (forfeit-before-deadline, op-after-terminal,
  wrong-party roll/complete-roll, repurchase-after-forfeit).
- The rolled-swap repurchase legs are `expect_failure` pending the **#71** roll→repurchase gap.

### `swap_lifecycle_combinations_group_suite.yaml` — group accounts
The lifecycle suite where **every party is a group** (Payer / Investor / Issuer Group). Operations
are signed by the group's confidential account (`user.group`); counterparties are named by group.
Requires the three per-party groups in `setup.yaml`. Funds each group via owner-deposit →
instant-send to group → group accept.

### `swap_exchange_conservation_suite.yaml` — does every leg settle?
Verifies the core exchange that other suites assumed, with **exact per-leg conservation** (the
assert `minus:` delta):
- **E1** the **upfront leg** — does the borrower actually receive the lender's cash? (it does) ·
  **E2** full repo cycle, all 4 cash deltas exact + collateral round-trip · **E3** forfeit cycle
  (borrower keeps the loan, lender keeps the collateral) · **E4** plain bilateral swap (obligation ⇄
  cash, no repo).

### `swap_repo_transfer_matrix_suite.yaml` — swapping the repo to a new counterparty
The lender **transfers** the repo position (`transfer_obligation` on `COMPOSED-CONTRACT-REPO-SWAP-{swap}`),
then each terminal op must follow the new holder:
- **T1** transfer → repurchase: cash to the new holder (exact delta); original lender can't claim ·
  **T2** transfer → forfeit: collateral to the new holder (forfeit *trigger* is permissionless;
  recipient follows the holder) · **T3** transfer → roll: **documented limitation** — `complete_roll`
  reverts `InvalidCollateralPayment` on a transferred position (#75) · **T4** double transfer →
  repurchase routes to the final holder.

### `swap_claim_gated_suite.yaml` — claim-gated swap + the vault/swap exemption
The only suite that gates the **asset itself**: the obligation is minted into a
ConfidentialObligation **class** with its own ERC-3643 IdentityRegistry requiring a
KYC claim (topic on the CTR, trusted issuer on the TIR). Proves the
`ExemptIdentityRegistry` invariant end-to-end:
- **P** a **verified** buyer (investor) completes the swap and receives the gated
  obligation — mint into the gated class → escrow into the **exempt** swap → deliver
  to a verified recipient (gate passes) → cash to the seller (exact delta).
- **N** an **unverified** buyer (the issuer, which configured the class but never
  KYC'd itself) is blocked: `create_swap` succeeds (escrow into the exempt swap) but
  `complete_swap` reverts at the recipient gate; the seller then cancels and recovers
  the asset — the gate protects **without loss**.
- **R** a verified seller who **loses KYC mid-escrow** can't recover their own asset:
  after escrow, the issuer `revoke_claim`s the seller, so `cancel_swap`'s refund reverts
  at the recipient gate; re-issue + re-accept restores the seller and the same cancel
  succeeds — the (intentional, compliance-consistent) gate-on-return is **recoverable**
  (security-review finding #2).
- **S** a **soul-bound** class (`transferable:false`) can be minted + held but **not
  escrowed**: `create_swap` reverts on the escrow transfer — the per-class `transferable`
  flag is enforced on the swap path (static form of finding #1).

Repo companion: [`swap_claim_gated_repo_suite`](swap_claim_gated_repo_suite.yaml) drives
the same gated class through **repurchase, roll, and expiry/forfeit** (proving the
per-class routing in `repurchase.rs`/`roll.rs`). Contract-level proof lives in hardhat
[`test/ConfidentialSwapPerClass.test.ts`](../../yieldfabric-smart-contracts/test/ConfidentialSwapPerClass.test.ts):
escrow + release both route to the per-class proxy, a malicious `obligation_address` is
bounded to self-harm, and an owner-freeze strands the asset without theft — **8/8 passing**.

Holder-side companion to `claims_lifecycle_group_suite` (which configures the IR but
deliberately stops before holder `isVerified`). Live-run notes: **P/N are live-proven**
(deploy, full gate config topic→CTR + issuer ClaimIssuer→TIR, escrow, delivery, and the
recipient-gate block); R/S and the repo companion are authored, pending a first run.
Holder registration is **not** a per-class step — accounts are pre-registered in the
shared IdentityRegistryStorage at account deploy and per-class IRs share it, so an
explicit `register_identity` reverts `address stored already`; the suite verifies holders
by claim alone.

---

## Harness reference (how to read / write a suite)

### Command anatomy
```yaml
- name: e2_create                 # unique; also the output-store key
  type: create_swap               # dispatched to an executor (see runner.py)
  user: { id: payer@yieldfabric.com, password: payer_password }
  parameters: { swap_id: "880002", ... }
```

### Acting as a user vs a group
Add `group: <Group Name>` to the user block to run the op **as that group** (delegation JWT; the
group's confidential account signs). Counterparties may be named by group too.
```yaml
user: { id: issuer@yieldfabric.com, password: issuer_password, group: Issuer Group }
counterparty: { id: Investor Group, expected_payments: { ... } }
```

### Output references — `$<command>.<field>`
Any later `parameters` value may reference a prior command's output: `$e2_create.swap_id`,
`$bal_after.private_balance`. **No `$step.` prefix.** The `balance` command exposes
`private_balance` / `locked_in` / `locked_out` / `beneficial`.

### `assert` — outcome checks
Exactly one operator, both sides substituted first:
`equals | not_equals | contains | not_contains | gte | gt | lte | lt`. Big-int safe.
```yaml
- type: assert
  parameters: { actual: "$after.private_balance", gt: "$before.private_balance" }
```
**`minus:` (delta)** — `actual := actual − minus` before comparing. Turns a before/after pair into
an **exact balance-change / conservation** check:
```yaml
- type: assert
  parameters:
    actual: "$aud_after.private_balance"
    minus:  "$aud_before.private_balance"     # actual := after - before
    equals: "1000000000000000000000"          # delta must equal 1000 AUD exactly
```

### Negative tests — `expect_failure` / `expect_error`
`expect_failure: true` flips the verdict (a failed command PASSES, a success FAILS). Optional
`expect_error: "<substring>"` requires the surfaced error to match. Used for rejection guards.

### Chain time — the cumulative rule
`advance_chain_time` does `evm_increaseTime + evm_mine`; the offset **stacks** for the whole run,
so `chain_time = wall_clock + Σ(all advances)`. Therefore, **per forfeit scenario**:
- **create** is rejected unless `deadline_offset > Σ_before + 120s`;
- **`expire_collateral`** fires only once `Σ_after (= Σ_before + this advance) > the EXPIRY offset`.

So forfeit deadlines/expiries must **grow** to stay ahead of the running Σ. Repurchased/rolled
levels use day-scale (`+40d`) expiries so advances never reach them.

`mine_block` (no-op off-localhost) forces a fresh block — `block.timestamp` only advances when a
block is mined. Params: `blocks` (default 1), `interval` (seconds between blocks).

### Funding (deploy seeds public ERC-20 to payer / investor / issuer only)
- **Individual:** `deposit` converts the caller's public ERC-20 → confidential balance.
- **Group:** a fresh group holds no ERC-20, so fund it via owner `deposit` (as self) → `instant`
  send to the group by name → group `accept_all` (as the group).

### Payment record naming (what to `accept`)
| Record | Created at | Payee | Notes |
|---|---|---|---|
| `PAY-SWAP-{swap}-counterparty-0` | complete | borrower (initiator) | the lender's **upfront**; pull-based |
| `PAY-REPURCHASE-{swap}-0` | repurchase | lender (current holder) | the **repurchase cash** |
| `PAY-REPURCHASE-OBLIGATION-{swap}-0` | complete | — | **placeholder** (id_hash 0x0); *not* the cash record |
| `PAY-COLLATERAL-{role}-{swap}` | forfeit | counterparty | forfeited collateral payment |
| `PAY-ROLL-UPFRONT/REPURCHASE-{new_swap}-0` | roll | — | roll-time legs |

### Ownership-verify pattern
To prove who owns an obligation after a forfeit/transfer, offer it in a fresh `create_swap`
(`initiator.obligation_ids: [<id>]`) **as the expected owner** — it succeeds only if they hold it.
A **non-owner** offering it is now **rejected** with a typed error (`"does not hold obligation
contract <id>"`); the residual-risk RR2 negatives assert that reason via `expect_error`. This holds
for any **explicitly-named** leg (an `obligation_ids` / `collateral_obligation_ids` entry, or a
single-`contract_id` reference); only `composed_contract_id` expansions silently drop their un-held
nested legs (a repo position legitimately resolves to the escrowed underlying it doesn't hold).

### Party / funding model
Only **payer / investor / issuer** are funded. Chains reuse the three circularly (roll-in lenders
and end-lenders reuse a funded party not already that swap's lender). Self-counterpart payment-less
obligations auto-accept at mint.

---

## Key system behaviors confirmed by these tests

- **Repo lifecycle:** `create_swap` → `complete_swap` (lender pays upfront, collateral escrows) →
  `repurchase_swap` (borrower buys back) **or** `expire_collateral` (forfeit on default) **or** roll.
- **Upfront leg delivers:** at `complete`, the lender's cash lands in the borrower's `locked_in`
  (pull-based; the auto-retrieve only fires for the completer's own receivables) — the borrower
  must `accept` `PAY-SWAP-{swap}-counterparty-0`. Verified exact in E1/E2.
- **Repurchase cash cascades up a rehyp chain:** cash paid into an inner repo is locked as
  collateral up the chain; only the **outermost** level's repurchase cash is freely claimable
  (suite L).
- **Forfeit-forward cascade:** on default, collateral forfeits to the *current holder* of the
  repurchase obligation and cascades up to the end-lender (F4/J1).
- **Position transfer:** `transfer_obligation` moves ownership **and** the payment payee to the new
  holder — so repurchase cash routes to the transferee and the original lender can't claim (T1).
- **Forfeit trigger is permissionless** (recipient is the holder, not the caller); claiming a
  payment is payee-gated (T2 vs T1).

---

## Open findings (tracked as tasks)

- **#71 — roll→repurchase gap — FIXED (in code; awaiting live re-run):** repurchasing a *rolled* swap
  emitted no transaction contexts (the repurchase is pre-funded at roll-complete), so the new lender's
  `PAY-REPURCHASE-{new_swap}-0` was never created. The repurchase post-processor now falls back to the
  roll's stored `repurchase_prefund_id_hashes` and writes the record with the real id_hash. The
  lifecycle suites' rolled-repurchase claims were flipped from `expect_failure` to positive assertions.
- **#68 — rehyp of a payment-collateral repo — FIXED (in code; awaiting re-run):** re-pledging was
  rejected ("No token associated") because the payment-collateral child has no NFT until forfeit.
  `resolve_contract_ids` now skips tokenless children and pledges the repurchase-obligation NFT
  instead. I1 flipped to a positive rehyp test.
- **#75 — roll × transfer — FIXED (in code; awaiting re-run):** `complete_roll` reverted on a
  *transferred* position because the vault routed the coverage to the **stored** counterparty while
  the contract validates the **current holder**. `roll.rs` now routes to `getCounterpartyAddress`
  (the dynamic holder). A Rust/vault fix — **no contract redeploy**. T3 flipped to a positive assertion.
- **T4** of the transfer matrix not yet verified (the run previously halted at T3 — now fixed).

---

## Writing a new suite (the skeleton)

```yaml
# Header: purpose, parties, prerequisites, the chain-time budget if it forfeits.
commands:
  # 1. Fund (individual deposits, or group deposit→instant→accept)
  # 2. Mint the underlying obligation(s) (self-counterpart → auto-accepts)
  # 3. create_swap → complete_swap (snapshot balances around the legs you assert)
  # 4. The terminal op(s): repurchase_swap / expire_collateral / initiate_roll+complete_roll
  # 5. accept the resulting payment(s) by their record name
  # 6. assert with `minus:` for exact deltas; verify ownership via a create_swap offer
  # 7. Negatives with expect_failure (+ expect_error where the message is stable)
```

Rules of thumb: snapshot **before and after** every leg you assert; use the exact record name from
the table above; for forfeits keep `advance > expiry` and grow deadlines past the cumulative Σ; run
on a fresh deploy.

---

## Other test files (not part of the swap/repo set; documented elsewhere / TBD)

- **Setup:** `setup.yaml` (+ `setup_testnet` / `setup_*_mainnet`) — seed users, assets, groups.
- **Walkthroughs / examples:** `commands.yaml` (canonical walkthrough), `composed_example.yaml`,
  `swap_deal.yaml`, `swap_payment.yaml`, `loan.yaml`, `linear.yaml`, `treasury.yaml`.
- **Annuities:** `settle_annuity_aud.yaml`, `settle_annuity_cbdc.yaml`, `composed_settle_annuity.yaml`.
- **Groups / policies:** `datapolicy_group_suite.yaml` (data-policy on group accounts, restricted
  member execution).
- **Deal flows:** `nc_acacia.yaml` (+ `_mainnet`).

These predate the swap/repo testing push and warrant their own documentation pass.
