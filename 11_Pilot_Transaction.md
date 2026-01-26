# Smart Contract-Enabled Securitisation of Collateralised Loans

**Author:** Arturo Rodriguez

## Introduction

This report examines the application of blockchain-based tokenisation to structured finance, with a particular focus on securitisation and the execution of commercial and capital flows.

Traditional structured finance transactions rely heavily on legal recourse, discretionary approvals, and manual operational processes at each stage of the transaction lifecycle. Capital calls, redemptions, collateral substitutions, loan drawdowns, and settlements are typically executed through notices, instructions, and confirmations between multiple parties, introducing delay, operational risk, and uncertainty despite well-defined legal frameworks.

This study investigates whether programmable blockchain infrastructure can be used to streamline these workflows by embedding rights and obligations directly into on-chain logic. Rather than replacing legal frameworks, the approach examined seeks to reduce the frequency with which legal enforcement is required by enabling deterministic execution of agreed commercial outcomes.

The report analyses a securitisation-style structure involving collateralised loans executed on a public, programmable blockchain. It evaluates how smart contract–enabled accounts, cryptographic access controls, and atomic settlement can be used to:

- Reduce operational friction in capital deployment and repayment flows
- Improve certainty of execution and settlement finality
- Preserve appropriate separation of roles such as investor, issuer, collateral holder, and borrower
- Support confidentiality and third-party auditability through cryptographic techniques such as zero-knowledge proofs

## Research Scope and Questions

This report is scoped to the study of private structured transactions and does not attempt to address public market issuance, secondary market liquidity, or retail participation.

The research is guided by the following questions:

- To what extent can cryptographic enforcement substitute for discretionary legal enforcement in structured finance workflows?
- How does tokenisation affect the execution of credit facilities, investor withdrawals, and collateral control within a securitisation-style structure?
- Can atomic, multi-party settlement support the separation of custody, control, and economic exposure required in structured finance without introducing settlement or counterparty risk?
- What operational and risk-management implications arise from executing these flows on a public blockchain?

## Transactional Flow

The transaction lifecycle is executed entirely on-chain using atomic swaps, token-based permissions, and smart contract–controlled accounts. Each step replaces discretionary or manual processes with cryptographically enforced rights.

### 1. Investor Funding

The transaction begins with investor funding.

The Investor Account acquires an Investment Token (IT) by entering into an atomic swap with the Issuer Account. In this swap, the investor transfers 10,000 units of tokenised AUD to the Issuer Account and receives 1 Investment Token in return.

Upon completion:

- The Issuer Account holds the tokenised AUD.
- The Investor holds the Investment Token.
- The Investment Token cryptographically grants the investor the right to withdraw funds directly from the Issuer Account at any time, without requiring issuer approval or off-chain coordination.

This establishes investor funding while embedding withdrawal rights directly into the token rather than relying on contractual discretion.

### 2. Collateral Binding

Following funding, the issuer establishes the credit structure through collateral binding.

The Issuer Account atomically exchanges a Credit Facility Token (CRT) for a Collateral Token (CT) with the Collateral Account. This swap cryptographically links the Issuer and Collateral Accounts.

As a result:

- The Collateral Account receives the Credit Facility Token.
- The Issuer Account receives the Collateral Token.
- The Credit Facility Token grants its holder cryptographic authority to withdraw funds from the Issuer Account, functioning as an on-chain credit line.
- The Collateral Token grants its holder cryptographic authority to withdraw assets from the Collateral Account.

The credit facility is therefore established entirely through token-based permissions rather than legal instructions or mandates.

### 3. Origination Deployment

The Collateral Account deploys capital into a loan origination using the Credit Facility Token.

The Collateral Account withdraws 5,000 units of tokenised AUD from the Issuer Account under its cryptographic authority. These funds are then used to enter into an atomic swap with the Borrower Account.

Under this swap:

- The Borrower receives 5,000 units of tokenised AUD.
- The Collateral Account receives a Loan Token representing the borrower's repayment obligation, and a digital asset used as loan collateral.

Following origination:

- The Borrower holds liquidity and a Loan Token obligation.
- The Collateral Account holds both the Loan Token and the digital asset securing the loan.

### 4. Investor Capital Call (Partial)

At any point, the investor may exercise withdrawal rights.

Using the cryptographic permissions embedded in the Investment Token, the Investor Account directly withdraws 5,000 units of tokenised AUD from the Issuer Account.

This withdrawal:

- Is unilateral and does not require issuer consent.
- Does not impact the loan, as deployed capital is isolated within the Collateral Account.
- Reduces the Issuer Account balance while preserving the credit structure.

This demonstrates investor liquidity through cryptographic enforcement rather than discretionary redemption processes.

### 5. Repurchase

Upon loan repayment or repurchase, the Borrower Account initiates settlement.

The Borrower enters into an atomic swap to repurchase:

- The Loan Token, and
- The digital asset previously pledged as collateral.

The Borrower transfers 5,000 units of tokenised AUD, which are received by the Collateral Account.

Using the Collateral Token's cryptographic authority, the Collateral Account transfers these funds back to the Issuer Account.

At this stage:

- The loan is extinguished.
- The borrower regains ownership of the collateral.
- Liquidity is returned to the issuer.

### 6. Final Investor Capital Call

Following loan repayment, the investor completes withdrawal of remaining capital.

The Investor Account uses the Investment Token to withdraw the remaining 5,000 units of tokenised AUD from the Issuer Account.

Once this withdrawal is completed:

- The Issuer Account balance is reduced to zero.
- All credit exposure has been settled.
- The Investment Token has fully exercised its economic rights.

The transaction lifecycle concludes with all obligations satisfied and no residual discretionary claims remaining.

## Tokenised Assets

All assets and representations of value within the structure are tokenised and implemented using ERC‑20 or ERC‑721 smart contracts. Each token functions as a cryptographic instrument that encodes specific economic rights or control permissions, replacing discretionary or manual processes with deterministic on‑chain execution.

### Investment Token (ERC‑721)

The Investment Token represents the investor's economic interest in the structure and confers:

- Entitlement to distributions generated by the Issuer Account.
- Cryptographically enforced authority to withdraw funds directly from the Issuer Account, without reliance on contractual requests or issuer discretion.

### Credit Facility Token (ERC‑721)

The Credit Facility Token represents an on‑chain credit line and confers:

- Cryptographically enforced authority to withdraw funds from the Issuer Account in accordance with the credit facility parameters.

### Collateral Token (ERC‑721)

The Collateral Token represents control over collateralised assets and confers:

- Cryptographically enforced authority to withdraw assets held within the Collateral Account.

### Loan Token (ERC‑721)

The Loan Token represents the borrower's repayment obligation and confers:

- The cryptographic right to receive programmed credit repayments generated by the loan over its lifecycle.

### Payment Token (ERC‑20)

The Payment Token represents a programmable payment instrument fully backed by Central Bank Digital Currency (CBDC).

For each unit of Payment Token in circulation, an equivalent unit of CBDC is held in escrow, ensuring full backing and settlement finality.

## Intelligent Accounts

Intelligent Accounts are smart contract–controlled accounts whose behaviour is embedded directly within the account smart contract itself. Token ownership confers specific cryptographic rights that the account logic enforces deterministically, enabling control over assets without discretionary instruction or manual approval.

### Investor

- Holds the Investment Token, representing the investor's economic interest in the structure.
- Exercises cryptographically enforced authority to withdraw funds directly from the Issuer Account.
- Controlled by Beachhead Venture Capital.

### Issuer

- Holds the Collateral Token and all undeployed cash‑equivalent tokens.
- Exercises cryptographically enforced authority, via the Collateral Token, to withdraw assets from the Collateral Account.
- Acts as the structural issuer of the transaction.
- Controlled by Perpetual Trustees.

### Collateral Account

- Holds the Credit Facility Token, enabling access to the Issuer Account under the credit facility.
- Holds originated Loan Tokens representing borrower obligations.
- Holds the digital assets pledged as collateral for the loans.

### Borrower

- Holds the Loan Token representing its repayment obligation.
- Holds the digital asset used to collateralise the loan.

## Confidential Execution Framework

The transaction structure relies on a confidential execution framework designed to support private yet programmable financial interactions on a public blockchain. This framework is composed of two core components: a confidential vault for controlled asset custody and execution, and a confidential swap mechanism for atomic settlement.

### Confidential Vault

The Confidential Vault is a smart contract–based account that holds assets on behalf of a role within the structured finance arrangement (for example, issuer, collateral holder, or investor). The vault enforces programmable rules governing how assets may be accessed, transferred, or encumbered.

Rather than exposing balances, transaction logic, or counterparties publicly, the vault operates with confidentiality guarantees that restrict observable information to authorised participants and permitted auditors. Asset movements and state transitions are executed according to predefined conditions embedded in the vault's smart contract logic.

