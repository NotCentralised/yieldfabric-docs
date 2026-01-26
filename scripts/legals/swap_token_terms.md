SWAP & TOKEN OPERATION TERMS (ANNEX)

(Enhanced Tokenised Operations and Deterministic Execution — Acacia Trust Framework)

⸻

# Swap and Token Operation Terms
## Annex to Information Memorandum

Capitalised terms used in this Annex and not otherwise defined have the meanings given in the Common Definitions Schedule.

### 1. Purpose

1.1 These terms govern all token-based, smart-contract, and programmatic operations conducted under or in connection with any Trust in the NotCentralised Acacia Trust Structure, including the Structured Issuer Trust, Invoice Collateral Trust, and AUD YieldFabric Cash Trust.

1.2 These terms form part of and are contractually binding on all signatories to the:
	•	Trust Deed;
	•	Investment Management Agreement (IMA);
	•	Collateral Security Deed;
	•	Subscription and Purchase Agreements; and
	•	Credit Facility Deed Poll.

1.3 In the event of any inconsistency between these terms and the above documents, the legal documents prevail, except where these terms provide for settlement finality or disaster recovery, in which case these terms prevail to preserve the integrity of digital operations.

⸻

2. Definitions

Key terms used herein are defined in Schedule 1.

Additional definitions:
	•	Operation means any on-chain function or sequence executed via authorised smart contracts.
	•	Smart Contract Registry means the canonical index of active contract addresses authorised by the Trustee and Manager.
	•	Authorised Signers means designated multi-signature keyholders approved by the Trustee.
	•	Ledger Event means a verified on-chain transaction hash recorded as an auditable event in the Trust’s registry.
	•	Failover Mode means a temporary state of manual or semi-automated operation initiated upon a system failure.

⸻

3. Legal Recognition of Digital Operations

3.1 Each Token Operation executed via an Authorised Smart Contract is deemed to:
	•	be made on behalf of the Trustee or Manager as applicable;
	•	be legally binding and final once recorded on the canonical blockchain;
	•	constitute electronic execution and delivery under the Electronic Transactions Act 1999 (Cth); and
	•	satisfy any requirements for writing, signature, or delivery under the governing agreements.

3.2 The canonical blockchain for purposes of this Annex shall be the one designated by the Trustee (see clause 16).

3.3 Each Transaction Hash recorded in the Smart Contract Registry shall constitute conclusive evidence of that action and its timestamp.

⸻

4. Authorised Smart Contracts

4.1 All operations must be executed only through Authorised Smart Contracts approved and whitelisted by the Trustee and Manager.

4.2 Each contract must:
	•	have undergone independent code audit and regression testing;
	•	include immutable version and governance metadata;
	•	support multi-signature or role-based access control;
	•	be registered in the Smart Contract Registry with function identifiers, signers, and legal mapping references.

4.3 The Registry must include:

Function	Description	Legal Clause Mapping	Required Signers
Mint	Issue new tokenised units or receivables	Trust Deed cl.6.3	2 of 3 (Trustee, Manager, Auditor)
Burn	Redeem or cancel tokens	Trust Deed cl.17.3	2 of 3
Transfer	Move units or receivable tokens between wallets	Subscription Agreement cl.7	1 of 2 (Trustee or Manager)
Distribute	Allocate income/yield	Trust Deed cl.7.4	2 of 3
Freeze	Suspend wallet or token	AML/CTF Programme	2 of 3
Swap	Exchange tokens between Trusts	Annex cl.9	3 of 3


⸻

5. Key Management and Authorisation

5.1 Multi-Signature Control:
All operational wallets must employ threshold multi-signature control (minimum 2 of 3) among:
	•	Trustee key;
	•	Manager key; and
	•	Independent Auditor or Custodian key.

5.2 Key Rotation:
Keys must be rotated at least annually or immediately upon compromise.

5.3 Emergency Guardian:
A time-locked Guardian Contract (e.g., 48-hour delay) may execute emergency freeze or migration functions if majority governance fails.

⸻

6. Token Standards and Metadata

6.1 Tokens issued under these terms must conform to:
	•	ERC-20 or ERC-1400 (fungible trust units);
	•	ERC-721 or ERC-1155 (receivable or asset tokens);
	•	or any approved successor standard providing equivalent auditability.

