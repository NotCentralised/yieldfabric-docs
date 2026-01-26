ANTI-MONEY LAUNDERING AND COUNTER-TERRORISM FINANCING PROGRAMME (AML/CTF PROGRAMME)

(Enhanced Tokenised Securitisation Version — NotCentralised Acacia Trust Framework)

⸻

1. Purpose and Scope

1.1 This AML/CTF Programme (“Programme”) sets out the framework by which NotCentralised Pty Ltd (“NotCentralised” or “the Reporting Entity”) and its related entities — including YieldFabric Pty Ltd (Platform Operator) and the Trustees of the Acacia Trusts — identify, mitigate, and manage the risk of money laundering and terrorism financing (ML/TF).

1.2 The Programme is designed to comply with the Anti-Money Laundering and Counter-Terrorism Financing Act 2006 (Cth) (“AML/CTF Act”), AML/CTF Rules, and AUSTRAC guidance, and to align with FATF Recommendations and international best practice for digital-asset service providers.

1.3 It applies to all employees, officers, agents, and contractors of NotCentralised, the Platform Operator, the Investment Manager, and the Trustees of the Acacia Trusts.

⸻

2. Designated Services and AUSTRAC Registration

2.1 The following constitute Designated Services under the AML/CTF Act:
	•	Providing custodial or depository services for digital assets;
	•	Operating a tokenised investment scheme or trust structure (e.g., issuance and redemption of Units);
	•	Exchanging fiat currency for digital tokens (stablecoins) and vice versa;
	•	Managing investment portfolios and trust accounts on behalf of investors;
	•	Facilitating international funds transfers or settlement instructions.

2.2 Reporting Entities:

Entity	Role	AUSTRAC Status
NotCentralised Pty Ltd	Investment Manager & DCE operator	Reporting Entity
YieldFabric Pty Ltd	Platform Operator (custodial wallet & registry)	Reporting Entity
AMAL Trustees Pty Ltd	Trustee (designated under s6(2))	Reporting Entity
Perpetual Corporate Trust Ltd	Security Trustee (lender-facing)	Reporting Entity
Structured Issuer Trust	Non-reporting entity (wholesale vehicle)	N/A


⸻

3. Governance and Oversight

3.1 Board and Compliance Structure

Role	Responsibility
Board of Directors	Ultimate oversight of AML/CTF compliance
AML/CTF Compliance Officer	Day-to-day implementation, reporting, and liaison with AUSTRAC
Deputy Compliance Officer	Acts during absence of primary officer
Risk & Audit Committee	Quarterly review of AML/CTF metrics and incidents
Independent Reviewer	Biennial independent AML/CTF Program review (as required by Rule 8.6)

3.2 The AML/CTF Compliance Officer reports directly to the CEO and Board.
3.3 The Programme is reviewed annually and approved by the Board.

⸻

4. Risk-Based Approach

4.1 Enterprise Risk Assessment (ERA)
The ERA identifies ML/TF risks across products, channels, customers, and jurisdictions.
Key risk categories:

Category	Risk Level	Controls
Tokenised Trust Units	Medium	KYC, source-of-wealth verification, whitelist wallets
Receivable Tokens	Low–Medium	Originator KYC, commercial contract validation
Stablecoin On/Off-Ramp	Medium–High	DCE monitoring, Travel Rule compliance
Institutional Investors	Low	AFSL/regulated entity reliance
Cross-Border Transfers	High	Travel Rule, FATF country risk scoring

4.2 Risk scores are reviewed quarterly and updated with emerging typologies (e.g., layering through decentralised exchanges or privacy tools).

⸻

5. Customer Identification Procedures (KYC / CDD)

5.1 When Identification Is Required
	•	Onboarding of investors, lenders, or originators;
	•	Opening of wallets or accounts;
	•	Prior to issuance or redemption of Units;
	•	Prior to any transaction ≥ AUD 10,000 (or equivalent stablecoin).

5.2 Verification Sources
	•	Digital ID services (e.g., Australian Document Verification Service);
	•	Independent KYC vendors (ISO/IEC 27001 certified);
	•	Blockchain analytics and address clustering tools.

5.3 Customer Categories