Key characteristics of the Confidential Vault include:

- Programmable custody, where control over assets is governed by deterministic rules rather than discretionary instructions.
- Role separation, enabling custody, control, and economic exposure to be allocated across distinct parties without commingling assets.
- Confidential state management, allowing balances and transactional intent to remain private while still enabling verification of correct execution.
- Auditability, where third parties can verify compliance with contractual constraints using cryptographic proofs without requiring full data disclosure.

Within the structured finance context, the confidential vault functions analogously to a trustee or custodian account, but with behaviour enforced directly by on-chain logic rather than operational processes.

### Confidential Atomic Swap

The Confidential Atomic Swap is a settlement mechanism that enables assets to be exchanged atomically between multiple parties under confidentiality constraints. The swap ensures that either all legs of a transaction execute simultaneously, or none do, eliminating settlement and counterparty risk.

In the context of this structure, confidential atomic swaps are used to:

- Exchange funding for investment tokens during investor onboarding.
- Deploy capital against loan and collateral tokens during origination.
- Repurchase loan and collateral positions upon repayment.

The swap mechanism supports multi-party settlement, allowing assets to move safely between three or more independent parties while preserving the separation of custody and control required in structured finance arrangements. Execution is conditional on all required parties satisfying the cryptographic conditions of the swap, ensuring deterministic settlement outcomes.

By combining confidential vaults with confidential atomic swaps, the framework enables private, programmable execution of complex financial workflows on a public blockchain, materially reducing reliance on bilateral trust, manual reconciliation, and legal enforcement at each transactional step.

## Use of Zero-Knowledge Proofs

Zero-knowledge proofs are used within the confidential execution framework to reconcile the requirement for transactional privacy with the need for correctness, enforceability, and auditability.

Rather than revealing balances, counterparties, or transactional intent on-chain, the smart contracts governing confidential vaults and swaps rely on zero-knowledge proofs to verify that required conditions have been satisfied. These proofs allow a party to demonstrate compliance with predefined rules, such as sufficient balance, valid token ownership, or adherence to transaction constraints, without disclosing the underlying private data.

Within the smart contract logic:

- Zero-knowledge proofs are verified on-chain to confirm that a proposed state transition is valid under the vault or swap rules.
- Proof verification acts as a gatekeeper for execution, ensuring that asset movements occur only when all cryptographic conditions are met.
- The contracts do not store or expose sensitive transactional data; instead, they store verification keys and enforce outcomes based on proof validity.

This approach allows confidential transactions to be executed deterministically on a public blockchain while limiting observable information to what is strictly necessary for consensus and settlement. At the same time, authorised third parties may be provided with appropriate proof artefacts to support independent audit or regulatory review without requiring full disclosure of transaction-level data.

## Conclusion

This report has examined the application of blockchain-based tokenisation to a securitisation-style structure involving collateralised loans, with a focus on the execution of commercial and capital flows rather than the creation of new financial instruments.

The analysis demonstrates that programmable blockchain infrastructure can materially streamline structured finance workflows by embedding rights and obligations directly into on-chain logic. Mechanisms such as smart contract–controlled accounts, cryptographically enforced access rights, confidential execution frameworks, and atomic multi-party settlement enable deterministic execution of actions that are traditionally reliant on discretionary approvals and legal processes.

Importantly, the approach studied does not seek to replace existing legal frameworks or fiduciary roles. Instead, it illustrates how cryptographic enforcement can reduce the operational frequency with which legal recourse is required, while preserving role separation, custody integrity, and settlement finality. Legal arrangements remain essential for establishing rights, governance, and remedies, but their day-to-day operational invocation may be reduced through programmable execution.

The use of confidential vaults, atomic settlement, and zero-knowledge proofs demonstrates that it is possible to reconcile transactional privacy with the requirements of correctness, enforceability, and auditability on a public blockchain. This has particular relevance for structured finance arrangements, where confidentiality and role separation are critical, and where operational complexity often introduces risk and cost.

From a market infrastructure perspective, the study suggests that tokenisation may be most impactful when applied to execution mechanics rather than instrument design. By focusing on how capital is deployed, controlled, and settled blockchain-based systems may offer a path to more resilient, transparent, and efficient financial workflows.

Further research is required to assess scalability, governance models, and regulatory alignment, as well as the interaction between on-chain execution and off-chain legal enforcement under stress scenarios. However, the mechanisms examined in this report indicate that blockchain-based execution frameworks warrant serious consideration as complementary infrastructure for future structured finance and capital market systems.
