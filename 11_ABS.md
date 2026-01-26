# Asset-Backed Securities (ABS)

## Introduction

This document has been prepared to support a **digital twin exercise** for the Wisr Freedom Trust 2025-1 transaction, conducted within NotCentralised's Smart ABS participation in the Reserve Bank of Australia's **Project Acacia**. The objective of the project is to model the full lifecycle of the ABS using **tokenisation methods and the YieldFabric framework**, in order to better understand how digital representations of assets, cashflows and states can improve the efficiency, transparency and control of securitisation operations.

Our approach combines **private tokenisation** with **state-machine representation** of the ABS, leveraging **zero-knowledge proofs** and **smart contracts**. This hybrid approach enables auditability through selective disclosure, rule integrity through smart contracts, and privacy through zero-knowledge proofs.

The blockchain serves as the **integrity layer**, ensuring that both data and state changes can only occur when they comply with rules encoded in the smart contracts. Since smart contracts are incorruptible, this achieves a very high level of efficiency and trust in the lifecycle management of the product. The benefits of state-machine representations include:

* **Auditability through selective disclosure**: Sensitive data remains private, while specific properties or assertions can be proven without revealing underlying information
* **Rule integrity through smart contracts**: Waterfall logic, payment priorities, and transaction rules are encoded as deterministic smart contract logic that cannot be altered or bypassed
* **Privacy through zero-knowledge proofs**: Loan-level data, investor positions, and cashflow details remain confidential while enabling verification of compliance and correctness

The digital twin does **not** seek to change the legal structure, economic characteristics, cash custody arrangements or fiduciary responsibilities of the transaction. Instead, it mirrors the existing ABS structure and processes, representing them as verifiable digital states that can be observed, audited and reconciled more efficiently.

The primary goal of this exercise is to:

* Map the end-to-end lifecycle of the ABS (origination, funding, repayment, waterfall calculation and note distributions) into explicit, state-driven representations
* Assess how tokenisation can reduce operational friction, reconciliation effort and evidentiary risk
* Demonstrate how YieldFabric can act as a confidential verification and coordination layer over existing trustee, administrator and banking arrangements

This document therefore combines a traditional ABS structural description with an overlay explaining how a digital twin approach can enhance lifecycle management, without altering the legal, regulatory or economic foundations of the transaction.

---

## Transaction Overview

**Issuer:** AMAL Trustees Limited, as trustee of the Wisr Freedom Trust 2025-1
**Asset Class:** Australian consumer loan receivables
**Structure:** Bankruptcy-remote trust issuing multiple classes of asset-backed notes
**Purpose:** Funding the acquisition of a pool of receivables originated by Wisr Finance Pty Ltd, with cashflows used to service noteholder obligations

---

## Key Transaction Parties

* **Originator / Seller:** Wisr Finance Pty Ltd
* **Issuer / Trustee:** AMAL Trustees Limited
* **Trust Manager:** AMAL Management Services Pty Ltd
* **Arranger & Lead Manager:** National Australia Bank Limited
* **Servicer:** Wisr Finance Pty Ltd (with standby servicing arrangements)

Each party has a ring‑fenced role, reducing commingling and operational risk.

---

## Capital Structure (Tranching)

The transaction employs a traditional sequential-pay, multi‑tranche capital structure designed to allocate credit risk, duration risk, and return across investor classes. The notes are issued by the Issuer and are limited‑recourse obligations backed solely by the trust assets.

* **Senior Notes (Class A)** – A$185.0 million, expected rating **Aaa(sf)**, with an initial margin of approximately **1.15%**. Class A benefits from the full subordination of all junior tranches, excess spread, and liquidity support, and is intended to be eligible for repo transactions with the Reserve Bank of Australia, subject to approval.

* **Mezzanine Notes (Classes B–D)** – Investment‑grade tranches providing graduated risk‑return exposure:

  * **Class B:** A$19.76 million, **Aa2(sf)**, ~1.35% margin
  * **Class C:** A$12.50 million, **A2(sf)**, ~1.60% margin
  * **Class D:** A$7.00 million, **Baa2(sf)**, ~1.80% margin
    These notes provide credit support to the senior class while benefiting from subordination of the junior tranches.

