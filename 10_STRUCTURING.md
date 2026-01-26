# Financial Structuring with YieldFabric

A comprehensive guide for financial structuring specialists on how to design and implement sophisticated financial instruments using YieldFabric's programmable payment infrastructure.

---

## Executive Summary

YieldFabric is a blockchain-based platform that enables the creation, management, and trading of **programmable confidential cashflows**. It provides the building blocks for structuring complex financial products with:

**Core Building Blocks:**
- **Intelligent Accounts**: Policy-based account abstraction enabling fund segregation and programmable access control
- **Contracts**: Programmable payment commitments with time locks, oracle conditions, and multiple payment streams
- **Atomic Swaps**: Risk-free bilateral exchanges of contracts and payments
- **Repurchase Agreements (Repos)**: Collateralized lending with repurchase options and automatic forfeiture
- **Credit & Cash Payments**: Support for both funded and unfunded payment structures
- **Time-Based & Event-Based Unlocks**: Payments that execute based on dates or external events

**Applications Built on Building Blocks:**
- **Bonds**: Debt instruments with coupon and principal payment streams (can be collateralized with digital assets)
- **Loans**: Lending structures with repayment schedules (can be collateralized with digital assets)
- **Escrows**: Conditional release accounts with policy-based fund management
- **Progress Payments**: Milestone-based payments with oracle verification
- **Asset Backed Securities**: Securitized pools of underlying assets
- **Corporate Treasury Manager**: Policy-based treasury management with fund segregation and spending controls
- **Supply Chain Financing**: Invoice and purchase order financing with early payment options
- **Funds and SPV Balance Sheet Manager**: Policy-based payments and distributions for funds and SPVs
- **Tokenized Credit Facilities**: Credit lines implemented using Intelligent Accounts with policy-based drawdown rules
- **Investor Callable Accounts**: Policy-based accounts enabling on-demand withdrawals within cryptographic constraints

This document explains how to leverage these capabilities to structure financial products ranging from simple invoices to complex structured notes.

---

## Core Building Blocks

### 1. Contracts

Programmable payment commitments between parties. Can contain single or multiple payment streams managed as one instrument. Support time locks, oracle conditions, linear vesting, and credit/cash payments. All payments execute atomically.

**Use Cases:** Bonds, loans, annuities, invoices, royalty agreements, structured products, multi-tranche structures, securitization.

### 2. Swaps

Atomic exchange mechanisms enabling simultaneous trading of contracts and payments without counterparty risk. Both sides execute simultaneously or transaction fails. Supports multi-asset exchanges with deadline management.

**Use Cases:** Securitization, debt trading, structured finance, asset exchanges.

### 3. Repurchase Agreements (Repos)

Collateralized lending built on swap infrastructure with repurchase options and automatic forfeiture. Two time windows: deadline (swap completion) and expiry (repurchase). Bilateral collateral; each party can repurchase their own collateral before expiry. Automatic forfeiture after expiry.

**Use Cases:** Short-term funding, securities lending, liquidity management, secured financing, margin lending.

### 4. Payments

Individual payment transactions (cash or credit). Support time locks, oracle triggers, linear vesting, and outstanding balance tracking per obligor.

**Use Cases:** Instant transfers, scheduled payments, conditional payments, vesting schedules.

### 5. Intelligent Accounts

Policy-based account abstraction enabling fund segregation and programmable access control. Cryptographic policies govern fund access and usage. Supports multi-signature, delegation, and token-based access. All operations automatically checked against policies.

**Use Cases:** Segregated fund accounts, escrow accounts, treasury management, multi-party accounts, delegated access.

---

## Applications Built on Building Blocks

### Application 1: Tokenized Credit Facilities

Credit facilities using Intelligent Accounts with policy-based drawdown rules. Credit lines are represented as transferable tokens that automatically enforce usage restrictions.

**Key Features:**
- Transferable credit facility tokens
- Policy-based drawdown restrictions (e.g., equipment purchases only)
- Cryptographic on-chain enforcement

