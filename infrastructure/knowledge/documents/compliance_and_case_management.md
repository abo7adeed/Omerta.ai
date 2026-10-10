---
document_id: DOC-CMP-001
title: Compliance Case Management, SAR Filing, and Evidence Procedures
category: Compliance and Case Management
document_type: PROCEDURE
version: 2
status: ACTIVE
effective_from: "2024-01-01"
effective_until: "2027-12-31"
classification: RESTRICTED
allowed_roles: ["FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
source: Omerta.ai Regulatory Compliance Directorate
---

# Section 1: Case Creation, Triage, and Prioritization

1.1. Case Origination Channels
Investigation cases in Omerta.ai originate through three defined triggers:
- AUTOMATED_ALERT: Triggered when real-time transaction risk score exceeds 40.00.
- ANALYST_ESCALATION: Created manually by frontline fraud analysts during transaction review.
- SUPPORT_TICKET: Escalated from customer identity verification disputes or recurrent transfer holds.

1.2. Priority Matrix
Cases are assigned strict SLAs based on risk tier:
- CRITICAL: Requires initial triage within 2 hours. Mandatory multi-hop graph trace and executive freeze evaluation.
- HIGH: Requires triage within 6 hours. Detailed account history inspection and device co-location analysis.
- MEDIUM: Standard 24-hour review window.
- LOW: Informational; reviewed within 72 hours or closed autonomously if false positive indicators match.

# Section 2: Evidence Standards and Referential Integrity

2.1. Evidence Categories
Every factual assertion in an active investigation must be cataloged into one of five immutable tiers:
- FACT: Verified raw records from PostgreSQL (transaction ledger rows, account metadata, login records).
- STRUCTURAL_SIGNAL: Topological relationships extracted from Neo4j (shared devices, co-located IP subnets, fund routing paths).
- MODEL_OUTPUT: Risk scores and signal contributions from deterministic rules or LightGBM models.
- KNOWLEDGE: Statutory definitions, regulatory thresholds, and policy citations retrieved from the Knowledge Base.
- AGENT_FINDING: Synthesized conclusions drawn by the multi-agent committee, strictly citing the underlying evidence IDs.

2.2. Prohibited Unsupported Allegations
No finding, note, or SAR draft may assert criminal conduct or illicit activity without explicitly linking to one or more verified evidence IDs. Reports failing referential integrity checks are automatically rejected at the validation layer.

# Section 3: Analyst Review, Escalation, and Closure

3.1. Case Dispositions
Upon concluding an inquiry, an investigator must record one of the following bounded dispositions:
- TRUE_POSITIVE_FRAUD: Confirmed fraud or AML breach; initiate fund freeze and escalate to legal.
- FALSE_POSITIVE_BENIGN: Legitimate commercial or family activity; dismiss alert with rationale.
- INCONCLUSIVE_MONITOR: Insufficient evidence; maintain account under heightened 30-day velocity monitoring.
- ESCALATE_TO_FIU: Activity warrants filing a formal Suspicious Activity Report (SAR) with state financial intelligence authorities.

3.2. Case Reopening Protocol
A closed case may only be reopened if subsequent transactions from associated accounts exceed risk thresholds within 90 days, or upon receipt of formal inquiry from law enforcement.