* **Subordinated / Junior Notes (Classes E–F)** – Below investment grade tranches designed to absorb higher expected losses in return for increased yield:

  * **Class E:** A$12.00 million, **Ba2(sf)**, ~3.50% margin
  * **Class F:** A$4.50 million, **B2(sf)**, ~4.50% margin

* **Residual / Seller Notes (Classes G1 & G2)** – Unrated tranches (A$5.50 million and A$3.74 million respectively) that represent the residual economic interest in the transaction. These tranches typically receive distributions only after all rated note obligations have been satisfied and are commonly retained to align the originator with asset performance.

All note classes share a common legal maturity date of **December 2034**. Principal and interest are paid in accordance with the transaction's priority of payments, with principal applied sequentially from senior to junior tranches unless otherwise directed by transaction triggers.

---

## Cashflow Waterfall

Collections from the receivables pool are applied on each determination date in accordance with a strictly defined priority of payments set out in the Transaction Documents. All payments are limited‑recourse and payable solely from available trust income and principal collections.

1. **Senior trust expenses and taxes** – Trustee fees, trust manager fees, security trustee costs, audit expenses, regulatory costs, and any applicable taxes or statutory charges.
2. **Liquidity facility drawings and costs** – Reimbursement of any amounts drawn under the liquidity facility, together with commitment fees and accrued interest, ensuring continuity of senior interest payments during temporary collection shortfalls.
3. **Hedging amounts** – Net amounts payable to the hedging counterparty under the interest rate hedge to manage basis and interest rate mismatch risk.
4. **Interest on Class A Notes** – Accrued and unpaid interest on the senior notes is paid in full before any principal allocation to junior tranches.
5. **Sequential principal repayment** – Principal collections are applied sequentially to reduce the outstanding balance of the notes, starting with Class A and progressing through Classes B to F, subject to performance and trigger conditions.
6. **Interest and principal on mezzanine notes (Classes B–D)** – Interest and, once senior obligations are satisfied, principal payments to the mezzanine tranches in order of seniority.
7. **Interest and principal on subordinated notes (Classes E–F)** – Payments to subordinated tranches after all senior and mezzanine obligations have been met.
8. **Residual distributions** – Any remaining excess spread or residual income is distributed to the unrated residual notes (Classes G1 and G2), representing the retained economic interest in the transaction.

The waterfall is designed to prioritise liquidity and credit protection for senior noteholders, with structural subordination, excess spread and liquidity support absorbing performance volatility before impacting senior tranches.

---

## Credit Enhancement

Credit support for senior and mezzanine tranches is provided through a combination of structural, cashflow and contractual mechanisms embedded in the Transaction Documents:

* **Subordination:** Losses arising from defaults, write‑offs or realised principal deficiencies are allocated first to the most junior tranches (Classes G, then F, E, D, C, B), preserving the principal balance and interest payments of senior notes for as long as possible.

* **Excess spread:** The weighted average interest rate on the underlying loan receivables exceeds the aggregate cost of funds (note coupons, hedge costs and senior expenses). This surplus income provides a first layer of loss absorption and can be redirected, if required, to cure principal deficiencies or support senior payments.

* **Liquidity facility:** A committed liquidity facility is available to cover temporary mismatches between borrower collections and required senior payments. Drawings may be used to ensure timely payment of senior note interest and certain senior costs, with amounts drawn ranking senior in the waterfall and repayable from future collections.

* **Structural protections and triggers:** Credit quality is further protected through asset eligibility criteria, concentration limits, servicing covenants, arrears and loss performance triggers, and step‑down conditions. Breach of these tests can restrict principal distributions to junior notes, redirect excess spread, or prevent optional redemption, thereby preserving credit enhancement for senior and mezzanine investors.

---

## Origination Process

The origination and servicing workflow follows a closed-loop value chain from borrower application through to investor payment, with clear separation of duties and controlled cash movements:

1. **Loan application and credit assessment** – Borrowers apply for personal loans through Wisr's digital channels. Applications are processed via Wisr's proprietary **Liger** platform, which performs identity verification, credit bureau checks, fraud screening, serviceability assessment and automated decisioning in accordance with Wisr's credit policy.

2. **Loan origination and funding** – Approved loans are originated by Wisr Finance Pty Ltd. Eligible loans are sold to the Trust pursuant to the receivables sale agreement, with purchase consideration funded from note issuance proceeds. Legal title to the receivables transfers to the Trust, establishing bankruptcy remoteness.