**Example: Tokenized Credit Facility**
```
Intelligent Account: "Equipment Financing Credit Line"

Structure:
- Credit Facility Token: Represents 1,000,000 AUD credit line
- Policy: Drawdowns only allowed for equipment purchases
- Oracle Integration: Verify equipment purchase invoices
- Drawdown Process:
  1. Token holder requests drawdown
  2. Policy checks: Is this for equipment purchase?
  3. Oracle verifies purchase documentation
  4. If valid, funds released to equipment vendor
  5. Credit balance updated

Result: Credit facility with automatic policy enforcement
```

**Use Cases:**
- Equipment financing
- Working capital lines
- Project-specific funding
- Trade finance
- Supply chain financing

### Application 2: Investor Callable Accounts

Investment accounts using Intelligent Accounts enabling on-demand withdrawals within cryptographic policy constraints (notice periods, amount limits, conditions).

**Example: Investor Callable Account**
```
Intelligent Account: "Investment Fund - Series A"

Structure:
- Investor Tokens: Each token represents investment share
- Withdrawal Policy: 
  - Minimum notice: 30 days
  - Maximum withdrawal: 25% of account balance per month
  - Oracle condition: Fund NAV must be above threshold
- Withdrawal Process:
  1. Investor requests withdrawal
  2. Policy checks: Notice period met? Amount within limit? NAV above threshold?
  3. If all conditions met, funds released
  4. Investor token balance updated

Result: Callable investment account with policy-based withdrawals
```

**Use Cases:**
- Open-ended investment funds
- Hedge funds with redemption policies
- Private equity funds with withdrawal windows
- Managed accounts with liquidity provisions

### Application 3: Bonds

Debt instruments using Contracts with coupon and principal payment streams. Coupons unlock at regular intervals; principal at maturity. Supports zero-coupon, callable, puttable, and floating rate structures.

**Collateralization:** Bonds can be collateralized with digital assets using a combination of contracts, future payments, and repo swaps. The bond contract is secured by collateral assets locked in a repo structure, providing credit enhancement and risk mitigation.

**Example: Corporate Bond**
```
Contract: "5-Year Corporate Bond - 5% Coupon"

Payment Stream 1: Quarterly Coupons
- Notional: 1,000,000 AUD
- Coupon Rate: 5% per annum
- Payment: 12,500 AUD per quarter
- Frequency: Quarterly (20 payments over 5 years)
- Unlock Dates: Every 3 months

Payment Stream 2: Principal Redemption
- Amount: 1,000,000 AUD
- Date: Maturity (5 years from issue)
- Single payment

Result: Single contract with coupon income + principal return
```

**Example: Collateralized Bond**
```
Structure:
1. Create bond contract with coupon and principal streams
2. Create repo swap with bond contract as primary asset
3. Lock digital assets (e.g., stablecoins, tokens) as collateral
4. Collateral provides security for bond payments
5. If default, collateral forfeits to bondholders via repo expiry

Result: Bond secured by digital asset collateral
```

**Use Cases:**
- Corporate bonds
- Government bonds
- Municipal bonds
- Convertible bonds
- Zero-coupon bonds
- Floating rate notes
- Collateralized bonds

### Application 4: Loans

Lending structures using Contracts with principal and interest repayment streams. Supports amortizing, interest-only, and balloon structures. Outstanding balance tracked per obligor.

**Collateralization:** Loans can be collateralized with digital assets using a combination of contracts, future payments, and repo swaps. The loan contract is secured by collateral assets locked in a repo structure, reducing credit risk and enabling better terms.

**Example: Term Loan**
```
Contract: "5-Year Term Loan"

Payment Stream 1: Principal Repayment
- Amount: Principal / Number of payments
- Frequency: Monthly
- Duration: 5 years
- Amortization: Equal payments

Payment Stream 2: Interest Payments
- Amount: Outstanding × Interest Rate / Frequency
- Frequency: Monthly
- Duration: 5 years
- Calculation: Based on remaining principal

Result: Loan with scheduled principal and interest repayments
```

**Example: Collateralized Loan**
```
Structure:
1. Create loan contract with principal and interest streams
2. Create repo swap with loan contract as primary asset
3. Lock digital assets (e.g., tokens, stablecoins) as collateral
4. Collateral secures loan repayment obligations
5. If default, collateral forfeits to lender via repo expiry

Result: Loan secured by digital asset collateral
```