Customer Type	Verification Level
Individual	Standard KYC (Photo ID, PoA)
Corporate / Trustee	Full KYC (ASIC search, beneficial owner verification)
Originator	Enhanced due diligence (EDD) inc. ownership chain
Institutional Investor	Simplified due diligence (regulated entity reliance)
Foreign Entity	EDD + sanctions screening

5.4 Beneficial Ownership
Identify individuals with ≥25% control or effective control through other means.

5.5 Record Keeping
KYC records retained for 7 years after relationship end.

⸻

6. Enhanced Due Diligence (EDD)

EDD applies when:
	•	the customer or transaction involves high-risk jurisdictions (FATF grey/black-listed);
	•	the structure involves cross-border stablecoin flows;
	•	the transaction type is unusual for the customer profile;
	•	the source of funds or wealth is unclear.

Measures include:
	•	verification of source of funds and wealth;
	•	senior management approval before onboarding;
	•	closer ongoing monitoring (high-frequency transaction review).

⸻

7. Ongoing Customer Due Diligence and Monitoring

7.1 Continuous Monitoring:
All customers are subject to real-time monitoring through:
	•	blockchain analytics for on-chain activity;
	•	automated alerts for abnormal transaction size, frequency, or counterparties;
	•	sanctions list updates (OFAC, DFAT, UN, EU).

7.2 Periodic Reviews:

Risk Tier	Review Frequency
High	Annually
Medium	Every 2 years
Low	Every 3 years

7.3 Any wallet receiving or sending funds to unverified or sanctioned addresses is automatically flagged and, if necessary, frozen.

⸻

8. Blockchain Analytics and Whitelisting

8.1 All wallets transacting with the Acacia Trusts must be whitelisted after passing KYC.
8.2 The Platform integrates with blockchain-intelligence providers (e.g., Chainalysis, TRM Labs, Elliptic) for:
	•	address risk scoring,
	•	transaction tracing,
	•	exposure monitoring.
8.3 Wallets associated with mixers, darknet markets, or sanctioned addresses are blocked automatically.

⸻

9. Suspicious Matter, Threshold, and Cross-Border Reports

9.1 Suspicious Matter Reports (SMRs): lodged within 3 business days (24 hours for terrorism financing) of detection.
9.2 Threshold Transaction Reports (TTRs): for cash/stablecoin transactions ≥ AUD 10,000 (or equivalent).
9.3 International Funds Transfer Instructions (IFTIs): filed for cross-border flows, including stablecoin transfers to offshore wallets.
9.4 All reports are submitted electronically via AUSTRAC Online and cross-referenced to blockchain transaction hashes.

⸻

10. Travel Rule Implementation

10.1 In accordance with FATF Recommendation 16, all cross-border token transfers must include:
	•	sender and beneficiary identifiers,
	•	wallet addresses,
	•	transaction purpose.
10.2 Data is exchanged securely through an API-based Travel Rule gateway between VASPs (Virtual Asset Service Providers).
10.3 Transfers without compliant Travel Rule data are rejected or held pending verification.

⸻

11. Sanctions Screening

11.1 Screening is conducted at onboarding and on each transaction against:
	•	DFAT Consolidated Sanctions List,
	•	OFAC SDN List,
	•	UN and EU lists.

11.2 Continuous screening occurs through automated data feeds.
11.3 Hits are escalated within 1 business day for manual review.
11.4 Confirmed hits trigger account freeze and reporting to AUSTRAC and DFAT.

⸻

12. Record Keeping and Audit Trail

12.1 Maintain:
	•	KYC data (7 years);
	•	transaction logs and analytics (7 years);
	•	SMR/TTR/IFTI evidence (7 years).

12.2 All records are hash-anchored to the blockchain for integrity verification.
12.3 Off-chain copies are stored encrypted in ISO 27001-compliant data centres located in Australia.

⸻

13. Training and Awareness

13.1 All employees and contractors receive AML/CTF training:
	•	at induction;
	•	annually; and
	•	upon material regulatory change or AUSTRAC feedback.

13.2 Training covers:
	•	typologies in tokenised finance;
	•	identifying red flags in smart-contract transactions;
	•	reporting and escalation protocols.

