# Omerta.ai — Forensic AML/CFT Money Laundering Typologies & Banking Transfer Warnings Report

## 1. Executive Summary

This report establishes the comprehensive regulatory and forensic framework for identifying money laundering typologies, financial crime vectors, and banking transfer warning triggers within the Omerta.ai banking intelligence ecosystem. 

All indicators adhere to the Financial Action Task Force (FATF) 40 Recommendations, Egmont Group guidelines, Central Bank regulations, and Omerta.ai internal security governance policies.

---

## 2. Comprehensive Money Laundering Typologies via Banking Transfers

The following scenarios represent the primary money laundering vectors executed through electronic funds transfers:

### 2.1 Structuring and Smurfing (Sub-Threshold Splitting)
- **Typology Mechanism:** Illicit actors intentionally divide a large volume of funds into multiple small deposits or peer-to-peer transfers just below mandatory regulatory reporting thresholds (e.g., transfers split into multiple 45,000 EGP or 49,000 EGP tranches to evade a 50,000 EGP CTR threshold).
- **Forensic Indicators:**
  - Multiple incoming or outgoing transfers occurring within 24 to 72 hours with amounts clustered just below threshold boundaries.
  - Transactions originating from multiple disparate accounts into a single consolidation account within a compressed time window.
- **Risk Assessment:** High to Critical. Trigger for immediate Transaction Monitoring System (TMS) SAR/STR investigation.

### 2.2 Rapid Velocity Inflow-Outflow (Pass-Through / Transit Accounts)
- **Typology Mechanism:** Funds are transferred into an account and almost immediately (often within minutes or hours) disbursed to one or more third-party destination accounts. The account holds minimal or zero closing balance.
- **Forensic Indicators:**
  - Inflow-to-outflow ratio exceeding 90% within a 24-hour lookback window.
  - Account does not demonstrate typical retail banking utility (no utility bill payments, salary deposits, or sustained savings balances).
  - High degree centrality in the transaction network with brief holding duration.
- **Risk Assessment:** Critical. Primary typology of money mule networks and layered payment rails.

### 2.3 Round-Tripping (Cyclic Fund Flow)
- **Typology Mechanism:** Funds leave an originator account, hop through one or more intermediate accounts, and return either directly to the originator or to a known affiliated entity (e.g., shared beneficial owner, spouse, or co-located device).
- **Forensic Indicators:**
  - Directed cyclic path detected in the Neo4j graph topology (Account A -> Account B -> Account C -> Account A).
  - Disbursed amounts match inbound amounts minus minor intermediary transaction fees.
- **Risk Assessment:** Critical. Indicates fictitious trade financing, tax evasion, or artificial volume inflation.

### 2.4 Money Mule Syndicates
- **Typology Mechanism:** Organized criminal rings recruit retail individuals (often students, unemployed individuals, or compromised account holders) to receive illicit proceeds and forward them onwards in exchange for a small percentage commission.
- **Forensic Indicators:**
  - Account historical activity changes abruptly from low volume (e.g., small retail spending) to large spikes in incoming transfers from unknown counterparties.
  - Multiple account holders authenticating from a single shared mobile device or computer hardware fingerprint.
  - Co-located IP addresses across ostensibly unrelated retail customer accounts.
- **Risk Assessment:** Critical. Warranting immediate account restriction and customer identity re-verification.

### 2.5 Shared Hardware Device and Infrastructure Rings
- **Typology Mechanism:** A single threat actor or botnet operator manages dozens of accounts simultaneously from a single device, emulator, or virtual private network (VPN) tunnel.
- **Forensic Indicators:**
  - Shared device identifier (DEV-ID) bound to more than one distinct customer national ID.
  - Device properties indicate root access, jailbreaking, or Android emulator signatures (e.g., Bluestacks, Genymotion).
  - Fast session switching between unrelated customer accounts within seconds.
- **Risk Assessment:** Critical. Direct violation of Omerta.ai security policy DOC-SEC-001.

### 2.6 Sudden Reactivation of Dormant Accounts
- **Typology Mechanism:** An account with zero transaction activity for 180+ days suddenly initiates or receives maximum-limit transfers.
- **Forensic Indicators:**
  - Velocity index spikes from 0 to peak limit within 24 hours.
  - Change in customer credentials or recovery requests followed immediately by high-value transfers.
- **Risk Assessment:** High. High correlation with account takeover (ATO) or sold mule credentials.

### 2.7 High-Value Transfers without Economic Rationale
- **Typology Mechanism:** Customer profile (stated income, occupation, and business type) does not support the volume or frequency of processed transfers.
- **Forensic Indicators:**
  - Discrepancy between Know Your Customer (KYC) risk profile and observed transaction velocity.
  - Transfers labeled with vague or nonsensical reference notes.
- **Risk Assessment:** Medium to High. Triggers Enhanced Due Diligence (EDD).

---

## 3. Systematic Banking Transfer Warnings & Threshold Rules

Omerta.ai implements multi-tier deterministic and behavioural transfer warnings:

| Warning Trigger | Evaluation Rule | System Action | Policy Reference |
| :--- | :--- | :--- | :--- |
| **3-Strike Security Password Hold** | 3 consecutive failed transfer password attempts on session | Automatic freeze on transfer execution; account state set to RESTRICTED | DOC-SEC-001 §2.1 |
| **New Hardware Device Warning** | Transfer initiated from device unseen in preceding 30 days | MFA Challenge step-up; 24-hour cooling-off cap applied | DOC-SEC-001 §3.4 |
| **VPN / Datacenter Proxy Signal** | Transfer telemetry originates from commercial VPN / hosting IP | Transfer flagged for review; high-risk score increment (+35 points) | DOC-SEC-001 §4.2 |
| **Single Transfer Velocity Cap** | Outgoing transfer exceeding single-transaction threshold (e.g., >100,000 EGP) | Requires secondary authorization (Four-Eyes approval) | DOC-OPS-001 §3.1 |
| **Rapid Successive Payee Addition** | New beneficiary added and transferred to within 15 minutes | Mandatory 30-minute delay; SMS verification dispatch | DOC-OPS-001 §4.3 |
| **High Disbursal Velocity** | Account receives funds and disburses >90% within 60 minutes | Auto-generated AML Case in Investigation Queue with High priority | DOC-AML-001 §2.3 |
| **Co-Located Device Shared Account** | Account sends or receives money to an account sharing the same DEV-ID | Graph alert displayed on Network Intelligence; risk score set to HIGH | DOC-AML-001 §3.5 |
| **Currency Discrepancy** | Transfer involves accounts of different currencies without authorized FX path | Transfer halted; exception record created in ledger | DOC-OPS-001 §1.4 |

---

## 4. Forensic Investigation & Escalation Protocol

When an investigator evaluates an alert in the Omerta.ai console:

1. **Phase 1 — Fact Collation:**
   - Review verified ledger records in PostgreSQL (exact balances, transfer timestamps, and transaction metadata).
   - Trace counterparty relationships and shared hardware in Neo4j (inspect shared devices, IP clusters, and degree count).
2. **Phase 2 — Contextual Grounding:**
   - Retrieve applicable internal policies and regulatory standards via Agentic RAG.
   - Corroborate whether the activity breaches KYC declared expectations.
3. **Phase 3 — Disposition Determination:**
   - **CLEAR:** Legitimate commercial or personal transaction substantiated by documentation.
   - **ESCALATE (SENIOR REVIEW):** Elevated suspicion requiring four-eyes review and potential SAR filing.
   - **RESTRICT:** Confirmed compromise or illicit laundering pattern. The security hold is enforced, preventing further disbursements.