6.2 Metadata Requirements:
Each token must include immutable metadata:
token_id, trust_id, owner_wallet, issue_date, unit_price, asset_reference, governing_law, hash_of_legal_doc, tx_hash.

6.3 Tokens representing trust units or receivables are not bearer instruments; they represent registered beneficial interests recorded by the Trustee.

⸻

7. Operation Types

Token Operations include but are not limited to:

Category	Description	Legal Reference
Minting	Issue tokens to represent units, receivables, or stable collateral	Trust Deed cl.6.3
Transfer	Move ownership of tokens between whitelisted wallets	Subscription Agreement cl.7
Swap	Exchange of one class of tokens for another (e.g., receivable token → unit token)	This Annex cl.9
Distribution	Yield or principal repayment via token or stablecoin	Trust Deed cl.7.4
Redemption	Burn or cancel token upon repayment	Trust Deed cl.17.3
Freeze/Burn	AML or sanctions control measures	AML/CTF Programme
Migration	Chain or platform transition	This Annex cl.16
Manual Settlement	Off-chain fallback operation	This Annex cl.17


⸻

8. Operational Hierarchy and Legal Mapping
	1.	Legal Instruments (Trust Deed, IMA, Credit Facility)
	2.	Platform Operations Manual (procedural specifications)
	3.	Smart Contracts (executable logic)
	4.	Ledger Records (transaction evidence)

In the event of discrepancy, hierarchy applies in the above order, unless settlement finality is required, in which case ledger state prevails.

⸻

9. Swap Operations

9.1 Purpose:
Swaps enable on-chain conversion or reallocation between token classes or Trusts (e.g., receivable token redemption into unit tokens of the Structured Issuer Trust).

9.2 Conditions:
	•	Must be executed via Authorised Swap Contract.
	•	Swap ratios and parameters must match off-chain valuation methodology verified by the Trustee.
	•	Each swap transaction must emit an event with cross-hash reference to the underlying legal documents.

9.3 Settlement:
Final upon confirmation of both tokens’ state transitions.
Ledger entries must be reconciled against Trust balance sheets.

9.4 Audit Trail:
Every swap event shall include:
swap_id, source_trust, target_trust, source_token_id, target_token_id, value, rate, timestamp, tx_hash.

⸻

10. Distribution Operations

10.1 The Distribution Contract shall automatically compute distributions in accordance with the Trust’s income waterfall (Trust Deed cl.7.4).

10.2 Distributions may be made in:
	•	stablecoin (A$DC or equivalent); or
	•	unitised yield tokens (auto-reinvested).

10.3 Distribution logs must reconcile to monthly NAV statements.
Audit evidence = distribution_id + transaction hash + investor snapshot block.

⸻

11. Compliance and AML Integration

11.1 All wallets must be whitelisted through KYC/AML screening before participating.

11.2 The Freeze Contract may be invoked to:
	•	suspend or burn tokens linked to sanctioned wallets;
	•	prevent onward transfer pending investigation.

11.3 Invocations require dual signatures (Trustee + Compliance Officer) and are recorded in the Sanctions Ledger (off-chain mirror for AUSTRAC reporting).

11.4 The Platform must maintain an immutable AML Activity Log for seven years.

⸻

12. Finality, Reversal, and Error Handling

12.1 Finality:
A Token Operation is final and irrevocable once included in a validated block of the canonical blockchain.

12.2 Administrative Reversal:
Permitted only if:
	•	approved by both Trustee and Manager;
	•	Auditor concurrence obtained;
	•	reversal executed via authorised “ReverseTx” contract with cross-reference to original transaction hash; and
	•	all affected Unitholders notified.

12.3 Error Logs:
All failed or reverted transactions must be logged, reconciled, and reported in monthly operational reports.

⸻

13. Failover and Manual Settlement

13.1 Trigger:
Initiated if smart-contract execution or network integrity is compromised.

13.2 Procedure:
	•	Activate Failover Mode via emergency governance contract.
	•	Freeze further token operations.
	•	Switch to manual processing using reconciled ledgers and bank or stablecoin balances.
	•	Trustee to approve each manual payment.

13.3 Audit Trail:
Manual settlements must be hashed and appended to the ledger upon system recovery.

⸻

14. Oracles and External Dependencies

14.1 Oracles used for pricing, interest, and exchange rates must:
	•	be from verified sources;
	•	use multi-source aggregation;
	•	have fallback values in case of failure.

