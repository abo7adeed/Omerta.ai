---
document_id: DOC-AML-001
title: Anti-Money Laundering, Counter-Terrorist Financing, and Typology Standards
category: AML/CFT and Financial Crime
document_type: STANDARD
version: 3
status: ACTIVE
effective_from: "2024-01-01"
effective_until: "2027-12-31"
classification: RESTRICTED
allowed_roles: ["FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
source: Omerta.ai Financial Intelligence Unit (FIU)
---

# Section 1: Suspicious Transaction Indicators and Red Flags

1.1. Core Typology Categories
The Omerta.ai detection engine tracks six primary financial crime typologies:
- MULE_ACCOUNT: Accounts utilized primarily as conduits for receiving and instantly forwarding funds, breaking the financial trail between predatory origin and destination.
- FRAUD_RING: Syndicates coordinating across multiple accounts, frequently operating from shared devices, co-located IP subnets, or common beneficiary targets.
- LAYERING: Successive, rapid, and purposeless transfers through multiple intermediate accounts intended to disguise the illicit source and ownership of funds.
- SMURFING: Structuring large monetary sums into numerous smaller sub-threshold deposits or transfers across disparate accounts.
- ACCOUNT_TAKEOVER: Unauthorized compromise of genuine customer credentials marked by immediate device changes, anomalous geolocation jumps, and rapid asset liquidation.
- NEW_DEVICE_ABUSE: Immediate high-value outbound transfers initiated within 60 minutes of binding an unrecognized hardware profile.

# Section 2: Rapid Inflow and Outflow (Conduit / Pass-Through Dynamics)

2.1. Mathematical Pass-Through Velocity Formula
An account is flagged as a potential pass-through conduit when meeting both thresholds within a rolling 24-hour observation window:
- Inflow Volume: Total credits received >= 2,000.00 EGP (or currency equivalent).
- Conduit Ratio: Total debited funds within 24 hours of receipt exceeds 65% of the total inflow volume (Outflow / Inflow > 0.65).
- Holding Period: Funds remain in the account for a median duration of less than 4 hours before onward routing.

2.2. Smurfing Fan-In Topology
Accounts receiving five or more sub-threshold transfers from distinct source accounts followed by a single consolidated outward transfer to an external beneficiary within 12 hours are marked with CRITICAL Conduit Risk.

# Section 3: Telemetry, Impossible Travel, and VPN Risk

3.1. Telemetry Geolocation Jumps
When consecutive login sessions or transfer attempts occur across geographic coordinates implying an impossible transit speed exceeding 800 km/h:
- An IMPOSSIBLE_TRAVEL anomaly is recorded in the risk engine.
- Outbound transfers require secondary step-up authorization.

3.2. Commercial VPN and Proxy Routing
Transfers initiated from known datacenter IP subnets, Tor exit nodes, or commercial VPN proxies are flagged with an elevated VPN Telemetry signal and factored into aggregate risk scoring.

# Section 4: Investigation and Human Review Mandate

4.1. Automated Alert Generation
Transactions exhibiting an aggregate risk score strictly exceeding 40.00 automatically generate a Review Queue Alert and provision an active Investigation Case.

4.2. Human-in-the-Loop Requirement
Automated algorithms, machine learning models, and autonomous AI agents cannot unilaterally freeze accounts or submit regulatory filings. All consequential actions require affirmative sign-off by a designated human Fraud Analyst or Senior Investigator.