**Use Cases:**
- Term loans
- Revolving credit facilities
- Construction loans
- Equipment financing
- Working capital loans
- Personal loans
- Collateralized loans

### Application 5: Escrows

Escrow accounts using Intelligent Accounts with conditional release policies. Oracle integration verifies external conditions (delivery, completion). Funds automatically released when conditions are met.

**Example: Escrow Account**
```
Intelligent Account: "Purchase Escrow"

Structure:
- Escrow Policy: Funds released upon delivery confirmation
- Oracle Integration: Verify delivery documentation
- Release Process:
  1. Buyer deposits funds into escrow
  2. Seller delivers goods/services
  3. Oracle verifies delivery documentation
  4. If verified, funds automatically released to seller
  5. If not verified within deadline, funds returned to buyer

Result: Secure escrow with automatic conditional release
```

**Use Cases:**
- Purchase escrows
- Construction escrows
- Milestone-based payments
- Dispute resolution escrows
- M&A transaction escrows
- Real estate escrows

### Application 6: Progress Payments

Milestone-based payments using Contracts with oracle-triggered releases. Each payment stream tied to a milestone (delivery, inspection, certification). Supports partial completion payments.

**Example: Construction Progress Payments**
```
Contract: "Construction Project - Progress Payments"

Payment Stream 1: Foundation Completion (20%)
- Amount: 200,000 AUD
- Oracle Condition: Foundation inspection passed
- Unlock: When oracle confirms inspection approval

Payment Stream 2: Framing Completion (30%)
- Amount: 300,000 AUD
- Oracle Condition: Framing inspection passed
- Unlock: When oracle confirms inspection approval

Payment Stream 3: Final Completion (50%)
- Amount: 500,000 AUD
- Oracle Condition: Final inspection and occupancy permit
- Unlock: When oracle confirms final approval

Result: Progress payments with automatic milestone verification
```

**Use Cases:**
- Construction projects
- Software development contracts
- Manufacturing milestones
- Research and development projects
- Service delivery milestones
- Government contracts

### Application 7: Asset Backed Securities

Securitization structures using Contracts bundling multiple underlying assets. Payment streams can be tranched (senior, mezzanine, equity). Originator receives immediate liquidity via swap.

**Example: Mortgage-Backed Security**
```
Contract: "Mortgage-Backed Security - Pool A"

Payment Stream 1: Senior Tranche
- Amount: 7,000,000 AUD (70% of pool)
- Priority: First claim on all payments
- Payment Schedule: Pro-rata from loan repayments
- Lower risk, lower yield

Payment Stream 2: Mezzanine Tranche
- Amount: 2,000,000 AUD (20% of pool)
- Priority: Second claim (after senior)
- Payment Schedule: Pro-rata from remaining payments
- Medium risk, medium yield

Payment Stream 3: Equity Tranche
- Amount: 1,000,000 AUD (10% of pool)
- Priority: Residual (after senior and mezzanine)
- Payment Schedule: All remaining payments
- Higher risk, higher yield

Result: Securitized pool with risk segmentation
```

**Use Cases:**
- Mortgage-backed securities (MBS)
- Asset-backed securities (ABS)
- Collateralized debt obligations (CDO)
- Receivables securitization
- Loan securitization
- Trade receivables financing

### Application 8: Corporate Treasury Manager

Treasury management using Intelligent Accounts with policy-based spending controls and fund segregation. Supports multi-signature approvals and oracle-based budget enforcement.

**Example: Corporate Treasury Management**
```
Intelligent Account: "Corporate Treasury - Operating Account"

Structure:
- Operating Account: Daily operations funding
- Spending Policy:
  - Department heads: Up to 50,000 AUD per transaction
  - CFO approval: Required for transactions > 50,000 AUD
  - CEO approval: Required for transactions > 500,000 AUD
  - Budget Oracle: Monthly spending cannot exceed budget
- Reserve Account: Emergency fund with restricted access
- Investment Account: Surplus cash with investment policies

Result: Automated treasury management with policy-based controls
```