3. **Borrower repayments and collections** – Borrowers make periodic repayments of principal and interest into the **Collections Account** held in the name of the Trust. Wisr, as Servicer, administers borrower accounts, manages arrears, hardship and recoveries, and reconciles inflows, but does not control distributions.

4. **Cash classification and ledgering** – All amounts received into the Collections Account are aggregated and classified by the Trust Manager into **principal collections** and **income collections** through accounting ledgers. No loan-by-loan earmarking occurs; cash is pooled at the trust level.

5. **Liquidity and hedging interface** – Where income collections are insufficient to meet senior obligations, the Trust Manager may direct a **Principal Draw (and, only if a Further Payment Shortfall exists, a Liquidity Facility draw)**, with funds credited to the transaction account. Hedge receipts or payments are settled in accordance with the interest rate hedge to manage basis risk.

6. **Waterfall calculation and payments** – On each determination and payment date, the Trust Manager calculates **Total Available Income** and **Total Available Principal** and applies the Income and Principal Priority of Payments. Funds are disbursed from the transaction account to pay senior expenses, hedge costs, note interest, note principal and residual distributions in strict order of priority.

7. **Ongoing reporting and oversight** – The Servicer provides loan-level and pool-level performance data to the Trust Manager and Trustee. Investor reports detail collections, arrears, principal amortisation, note balances and trigger status, ensuring transparency across the value chain.

---

## Tokenisation Approach

This section explains how the approach described in the Introduction — combining **private tokenisation** with **state-machine representation** — is implemented using YieldFabric's confidential verification and coordination framework. 

Tokenisation is used to create **registers of assets** (loan receivables) and **registers of obligations** (note entitlements), where each asset and obligation is represented as a tokenised record. These tokenised registers provide the foundation for the state-machine representation, where each token maintains its own state (balances, status, attributes) and state transitions occur through transactions encoded in smart contracts.

The **state-machine representation** models the ABS lifecycle as a sequence of states and state transitions, where each state (loan state, cash state, waterfall state, note state) is recorded on the blockchain integrity layer, and transitions between states are enforced by smart contract rules. Zero-knowledge proofs enable selective disclosure of tokenised register data, allowing verification without revealing sensitive information.

Tokenisation does not change the economic structure of the ABS. Instead, it **makes the existing structure explicit, programmable, and auditable** by representing assets and obligations as tokenised registers and state transitions as deterministic execution rules enforced by smart contracts.

---

### Conceptual Overview

This section provides a **systems‑level interpretation of the ABS**, showing that a traditional securitisation is already a **state machine** operating across multiple platforms, accounts, and calculation agents. Each participant (originator, servicer, bank, administrator, trustee) is responsible for updating a specific *state* of the transaction — loan state, cash state, waterfall state, or note state — with payments acting as state transitions.

In our tokenised approach, these states are maintained in **tokenised registers**: the register of assets tracks loan receivables (their balances, status, and attributes), while the register of obligations tracks note entitlements (principal balances, interest accruals, and payment priorities). The blockchain serves as the integrity layer, ensuring that state changes in these registers can only occur in accordance with the rules encoded in the smart contracts.

---

#### End‑to‑End System Mapping

The table below explains **who does what today** in the ABS and how tokenisation provides a **verification and coordination layer** over those existing responsibilities. Tokenisation does not replace systems or decision‑makers; it records and attests to outcomes so they can be independently verified.

