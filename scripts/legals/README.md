# YieldFabric Structured Receivables – Legal Pack Overview

This directory houses the draft legal instruments supporting the YieldFabric structured receivables investment programme. The materials outline the contractual lifecycle from origination of the invoice receivable through tokenised issuance, collateralisation, capital deployment, and ongoing investor governance. The Common Definitions Schedule provides shared terminology referenced across the pack.

## 1. Transaction Lifecycle (Legal Narrative)
1. **Invoice origination and acceptance** – The Originator documents the receivable, the payer provides enforceable acceptance, and a corresponding `invoice_token` is minted for transfer to the Trust.
2. **Tokenised capital stack issuance** – The Issuer creates the `investment_token`, `credit_token`, and `collateral_token`, each conferring defined economic, credit, or collateral rights within the Trust structure.
3. **Membership and governance controls** – Tokens are associated with issuer or collateral group memberships, ensuring that only authorised, KYC-cleared participants can trigger platform operations or exercise rights.
4. **Investor funding and allocation** – Wholesale investors contribute capital and enter into a swap with the Issuer, receiving the `investment_token` and the attendant right to issuer account distributions.
5. **Collateral binding** – A dedicated swap aligns the `credit_token` with the `collateral_token`, pairing the revolving facility with pledged collateral assets and locking in security interests.
6. **Capital deployment and factoring** – The Originator factors the invoice at the agreed advance rate; a composed operation disburses proceeds and transfers the `invoice_token` into the collateral account to secure investor exposure.
7. **Capital call and distribution mechanics** – Throughout the investment term, instant transfers and `accept_all` operations facilitate capital calls, reconciliations, and cash distributions, while updating token state to reflect entitlements.

## 2. Document Map and Purpose
- **information_memorandum.md** – Primary disclosure document describing the lifecycle above, token architecture, risk factors, fees, and investor eligibility conditions.
- **subscription_agreement.md** – Contractual terms governing investor commitments, representations, wallet control acknowledgements, funding obligations, and transfer restrictions.
- **trust_deed.md** – Constitutive instrument for the Trust, covering beneficiary definitions, trustee powers (including wallet governance), distribution mechanics, and termination procedures.
- **investment_management_agreement.md** – Appointment of the Manager with duties covering credit diligence, smart contract governance, reporting, and security controls.
- **invoice_purchase_agreement.md** – Receivable sale terms between Originator and Trust, including token minting obligations, metadata integrity warranties, and servicing covenants.
- **collateral_security_deed.md** – Security interest over receivables, collateral accounts, and associated NFTs, with procedures for perfection, enforcement, and token custody.
- **credit_deed_poll.md** – Terms of the revolving credit facility linked to the `credit_token`, detailing drawdown mechanics, conditions precedent, covenants, and default remedies.
- **swap_token_terms.md** – Annex defining the smart-contract operations, identity controls, custodial standards, and continuity procedures governing swaps and token transfers.
- **aml_ctf_program.md** – AML/CTF framework adapted for tokenised instruments, including wallet verification, blockchain analytics, and Travel Rule compliance.
- **privacy_notice.md** – Data handling statement aligned with Australian Privacy Principles, addressing ledger metadata, custody telemetry, and breach notification.
- **common_definitions_schedule.md** – Harmonised glossary of capitalised terms used throughout the legal pack.
- **investment.md / invoice.md / credit.md / collateral.md** – Concise summaries of each tokenised instrument’s legal effect and lifecycle role.

## 3. Using the Pack
1. **Structuring and disclosure** – Begin with the Information Memorandum to understand the investment lifecycle and associated risks before tailoring deal-specific terms.
2. **Investor onboarding** – Deploy the Subscription Agreement alongside the Trust Deed to admit wholesale investors, confirm eligibility, and register wallets.
3. **Asset acquisition** – Execute the Invoice Purchase Agreement, Collateral Security Deed, and Credit Deed Poll when purchasing receivables and establishing secured credit support.
4. **Operational alignment** – Coordinate with the Investment Management Agreement and Swap/Token Terms to ensure technology controls, smart contract authority, and reporting processes are in place.
5. **Compliance and privacy** – Implement the AML/CTF Programme and Privacy Notice ahead of launch to satisfy AUSTRAC and APP obligations.

## 4. Next Steps / Outstanding Actions
- Populate placeholders (party names, ACNs, facility limits, fee percentages, dates) prior to circulation.
- Harmonise defined terms across documents and establish a version-controlled register.
- Commission Australian legal review covering enforceability, token treatment, and cross-border considerations.
- Align operational runbooks (key management, transaction approval workflows, incident escalation) with the obligations captured in these documents.

This overview is intended to orient legal, compliance, and product stakeholders as they finalise the structured receivables investment documentation.