**Use Cases:**
- Corporate cash management
- Multi-entity treasury consolidation
- Budget control and enforcement
- Automated approval workflows
- Reserve fund management
- Investment account segregation
- Intercompany fund management

### Application 9: Supply Chain Financing

Financing solutions using Contracts and Intelligent Accounts for supplier liquidity. Supports invoice financing, purchase order financing, dynamic discounting, and oracle-verified delivery/quality.

**Example: Supply Chain Financing**
```
Contract: "Supplier Invoice - PO-12345"

Structure:
- Invoice Amount: 100,000 AUD
- Payment Terms: Net 60 days
- Oracle Condition: Delivery confirmation
- Early Payment Option:
  - 2% discount if paid within 10 days
  - 1% discount if paid within 30 days
  - Full amount if paid at 60 days

Financing Flow:
1. Supplier creates contract with invoice details
2. Financier reviews and accepts contract
3. Financier can swap contract for immediate cash (with discount)
4. Buyer pays at maturity to financier
5. Oracle verifies delivery before final payment

Result: Supplier gets early liquidity, buyer extends payment terms
```

**Use Cases:**
- Invoice financing
- Purchase order financing
- Dynamic discounting
- Reverse factoring
- Supplier credit facilities
- Trade finance
- Supply chain credit programs
- Early payment programs

### Application 10: Funds and SPV Balance Sheet Manager

Balance sheet management for funds and Special Purpose Vehicles (SPVs) using Intelligent Accounts with policy-based payments and distributions. Enables automated cash flow management, investor distributions, and liability payments based on cryptographic policies.

**Key Features:**
- **Policy-Based Distributions**: Automated investor distributions based on predefined policies
- **Cash Flow Management**: Automatic allocation of incoming payments to liabilities and distributions
- **Multi-Party Payments**: Policy-based payments to investors, creditors, and service providers
- **Balance Sheet Segregation**: Separate accounts for assets, liabilities, and equity
- **Oracle Integration**: Trigger distributions based on external events (NAV calculations, performance metrics)

**Example: Fund Balance Sheet Management**
```
Intelligent Account: "Investment Fund - Balance Sheet Manager"

Structure:
- Asset Account: Receives investment returns and capital calls
- Liability Account: Manages fund expenses and creditor payments
- Distribution Account: Handles investor distributions

Distribution Policy:
- Quarterly distributions: 80% of net income
- Capital return: After hurdle rate achieved
- Waterfall: Preferred return → catch-up → carried interest
- Oracle: NAV calculation triggers distribution calculations

Payment Flow:
1. Investment returns flow into Asset Account
2. Policy calculates net income (after expenses)
3. Oracle verifies NAV and performance metrics
4. Distribution policy determines allocation:
   - Expenses → Liability Account
   - Preferred return → Investors
   - Catch-up → General partners
   - Carried interest → General partners
5. Payments execute automatically based on policy

Result: Automated balance sheet management with policy-based distributions
```

**Example: SPV Balance Sheet Management**
```
Intelligent Account: "SPV - Asset Backed Structure"

Structure:
- Asset Account: Receives payments from underlying assets
- Senior Debt Account: Manages senior tranche payments
- Mezzanine Debt Account: Manages mezzanine tranche payments
- Equity Account: Residual distributions to equity holders

Payment Policy:
- Priority: Senior debt → Mezzanine debt → Equity
- Waterfall: Sequential payment based on priority
- Reserve: Maintain minimum reserve before distributions
- Oracle: Asset performance triggers payment calculations

Payment Flow:
1. Underlying assets generate cash flows
2. Cash flows into Asset Account
3. Policy applies waterfall:
   - Senior debt service → Senior Debt Account
   - Mezzanine debt service → Mezzanine Debt Account
   - Residual → Equity Account
4. Reserve policy maintains minimum balance
5. Distributions execute automatically

Result: Automated SPV balance sheet with priority-based payment waterfall
```

**Use Cases:**
- Investment fund balance sheet management
- SPV cash flow management
- Private equity fund distributions
- Hedge fund investor payouts
- Real estate fund distributions
- Infrastructure fund management
- Securitization vehicle management
- Structured finance SPVs