| Stage | Lifecycle Step      | Who Performs the Function                     | What Happens in the ABS Today                                                                                          | How YieldFabric Represents This                                                                                      | Why This Matters to Trustees                                                                             |
| ----- | ------------------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 1     | Loan Application    | Wisr (via Liger)                              | Borrower information, credit checks and approval decisions are assessed in Wisr's origination system.                  | **Confidential Oracle** records a commitment that a valid application and approval state existed at a point in time. | Provides evidence that assets were originated in accordance with policy, without exposing borrower data. |
| 2     | Loan Origination    | Wisr Finance Pty Ltd                          | Approved loans are legally originated and later sold to the Trust.                                                     | **Confidential Obligation** represents the existence and key attributes of each loan as a private, verifiable state. | Confirms asset existence and eligibility at sale into the Trust.                                         |
| 3     | Loan Repayments     | Wisr (Servicer) and NAB (Bank)                | Borrowers repay principal and interest into the Trust's bank accounts; loan balances are updated in servicing systems. | **Payments** reflect state changes linking borrower repayments to loan and cash balance updates.                     | Creates a clear audit trail between borrower payments and trust cash receipts.                           |
| 4     | Cash Classification | Administrator (on Trust Manager instructions) | Collections are classified as income or principal in accordance with the Transaction Documents.                        | **Distribution State** records the income vs principal classification as a verified state.                           | Demonstrates correct application of waterfall inputs before payments are made.                           |
| 5     | Class Distribution  | Administrator (on Trust Manager instructions) | Calculated amounts are allocated to note classes in priority order.                                                    | **Intelligent Account** models the priority allocation logic and resulting entitlements.                             | Provides evidence that distributions follow the documented priority of payments.                         |
| 6     | Note Balances       | Administrator / Trustee                       | Note balances are reduced by principal and credited with interest after each payment date.                             | **Intelligent Account** records updated note balances as a verifiable state.                                         | Enables independent confirmation of amortisation, triggers and investor entitlements.                    |

---

### YieldFabric Primitives

The following concepts translate familiar ABS components into trustee‑safe digital representations. They are **descriptive and evidentiary**, not substitutes for legal documents or bank accounts.

| Concept                                                | What It Means in ABS Terms                                                | YieldFabric Usage                                                                                                                                                               | Trustee Relevance                                                                                                     |
| ------------------------------------------------------ | ------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Stateful digital instrument (NFT‑like abstraction)** | A loan or note position with a changing balance over time.                | Used to represent loan and note balances as private, verifiable states.                                                                                                         | Mirrors existing loan and note ledgers without changing ownership or custody.                                         |
| **Payment**                                            | Movement of cash due to borrower repayment or investor distribution.      | Captures the fact that a payment occurred and updated balances accordingly.                                                                                                     | Links cash movements to calculated entitlements and waterfall logic.                                                  |
| **Account**                                            | Trust‑controlled bank accounts (collections, transaction, note accounts). | Represented as balance states only; fiat funds remain in a limited number of trust‑controlled bank accounts, while tokenised balance representations are passed across wallets. | Reduces the need for multiple physical bank accounts while preserving trustee control and simplifying reconciliation. |
| **Oracle Log**                                         | Time‑stamped record of calculations and outcomes.                         | Stores cryptographic commitments to loan, waterfall and note states.                                                                                                            | Provides immutable evidence for audit, surveillance and dispute resolution.                                           |

---

#### Confidential Documents (Private State Representation)

Confidential Documents are cryptographic hashes generated using YieldFabric methods to represent **private, self-custodied documents and states** (for example: loan records, waterfall states, note balances, trigger evaluations).

* Each Confidential Document encapsulates a **JSON representation** of a document or state.
* The full JSON content remains **off-chain and private**.
* Using zero-knowledge proofs, specific **properties or assertions** about the JSON (e.g. balances, thresholds met, eligibility flags) can be proven **without revealing the underlying data**.

This allows sensitive loan, investor, and cashflow information to remain confidential while still being verifiable.

---

#### Confidential Oracles (On-chain Integrity and Coordination)

Confidential Oracles are used to **log commitments to Confidential Documents on-chain**. These oracle entries do not disclose the document contents but provide:

* An immutable, time-ordered record that a specific state existed at a specific point in time
* A cryptographic anchor linking off-chain calculations to on-chain execution

Critically, Confidential Oracles allow:

* **Separation of responsibilities** between calculation, disclosure, and execution
* On-chain triggers for **payments or financial actions** without requiring publication of sensitive data

This enables trustee- and administrator-controlled processes to remain off-chain, while preserving on-chain integrity and auditability.

---

#### Stateful Balances and Asset–Cash Transitions

YieldFabric tracks **stateful balances** for both loan principal and cash positions, enabling the full ABS balance sheet to be represented privately and coherently:

* Loan balances reflect amortisation, prepayments, defaults, and recoveries
* Cash balances reflect collections, liquidity draws, hedge flows, and distributions

YieldFabric supports controlled **asset–cash state transitions**, allowing:

* Conversion of loan principal into cash upon borrower repayment
* Reclassification of principal to income (e.g. Principal Draws)
* Swapping credit exposure for cash exposure while maintaining a verifiable audit trail

This allows the entire ABS state — assets, liabilities, and cash — to be tracked continuously with selective disclosure.

---

### Operational Workflows

The operational workflow expresses the ABS lifecycle as a series of **state transitions**, with clear separation between private data, on-chain integrity, and financial execution. YieldFabric introduces three core primitives — **Confidential Documents**, **Confidential Oracles**, and **Stateful Balances** — to model this lifecycle without altering legal ownership, custody, or trustee control.

---

#### End-to-End Operational Flow

The end-to-end operational flow below describes how loan origination, funding, repayment, waterfall calculation and note distributions are coordinated using YieldFabric primitives, while preserving the legal, operational and fiduciary roles described in the Transaction Documents. The diagram below illustrates how the ABS lifecycle can be represented as a sequence of verifiable state transitions.

![ABS Operational Workflow Diagram](path/to/abs-operational-workflow-diagram.png)

*Figure: End-to-end ABS operational workflow showing loan origination, Transaction block aggregation, state calculations (ABS State and Note State), sequential note distribution, and investor payments.*

Each step should be read as **descriptive of what already occurs operationally**, with YieldFabric providing a confidential verification and coordination layer rather than replacing existing parties or bank accounts.

---

* **Loan Application and Credit Assessment**
  The process begins when an applicant submits a loan application through Wisr's origination channels. Credit and identity information is obtained from multiple external data providers (including identity documentation services such as IDMatrix, credit bureau sources such as Equifax, and other identity verification services). The inputs and outcome of the assessment are summarised and committed to a **Confidential Document**, creating an **Application ID State** represented as a cryptographic hash. This hash evidences that the application was assessed in accordance with policy, without disclosing the underlying personal or credit data.

* **Loan Approval and Loan NFT Creation within Transaction**
  Where a loan is approved, a **stateful digital loan instrument (Loan NFT)** is created and stored within the **Transaction block**, which serves as the central container for the asset pool. Each Loan NFT (Loan NFT (1) through Loan NFT (n)) tracks its principal balance and is linked to the Application ID State from the assessment process. The metadata of each Loan NFT references the Confidential Document hash associated with the approved loan. Multiple borrowers contribute to the Transaction block, with each borrower's loan represented as a separate Loan NFT with its own principal balance tracking. This does not constitute public disclosure of loan information; it is a private, verifiable reference to the approved loan state.

* **Funding and Transaction Pool Formation**
  The Transaction block aggregates multiple Loan NFTs from multiple borrowers (Borrower (1) through Borrower (n)), each contributing AUD flows into the Transaction. Economically, this step represents the pooling of loan assets and the advance of loan principal. Legally and operationally, fiat funds are held in trust-controlled bank accounts; the digital representation serves to track entitlement and balances rather than custody of cash. The Transaction block maintains separate AUD pools representing the aggregate cash position of the securitisation.

* **Borrower Repayments**
  Borrowers make repayments of principal and interest into the Trust's collections and transaction accounts in AUD. Repayments are made to the holder of the loan instrument (in this case, the Originator on behalf of the Trust). As repayments occur, the outstanding loan balance is updated and committed as a new Confidential Document via the **Confidential Oracle**, creating a time-stamped record of loan performance.

* **Waterfall Calculation and ABS State**
  IQEQ, acting as calculation agent in accordance with the Transaction Documents, calculates the ABS waterfall state based on payments received into the transaction account from the Transaction block. This includes the determination of Total Available Income, Total Available Principal, and any required reallocations. The resulting **ABS State** is recorded as a Confidential Document and logged on-chain using the Confidential Oracle, providing immutable evidence that calculations were performed correctly and in sequence.

* **Note Calculation and Note State**
  IQEQ performs note-level calculations for each class, determining outstanding principal balances, interest accruals and amounts due. The resulting **Note State** is captured as a Confidential Document and logged via the Confidential Oracle. This provides a verifiable record of amortisation, interest payments and trigger status for each class.

