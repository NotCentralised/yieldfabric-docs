INVESTMENT MANAGEMENT AGREEMENT (IMA)

(Enhanced Tokenised Securitisation Version — Acacia Trust Framework)

⸻

1. Parties
	1.	Trustee: [AMAL Trustees Pty Ltd] (ABN [●]) in its capacity as trustee of the Invoice Collateral Trust (“Trustee”).
	2.	Investment Manager: NotCentralised Pty Ltd (ABN [●]) (“Manager”).
	3.	Platform Operator (Optional): YieldFabric Pty Ltd (ABN [●]) providing the distributed ledger infrastructure and operational interfaces (“Platform”).

Capitalised terms used in this Agreement and not otherwise defined have the meanings given in the Common Definitions Schedule.

⸻

2. Background

A. The Trustee has established the Invoice Collateral Trust (“Trust”) under a trust deed dated [●] (the Trust Deed).
B. The Trust’s purpose is to acquire, hold, and manage tokenised receivables and associated assets in accordance with the Trust Deed.
C. The Trustee wishes to appoint the Manager to manage the investment and operational affairs of the Trust, subject to this Agreement.
D. The Manager holds the technical, operational, and compliance expertise to execute those functions through the YieldFabric Platform and related systems.

⸻

3. Appointment

3.1 The Trustee appoints the Manager as its exclusive investment and operational manager for the Trust.

3.2 The Manager accepts the appointment and agrees to perform the Delegated Functions set out in Schedule 1 with due care, skill, and diligence.

3.3 The Manager acts as agent of the Trustee (and not as principal) and acknowledges that all property, data, and tokens acquired or managed under this Agreement are held on behalf of the Trust.

3.4 The appointment is non-exclusive as between Trusts under the Acacia Structure, but the Manager must ensure that no conflicts or co-mingling occur between Trusts.

⸻

4. Delegated Authority

4.1 Subject to this Agreement and the Trust Deed, the Manager may:
	•	originate, assess, and acquire eligible receivables via Invoice Purchase Agreements;
	•	approve or reject investments in accordance with Eligibility Criteria;
	•	manage receivable lifecycle events (repayments, repurchases, defaults);
	•	execute smart-contract operations (minting, transfers, redemptions, distributions);
	•	monitor and report on portfolio performance; and
	•	recommend strategic adjustments to Trust parameters (yield, liquidity, tenor).

4.2 The Manager must not:
	•	issue or redeem units without Trustee approval;
	•	borrow funds or grant security interests beyond the approved facility limits;
	•	enter into derivatives or hedges without Trustee consent;
	•	engage in any transaction for its own account using Trust information;
	•	amend Trust governance or smart contracts without Trustee co-signature.

⸻

5. Standard of Care and Compliance

The Manager must:
	•	act in good faith, with reasonable care, skill, and diligence;
	•	comply with applicable laws, including the Corporations Act 2001 (Cth), PPSA, Privacy Act 1988 (Cth), and AML/CTF Act 2006 (Cth);
	•	maintain systems ensuring operational resilience, cyber protection, and data privacy;
	•	maintain a clear segregation between proprietary and Trust assets; and
	•	act in the best interests of the Trust and its unitholders.

If the Manager performs functions requiring an AFSL, it must either hold an appropriate licence or rely on a valid wholesale exemption.

⸻

6. Key Personnel

6.1 The Manager must nominate Key Persons responsible for oversight (e.g., CEO, Head of Risk, Platform Architect).

6.2 The Manager must notify the Trustee of any departure or incapacity of Key Persons within 5 Business Days and propose replacements acceptable to the Trustee.

6.3 Loss of Key Persons without replacement may constitute a Termination Event (see clause 15).

⸻

7. Conflicts of Interest

7.1 The Manager must maintain and comply with a documented Conflicts Management Policy.

7.2 Related-party transactions (including any with the Platform Operator or Originators) must be disclosed to and approved by the Trustee in writing.

7.3 The Manager may manage multiple trusts under the Acacia framework, provided segregation and fairness are maintained.

⸻

8. Reporting and Transparency

8.1 The Manager must provide to the Trustee:
	•	Monthly Reports: NAV, portfolio composition, receivable performance metrics, default/dilution statistics.
	•	Quarterly Compliance Reports: certification of adherence to Eligibility and Concentration Limits.
	•	Incident Reports: within 24 hours of any material system, settlement, or data breach.
	•	Annual Review: performance analysis and strategic outlook.

8.2 Reports must be generated through the Platform’s immutable ledger and API interface, digitally signed by authorised keys.

⸻

9. Operational Risk and Business Continuity

9.1 The Manager shall maintain and test a Business Continuity Plan (BCP) and Disaster Recovery Plan (DRP) covering:
	•	critical systems redundancy;
	•	manual fallback procedures;
	•	cold-wallet recovery of private keys;
	•	third-party service continuity (custodians, oracles, KYC vendors).

9.2 RTO (Recovery Time Objective): ≤ 24 hours; RPO (Recovery Point Objective): ≤ 4 hours.

9.3 The Trustee may conduct or request independent testing of these plans annually.

⸻

10. Cybersecurity and Data Protection

10.1 The Manager must maintain compliance with:
	•	ISO/IEC 27001 Information Security Management standards;
	•	privacy and encryption protocols aligned with the Privacy Notice;
	•	key custody through multi-signature or HSM-secured systems.

10.2 In case of a cybersecurity incident, the Manager shall immediately notify the Trustee and implement containment measures.

10.3 Ledger integrity and hash records of data provenance must be auditable and preserved for 7 years.

⸻

11. Fees and Expenses

11.1 The Manager is entitled to the following remuneration, payable monthly in arrears:

Fee Type	Calculation Basis	Notes
Base Management Fee	[●]% per annum of Trust NAV	Paid monthly
Performance Fee	[●]% of returns exceeding [Benchmark]% p.a.	Subject to high-water mark
Transaction Fee	[●] bps of each receivable purchase	Optional
Reimbursement of Expenses	At cost	With supporting invoices

11.2 Fees may be deducted directly from the Trust’s income waterfall under Trustee authorisation.

⸻

12. Records, Audit, and Inspection

12.1 The Manager must maintain complete and accurate records of all Trust operations.

12.2 The Trustee and its auditors may, on reasonable notice, inspect and copy all such records (including smart-contract logs and blockchain transactions).

12.3 All data must be made available in machine-readable format and cross-referenced to on-chain transaction IDs.

⸻

13. Insurance

The Manager must maintain at all times:
	•	Professional Indemnity Insurance covering not less than AUD [●];
	•	Cybersecurity Insurance with coverage for data breaches, key loss, and operational downtime;
	•	Directors’ & Officers’ Insurance covering senior management.

Certificates of currency must be provided to the Trustee annually.

⸻

14. Representations and Warranties

The Manager represents that:
	•	it has all necessary authorisations and resources to perform its duties;
	•	it is solvent and not subject to external administration;
	•	its systems and personnel comply with relevant data and financial regulations;
	•	it will not knowingly engage in conduct that causes the Trust to breach law or regulation.

⸻

15. Term and Termination

15.1 This Agreement commences on [Commencement Date] and continues until terminated under this clause.

15.2 Termination by Trustee:
	•	for cause, immediately upon breach or insolvency of the Manager;
	•	without cause, on 90 days’ written notice.

15.3 Termination by Manager:
	•	on 120 days’ written notice to the Trustee.

15.4 On termination, the Manager must:
	•	cooperate fully in handover to any replacement manager;
	•	provide complete data export (off-chain and on-chain state);
	•	return all Trust property, credentials, and intellectual property.

15.5 Termination does not affect accrued rights to fees or indemnities.

⸻

16. Indemnity and Limitation of Liability

16.1 The Manager indemnifies the Trustee and Unitholders against loss arising from its breach, negligence, fraud, or wilful misconduct.

16.2 The Trustee indemnifies the Manager for liabilities incurred in good faith performance of its duties (excluding fraud or negligence).

16.3 The Manager’s total liability under this Agreement (excluding fraud or wilful misconduct) shall not exceed the total fees paid in the preceding 12 months.

⸻

17. Confidentiality and Intellectual Property

17.1 Each Party must treat as confidential all information obtained under this Agreement.

17.2 Intellectual property developed by the Manager in the course of providing services shall be owned by the Manager but licensed to the Trustee for perpetual internal use.

17.3 The Manager may use anonymised, aggregated data for analytics and system improvement, provided it contains no identifiable personal or Trust-specific information.

⸻

18. AML/CTF Obligations

The Manager must:
	•	operate under and comply with the Trust’s AML/CTF Program;
	•	ensure all KYC, sanctions screening, and blockchain analytics are performed before acquisitions;
	•	maintain transaction records for seven (7) years;
	•	promptly report suspicious matters to AUSTRAC through the Trustee.

⸻

19. Notices

Notices may be delivered by:
	•	Email to designated representatives;
	•	Secure Platform Message (yieldfabric.io notification); or
	•	On-chain signed message verified by authorised wallet keys.

Notice is deemed received on the earlier of blockchain confirmation or next Business Day.

⸻

20. Governing Law

This Agreement is governed by and construed in accordance with the laws of New South Wales, Australia.
The Parties submit to the exclusive jurisdiction of the courts of New South Wales.

⸻

21. Dispute Resolution

Before commencing proceedings, the Parties must:
	1.	Attempt informal negotiation (10 Business Days);
	2.	Refer to mediation under the Resolution Institute Rules (Sydney);
	3.	If unresolved, proceed to binding arbitration or court proceedings.

⸻

22. Force Majeure

Neither Party shall be liable for delay or failure to perform obligations (other than payment) due to causes beyond reasonable control (including cyber incidents, power outages, or blockchain network halts).

⸻

23. Counterparts and Electronic Execution

This Agreement may be executed in any number of counterparts (including digitally) and together form one instrument.
Digital signatures and smart-contract confirmations constitute valid execution.

⸻

Schedule 1 — Delegated Functions

Function	Description	Limits
Receivable Acquisition	Evaluate and execute IPAs for eligible invoices	Within Concentration Limits
Portfolio Monitoring	Real-time performance tracking via Platform	Continuous
Reporting	Monthly NAV and yield reporting to Trustee	Required
Servicer Oversight	Monitor originators’ compliance	Ongoing
Liquidity Management	Coordinate with Cash Trust for redemptions	Subject to Trustee approval
Risk Analysis	Maintain loss, default, and stress metrics	Monthly updates
Smart Contract Operations	Execute mint, burn, transfer, and distribution functions	Multi-sig controlled


⸻

Schedule 2 — Fee Example
	•	Management Fee: 1.00% p.a. of NAV
	•	Performance Fee: 10% of returns above 6% p.a.
	•	Transaction Fee: 0.10% per purchase
	•	Minimum annual fee: AUD 100,000 (if applicable)

⸻

Schedule 3 — Definitions

Include references to:
	•	Corporations Act 2001 (Cth)
	•	Personal Property Securities Act 2009 (Cth)
	•	Privacy Act 1988 (Cth)
	•	AML/CTF Act 2006 (Cth)
	•	Invoice Purchase Agreement
	•	Trust Deed
	•	YieldFabric Platform
	•	Receivable Token
	•	Collections Account
	•	Majority Investors