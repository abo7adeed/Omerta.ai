---
document_id: DOC-OPS-001
title: Banking Operations Policy and Double-Entry Ledger Standards
category: Banking Operations
document_type: POLICY
version: 2
status: ACTIVE
effective_from: "2024-01-01"
effective_until: "2027-12-31"
classification: INTERNAL
allowed_roles: ["CUSTOMER", "FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
source: Omerta.ai Core Banking Operations Manual
---

# Section 1: Account Lifecycle and Account Status

1.1. Account Status Definitions
Every customer checking or savings account in Omerta.ai maintains a strict operational lifecycle status:
- ACTIVE: Account is fully authorized for deposits, peer-to-peer transfers, wire settlements, and withdrawals.
- DORMANT: Account has experienced no user-initiated transactions for 180 consecutive days. Requires re-authentication and automated identity confirmation before outbound money movement.
- SUSPENDED: Temporary operational lock triggered by automated risk thresholds, chargeback disputes, or compliance reviews. Deposits are allowed; outbound transfers are rejected.
- BLOCKED: Total operational freeze enacted by security holds (e.g. 3 consecutive failed transfer password strikes) or formal court/FIU injunctions. Outbound fund movement is strictly prevented until administrative restoration.
- CLOSED: Account has been permanently liquidated with zero remaining balance and archived into the immutable audit store.

1.2. Account Creation and KYC Minimum Requirements
To transition from registered prospect to ACTIVE account holder:
- The customer must provide full legal name, verified email address, mobile number, and national identification document (Egyptian National ID or equivalent passport).
- A unique immutable Omerta User Number (e.g. OMR-1092-4821) is stamped on the account profile.

# Section 2: Transfer Processing and Double-Entry Accounting

2.1. Principle of Balanced Double-Entry Accounting
All financial balance movements within Omerta.ai are recorded using strictly balanced double-entry ledger entries (account_ledger_entries).
- A transfer from Sender Account A to Recipient Account B generates two atomic entries within a single transactional block:
  1. DEBIT entry on Account A decreasing available balance by the principal amount.
  2. CREDIT entry on Account B increasing available balance by the exact principal amount.
- The platform enforces an absolute mathematical invariant: SUM(Debits) == SUM(Credits) across every executed transfer. Direct updates to account balances without matching ledger entries are blocked at the database constraint layer.

2.2. Atomic Concurrency and Row-Level Locking
To prevent race conditions and double-spending during rapid concurrent requests, transfer executions employ pessimistic database locks (SELECT ... FOR UPDATE) on both sender and recipient account rows before balance verification and ledger insertion.

# Section 3: Transaction Limits and Verification

3.1. Daily and Per-Transaction Ceilings
Standard individual retail accounts operate under tiered transfer limits:
- Standard Tier: Maximum single transfer of 50,000.00 EGP; daily cumulative ceiling of 100,000.00 EGP.
- Verified Tier (with National ID photo verification): Maximum single transfer of 250,000.00 EGP; daily cumulative ceiling of 500,000.00 EGP.
- Commercial/Corporate Tier: Negotiated limits subject to formal board resolution and enhanced due diligence.

3.2. Structuring and Smurfing Detection
Any series of transfers executed within a 72-hour window structured intentionally below reporting thresholds (for instance, consecutive transfers of 49,000.00 EGP) are automatically aggregated and assigned a HIGH velocity risk signal for analyst review.

# Section 4: Security Holds and Access Restoration

4.1. Non-Logout Security Hold Mechanics
If a customer enters an incorrect transfer password three consecutive times, the platform places the customer's transfer capabilities into BLOCKED status.
- Crucially, the customer's portal session is NOT terminated. The user retains read access to balances, past transactions, and the support desk.
- An automated support ticket is immediately created with priority HIGH, allowing the customer to communicate with staff and upload identification.

4.2. Administrative Restoration Procedure
Only compliance officers or fraud analysts possessing authorized roles can restore transfer permissions:
- The officer reviews uploaded identity verification documents.
- Upon approval, the officer invokes the restoration action, resetting failed attempt counters, logging the event in transfer_restorations, and flagging require_transfer_password_change.

# Section 5: Reconciliation and Audit Procedures

5.1. Daily Ledger Reconciliation
At 23:59:59 UTC daily, automated reconciliation jobs compute the sum of all historical ledger entries against the balance snapshot on each account. Any variance greater than 0.00 EGP halts automated settlement batching and alerts system administrators.