* **Note Distribution in Sequential Priority**
  Based on both the verified **ABS State** and **Note State**, funds from the Transaction block are distributed to note classes in strict sequential priority order: **Note A** (senior tranche) receives distributions first, followed by **Note (B–F)** (mezzanine and subordinated tranches) in order of seniority, and finally **Note G** (residual tranches). Both the ABS State and Note State inform the distribution calculations, with the Transaction block providing the underlying cash flows. These allocations reflect entitlements under the priority of payments and are mirrored digitally using AUD-denominated accounting abstractions, while fiat settlement continues to occur through trust-controlled bank accounts.

* **Note Distributions to Investors**
  Using the verified note state and the sequential distribution logic, coupons, principal repayments and residual amounts are distributed from each note class to individual investors (Investor (1), Investor (3), Investor (5), through Investor (n)). YieldFabric represents this step as a deterministic allocation of amounts across noteholder wallets, with AUD flows from the notes to investors, providing assurance that each investor receives the correct payment at the correct priority, without altering custody, settlement or trustee authority.

---

**Trustee and Originator perspective:**
This model preserves existing trust law, banking arrangements and delegated authorities, while adding a cryptographically verifiable audit trail across the full ABS lifecycle — from loan application through to final investor distributions. It reduces evidentiary risk, simplifies oversight and supports audit, rating and listing processes, without introducing new custody or settlement risks.

---

#### Structural Outcome

By combining private Confidential Documents, on-chain Confidential Oracles, and stateful balance tracking, YieldFabric enables:

* Full lifecycle visibility of the ABS without public data leakage
* deterministic verification of execution of payments based on verifiable state
* Independent verification by investors, listing venues, and regulators
* A programmable yet regulator-aligned operating model

This approach preserves traditional trust, banking, and custody arrangements while expressing the ABS as a **verifiable financial state machine**.

---

## Benefits and Impact

This section consolidates the benefits and impacts of tokenisation for the ABS transaction, covering operational improvements, rating agency implications, and listing opportunities.

---

### Benefits of Tokenisation

Tokenisation transforms the ABS from a process-dependent, reconciliation-intensive structure into a deterministic, verifiable state machine. The key benefits include:

**Operational Efficiency:**

In a conventional ABS:
* State is fragmented across **multiple systems** including Wisr, NAB and IQEQ
* Cash control and logic are enforced via **process, reconciliation, and reporting**
* Investors rely on **ex‑post reports** to understand performance

Tokenisation allows these same mechanics to be expressed as:
* **Single‑source‑of‑truth state objects** (loans, notes, waterfall positions) instead of fragmented state across multiple systems
* **deterministic verification of execution** of distributions once conditions are met
* **Cryptographically verifiable audit trails** instead of periodic reconciliation

This reduces operational risk, reconciliation cost, and latency without changing legal ownership, cash accounts, or trustee control. Tokenisation removes manual reconciliation between servicer, bank, administrator and trustee systems.

**Deterministic Verification:**

* Once states are attested, distributions can be executed automatically and correctly
* Deterministic verification of execution of distributions once conditions are met

**Improved Transparency:**

* Investors can observe state changes (balances, triggers, amortisation) in near-real time
* No reliance on ex‑post reports to understand performance

**Auditability:**

* Every calculation and payment is backed by an immutable oracle log
* Complete cryptographic audit trail for regulators and auditors

**Faster Innovation:**

* Enables programmable features such as conditional calls, real-time reporting, and composable secondary markets
* Supports new features without altering trust law or custody arrangements

---

### Impact on Credit Rating and Surveillance

Tokenisation does not alter the economic risk profile, legal structure, or cashflow priority that underpin the initial credit rating of the Notes. Rating agencies would continue to assess asset quality, credit enhancement, liquidity support, counterparty risk, and legal enforceability in the same manner as a traditional ABS.

However, representing the transaction as an explicit, state-driven system can materially improve **operational and execution confidence**, particularly during ongoing surveillance:

* **Reduced operational risk:** deterministic verification of execution of waterfalls and distributions reduces reliance on manual processes and mitigates human error risk.
* **Timely payment assurance:** Explicit modelling and execution of liquidity draws, principal draws and interest payments strengthens confidence in timely payment mechanics for senior notes.
* **Enhanced surveillance:** Rating agencies can observe verified state transitions (note balances, trigger status, amortisation, principal deficiencies) rather than relying solely on periodic reports.
* **Faster review cycles:** Clear, machine-verifiable data can shorten surveillance reviews and improve responsiveness following stress or performance events.