Records of attendance are maintained for 7 years.

⸻

14. Independent Review

14.1 An independent reviewer must assess the design and effectiveness of the Programme every two years, in accordance with AML/CTF Rule 8.6.
14.2 Findings and remediation plans must be reported to the Board and documented in the annual compliance report to AUSTRAC.

⸻

15. Interaction with the YieldFabric Platform

15.1 The Platform enforces AML/CTF compliance by design:
	•	wallet whitelisting and address scoring;
	•	automated alerts for high-risk activity;
	•	transaction screening before execution;
	•	immutable audit logging of all KYC and AML events;
	•	configurable freeze/burn mechanisms for tokens linked to breaches.

15.2 All AML events are recorded as Ledger Events under the Swap & Token Operation Terms (Annex).

⸻

16. Reporting to the Board and AUSTRAC

16.1 Quarterly Compliance Report includes:
	•	number of customers onboarded by risk tier;
	•	number of alerts and SMRs;
	•	high-risk country exposures;
	•	training and system performance metrics.

16.2 Significant breaches are reported to AUSTRAC immediately.

⸻

17. Cooperation with Regulators and Law Enforcement

The Reporting Entity cooperates fully with:
	•	AUSTRAC (AML/CTF regulator and FIU);
	•	AFP and NSW Police (criminal investigations);
	•	ASIC and ATO (financial markets and tax compliance).

Information sharing occurs under permitted gateways (AML/CTF Act s123) and MOUs.

⸻

18. Incident Response and Escalation

18.1 Incident Types: data breach, key compromise, suspicious activity, system outage.
18.2 Response Protocol:
	1.	Immediate containment and log preservation;
	2.	Escalation to AML/CTF Officer within 2 hours;
	3.	Assessment for SMR lodgement;
	4.	Notification to Board and, where applicable, OAIC (for data breach).

18.3 Freeze Function: triggered if ML/TF suspicion cannot be ruled out within 24 hours.

⸻

19. Cross-Entity Coordination (Trust-Level Compliance)

19.1 Each Trust (Structured Issuer, Invoice Collateral, Cash) operates its own AML/CTF record subset within the shared platform.
19.2 Trustees and the Manager share data through secure inter-trust gateways with hashed logs to preserve segregation and auditability.
19.3 AML obligations are allocated as follows:

Function	Responsible Entity
Customer Onboarding	Investment Manager / Platform
Trust-level KYC	Trustee
Transaction Screening	Platform
Suspicious Matter Reporting	Investment Manager / Trustee
Record Retention	Platform (custodian)


⸻

20. Program Maintenance and Continuous Improvement

20.1 The AML/CTF Officer ensures this Programme remains current with:
	•	AUSTRAC rule amendments;
	•	FATF guidance on virtual assets;
	•	emerging ML/TF typologies.

20.2 The Programme is reviewed annually by the Board and updated as needed.

⸻

21. Appendices

Appendix A — Red Flag Indicators (Digital Asset Context)
	•	Frequent transfers to/from mixers or anonymity-enhanced tokens.
	•	Originator wallets with multiple unrelated token types.
	•	Repeated small value transactions below reporting thresholds.
	•	Rapid redemption of stablecoins into fiat.
	•	Token swaps without clear economic purpose.

Appendix B — Sanctions Escalation Flow
	1.	Automated alert (Level 1)
	2.	Manual review by AML Analyst (Level 2)
	3.	Escalation to Compliance Officer (Level 3)
	4.	Freeze and AUSTRAC/DFAT report (Level 4)

Appendix C — Training Matrix

Role	Frequency	Content Focus
Board	Annual	Strategic AML oversight
Executive	Semi-annual	Emerging ML/TF typologies
Staff / Contractors	Annual	Operational AML procedures
Developers	Annual	Secure coding & AML integration
Advisors / Consultants	Onboarding	AML obligations and data handling


⸻

22. Governance Approval

This Programme was approved by the Board of NotCentralised Pty Ltd on [●].
It is effective from [Effective Date] and supersedes all prior AML/CTF Programmes.

Signatures

Name	Title	Signature	Date
[●]	Chair, NotCentralised Pty Ltd		
[●]	AML/CTF Compliance Officer		