---

## Structuring Patterns

### Pattern 1: Self-Referential Construction

**Concept:** Build complex structures independently without counterparty risk, then transfer atomically.

**How It Works:**
1. Create contracts with yourself as both issuer and counterparty
2. Accept your own contracts (locks the structure)
3. Swap the contracts atomically to the actual counterparty

**Benefits:**
- No counterparty risk during construction
- Structure is locked before external involvement
- Atomic transfer ensures security

**Example: Securitization**
```
1. Issuer creates self-referential contracts:
   - Contract A: 50 AUD due in 6 months
   - Contract B: 55 AUD due in 12 months
   
2. Issuer accepts own contracts (structure locked)

3. Issuer swaps contracts to investor:
   - Gives: Contracts A + B (105 AUD total)
   - Receives: 100 AUD immediately (cash, no obligor)
   
Result: Issuer gets liquidity, investor gets yield-bearing asset
```

### Pattern 2: Multi-Stream Contracts

Combine multiple payment streams into a single contract. Each stream can have different schedules and conditions. All payments execute atomically.

### Pattern 3: Conditional Payment Structures

Payments execute based on external events (oracles). Define oracle conditions; payments remain locked until confirmed. Supports event verification, price movements, and other external data.

### Pattern 4: Repurchase Agreements (Repos)

Collateralized lending with repurchase options and automatic forfeiture. Two time windows: deadline (swap completion) and expiry (repurchase). Bilateral collateral; each party can repurchase their own collateral before expiry. Automatic forfeiture after expiry.

**Collateralization of Bonds and Loans:** Repos enable collateralization of bonds and loans with digital assets. The bond or loan contract (with future payment streams) is combined with digital asset collateral in a repo structure, providing secured financing with automatic forfeiture mechanisms.

### Pattern 5: Multi-Tranche Structures

Create hierarchical payment structures with different risk/return profiles. Each payment stream represents a tranche with prioritized payment claims (senior, mezzanine, equity).

---

## Advanced Techniques

**Dynamic Payment Schedules**: Use oracle conditions to determine payment amounts based on external data (prices, rates, events).

**Conditional Structures**: Create contracts with oracle conditions; structure remains locked until condition met. Supports AND/OR logic.

**Multi-Currency Structures**: Create contracts with different denominations. Each payment stream uses different asset ID. Swaps can exchange multiple currencies atomically.

**Time-Based Vesting**: Use `linearVesting = true` for gradual unlock over time. Payments unlock proportionally; partial acceptance supported.

**Credit Enhancement**: Structure payment priority (senior/subordinated) and add guarantee payment streams from third parties.

---

## Structuring Workflows

**Secure Securitization**: (1) Create self-referential contracts (yourself as counterparty), (2) Accept own contracts to lock structure, (3) Create swap offering contracts for immediate cash, (4) Investor completes swap atomically. Result: Liquidity without counterparty risk during construction.

**Structured Product Issuance**: (1) Create contract with capital protection and equity participation streams, (2) Set oracle conditions, (3) Accept contract to lock structure, (4) Distribute via swap to investors. Result: Complex structured product with atomic distribution.

**Loan Origination & Securitization**: (1) Create loan contracts with principal and interest streams, (2) Tranche structure (senior/mezzanine/equity), (3) Swap tranches separately to investors. Result: Risk segmentation with atomic settlement.

---

## Design Considerations & Best Practices

**Payment Scheduling:**
- **Time Locks**: `unlockSender` (cancel/retrieve) and `unlockReceiver` (accept) for scheduled payments
- **Linear Vesting**: Gradual unlock over time; allows partial acceptance
- **Oracle Conditions**: Event-based or price-based unlocks

**Credit vs Cash:**
- **Cash** (`obligor = null`): Immediate, unconditional; no outstanding balance tracking
- **Credit** (`obligor = entity`): Future obligation; tracks outstanding balance
- Use cash for immediate payments; credit for debt structures

**Atomic Operations:**
- Contracts: All payment streams created together, atomic acceptance
- Swaps: Both sides execute simultaneously or nothing happens
- Eliminates counterparty risk and ensures structure integrity