This shifts the rating interaction from a report-based review process to a **state-based verification model**, improving transparency and robustness without changing the rating perimeter.

---

### Listed Notes and Alternative Funding Channels

Tokenisation enables ABS Notes and bonds to be **structured for listing or admission to trading**, creating additional funding and liquidity benefits beyond private placements and bilateral issuance.

Beyond secondary liquidity, tokenisation materially improves the **listing and admission process itself** by simplifying due diligence and ongoing compliance for listing venues.

#### How Tokenisation Supports Listing

Listing venues must satisfy themselves that the underlying assets, cashflow mechanics, and ongoing obligations of a securitised product operate exactly as disclosed. Tokenisation supports this process by making the ABS lifecycle **observable, testable, and auditable at a system level**.

Specifically, tokenisation allows listing venues to:

* **Verify asset existence and eligibility:** Loan-level state objects allow venues to confirm that receivables exist, meet eligibility criteria, and are correctly transferred into the trust.
* **Inspect cashflow logic:** Waterfall rules, trigger conditions, and priority of payments can be reviewed as deterministic execution logic rather than inferred from narrative disclosure.
* **Observe lifecycle behaviour:** Amortisation, trigger breaches, step-down eligibility, and principal deficiency states can be monitored as state changes rather than periodic summaries.
* **Validate distributions:** Investor payments can be matched directly to defined rules and verified against attested execution records.

This shifts listing due diligence from a reliance on static documents and ex-post reporting to **direct verification of transaction state and behaviour**.

#### Benefits for Listed ABS Funding

* **Reduced admission friction:** Clear, machine-verifiable asset and cashflow states lower the burden and risk of initial listing approval.
* **Lower ongoing compliance risk:** Continuous lifecycle visibility supports ongoing disclosure obligations and reduces the likelihood of reporting errors.
* **Improved market confidence:** Transparent, verifiable execution increases confidence for both venues and investors, supporting tighter pricing over time.
* **Scalable issuance:** Once a standardised tokenised framework is established, follow-on issues and tap transactions can be admitted more efficiently.

Taken together, listing and tokenisation transform ABS Notes from a static, document-driven funding instrument into a **continuously verifiable, market-accessible funding channel**, while preserving the same legal, credit, and cashflow fundamentals relied upon by rating agencies, trustees, and regulators.

---

## Conclusion

This document has presented a framework for tokenising the Wisr Freedom Trust 2025-1 transaction using a combination of **private tokenisation** and **state-machine representation**, leveraging zero-knowledge proofs and smart contracts. The approach creates tokenised registers of assets (loan receivables) and obligations (note entitlements), with the blockchain serving as an incorruptible integrity layer that enforces rule compliance and enables selective disclosure.

The tokenisation approach does not alter the fundamental economic, legal, or regulatory characteristics of the ABS. Instead, it provides a **digital twin** that mirrors the existing structure and processes, making them explicit, programmable, and auditable through state-driven representations. This enables operational efficiency, deterministic verification, improved transparency, and enhanced auditability while preserving privacy through zero-knowledge proofs.

The benefits extend beyond operational improvements to **structural advantages** for rating agencies, listing venues, and investors. By providing continuous visibility into transaction state and verifiable execution of waterfall logic, tokenisation shifts the interaction model from periodic reporting to real-time state verification. This enhances operational confidence and enables more efficient surveillance, due diligence, and ongoing compliance.

As an **ongoing study** conducted within NotCentralised's Smart ABS participation in the Reserve Bank of Australia's Project Acacia, this work aims to demonstrate how digital representations can improve the efficiency, transparency, and control of securitisation operations without compromising legal structures, trustee control, or regulatory compliance. The digital twin exercise will continue to evolve as we implement and test the tokenisation framework against the actual transaction lifecycle, validating the theoretical benefits described in this document through practical application.

The ultimate goal is to establish a **proven, production-ready framework** for tokenised ABS that preserves all traditional trust, banking, and custody arrangements while delivering the benefits of programmable execution, continuous verification, and cryptographic auditability. This framework has the potential to transform securitisation from a process-dependent, reconciliation-intensive structure into a deterministic, verifiable state machine that serves trustees, investors, rating agencies, and regulators more effectively.