14.2 Any oracle malfunction or price deviation >2% must be automatically flagged to Trustee and Manager.

⸻

15. Governance and Upgrades

15.1 Upgrades to smart contracts or operational parameters require multi-signature authorisation (Trustee + Manager + Auditor).

15.2 All upgrades must be:
	•	audited before deployment;
	•	version-controlled in the Smart Contract Registry;
	•	announced to investors at least 7 days before activation; and
	•	recorded in the on-chain Change Log.

15.3 Investors may challenge an upgrade by majority vote before activation.

⸻

16. Forks and Migration

16.1 In the event of a blockchain network fork, the Trustee designates the canonical chain.
Only tokens and records on that chain remain valid.

16.2 In a migration, all token balances and metadata will be snapshotted and re-issued on the successor chain.
Migration audit file includes all transaction hashes, balances, and investor addresses.

⸻

17. Dispute Resolution

17.1 Any operational or on-chain dispute shall first be referred to the Trustee for reconciliation.

17.2 If unresolved, disputes shall proceed to mediation in Sydney under the Resolution Institute Rules.

17.3 For technical disputes (e.g., contract execution anomaly), an independent Blockchain Forensics Expert may be appointed jointly by the Trustee and Manager.

⸻

18. Liability and Indemnity

18.1 The Trustee and Manager are not liable for any loss arising from blockchain network failure, oracle malfunction, or third-party infrastructure outage, provided they acted in good faith.

18.2 Each Party indemnifies the others for losses arising from unauthorised operations, key misuse, or breach of these terms.

⸻

19. Recordkeeping and Audit

19.1 The Platform must maintain:
	•	comprehensive operation logs;
	•	hash-linked evidence of every transaction;
	•	daily reconciliations with Trust records;
	•	audit snapshots at month-end.

19.2 Independent audit of smart contracts and operational events must occur annually and be made available to investors and regulators.

⸻

20. Governing Law

This Annex is governed by and construed in accordance with the laws of New South Wales, Australia, and all disputes are subject to the exclusive jurisdiction of its courts.

⸻

Schedule 1 — Definitions

Term	Meaning
Authorised Smart Contract	A verified and whitelisted contract approved under these Terms
Blockchain	The authorised distributed ledger designated by the Trustee
Canonical Chain	The chain recognised by the Trustee for record finality
Failover Mode	A manually controlled operational state during system outage
Ledger Event	A recorded on-chain transaction linked to a legal right or obligation
Mint, Burn, Swap, Freeze, Distribution, Migration	Operations as defined under these Terms
Platform	The YieldFabric operational environment or approved successor
Registry	The authoritative register of smart contract addresses and transactions
Trust	Any trust within the Acacia Trust Structure
Wallet	A digital address authorised by the Trustee for participation


⸻

Schedule 2 — Operational Control Matrix

Operation	Required Signers	Audit Required	Recovery Allowed	Legal Reference
Mint Units	Trustee + Manager	Yes	Yes (ReverseTx)	Trust Deed cl.6.3
Burn Units	Trustee + Auditor	Yes	No	Trust Deed cl.17.3
Distribution	Manager + Trustee	Yes	Yes	Trust Deed cl.7.4
Freeze	Trustee + Compliance Officer	Yes	Yes	AML/CTF Programme
Swap	Trustee + Manager + Auditor	Yes	No	Annex cl.9
Oracle Update	Manager	Yes	Yes	Annex cl.14
Upgrade	3 of 3	Yes	Yes	Annex cl.15
Manual Settlement	Trustee	Yes	N/A	Annex cl.13


⸻

Schedule 3 — Smart Contract Registry Template

Contract Name	Version	Address	Function	Governance Keys	Audit Hash	Date Effective
UnitToken	v1.0	0x…	ERC-20 Issue	Trustee, Manager	QmHash1	[●]
ReceivableNFT	v1.0	0x…	ERC-721 Asset Token	Trustee, Manager	QmHash2	[●]
DistributionContract	v1.1	0x…	Payout Waterfall	Trustee, Manager	QmHash3	[●]
FreezeContract	v1.0	0x…	AML Freeze	Trustee, Compliance	QmHash4	[●]
SwapRouter	v1.0	0x…	Token Swaps	3 of 3	QmHash5	[●]