**Acceptance Windows:**
- Contract expiry defines acceptance window (separate from payment unlock dates)
- Set realistic expiry dates for acceptance; set unlock dates for payment schedules
- Once accepted, expiry no longer relevant

**Structure Design:**
- Start simple, add complexity gradually
- Use self-referential construction to eliminate counterparty risk during building
- Combine related payment streams in one contract
- Use integer strings for payment amounts (no decimals)
- Set realistic swap deadlines and clear terms

---

## Integration with Traditional Finance

### Regulatory Considerations

- **Know Your Customer (KYC)**: Entities must be verified
- **Anti-Money Laundering (AML)**: Transaction monitoring
- **Securities Regulations**: Structures may be subject to securities laws
- **Tax Treatment**: Consult tax advisors for structure implications

### Accounting Treatment

- **Contracts**: Record as liabilities (if issuer) or assets (if holder)
- **Swaps**: Mark-to-market or accrual accounting depending on structure
- **Outstanding Balance**: Track credit/debt per obligor
- **Payment Schedules**: Amortize over payment periods

### Risk Management

- **Credit Risk**: Track obligor outstanding balances
- **Liquidity Risk**: Consider acceptance windows and unlock dates
- **Market Risk**: Oracle-based structures subject to underlying movements
- **Operational Risk**: Ensure oracle reliability and verification

---

## Summary

YieldFabric provides a powerful platform for financial structuring with:

**Core Building Blocks:**
1. **Intelligent Accounts**: Policy-based account abstraction for fund segregation and programmable access control
2. **Contracts**: Create sophisticated payment structures with time locks, conditions, and multiple payment streams
3. **Atomic Swaps**: Execute risk-free bilateral exchanges
4. **Credit & Cash Support**: Handle both funded and unfunded structures
5. **Oracle Integration**: Event-based and price-based payment execution

**Applications Built on Building Blocks:**
- **Bonds**: Debt instruments implemented using Contracts with coupon and principal payment streams
- **Loans**: Lending structures implemented using Contracts with repayment schedules
- **Escrows**: Conditional release accounts implemented using Intelligent Accounts with release policies
- **Progress Payments**: Milestone-based payments implemented using Contracts with oracle-triggered releases
- **Asset Backed Securities**: Securitized pools implemented using Contracts bundling multiple underlying assets
- **Corporate Treasury Manager**: Treasury management implemented using Intelligent Accounts with spending policies and fund segregation
- **Supply Chain Financing**: Invoice and purchase order financing implemented using Contracts with early payment options
- **Funds and SPV Balance Sheet Manager**: Policy-based payments and distributions for funds and SPVs using Intelligent Accounts
- **Tokenized Credit Facilities**: Credit lines implemented using Intelligent Accounts with policy-based drawdown rules
- **Investor Callable Accounts**: On-demand withdrawal accounts implemented using Intelligent Accounts with withdrawal policies

**Key Advantages:**
- **No Counterparty Risk During Construction**: Self-referential structures
- **Atomic Settlement**: Simultaneous execution eliminates settlement risk
- **Programmable Conditions**: Time-based and event-based unlocks
- **Transferability**: Contracts are transferable and can be traded
- **Confidentiality**: Amounts and balances are encrypted

**Common Use Cases:**
- Bonds (via Contracts)
- Loans (via Contracts)
- Escrows (via Intelligent Accounts)
- Progress Payments (via Contracts)
- Asset Backed Securities (via Contracts)
- Corporate Treasury Management (via Intelligent Accounts)
- Supply Chain Financing (via Contracts)
- Funds and SPV Balance Sheet Management (via Intelligent Accounts)
- Structured products
- Repurchase agreements
- Employee compensation
- Royalty agreements
- Segregated fund management
- Tokenized credit facilities (via Intelligent Accounts)
- Investor callable accounts (via Intelligent Accounts)

For technical implementation details, refer to:
- [Contracts Documentation](./04-CONTRACTS.md)
- [Payments Documentation](./05-PAYMENTS.md)
- [Swaps Documentation](./06-SWAPS.md)

