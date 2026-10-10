---
document_id: DOC-SYS-001
title: System Architecture, Data Classification, and Role-Based Access Control
category: System and Data Governance
document_type: SPECIFICATION
version: 2
status: ACTIVE
effective_from: "2024-01-01"
effective_until: "2027-12-31"
classification: RESTRICTED
allowed_roles: ["FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
source: Omerta.ai Enterprise Systems Architecture
---

# Section 1: Data Classification and Retention Standards

1.1. Data Classification Tiers
All data stored within the platform falls under three sensitivity tiers:
- TIER 1 - PUBLIC: Public documentation, general AML typologies, public API health specs.
- TIER 2 - INTERNAL: Operational guidelines, system runbooks, anonymized statistical aggregations.
- TIER 3 - RESTRICTED: Customer PII, National IDs, passwords hashes, account ledger balances, real-time transaction graphs, active investigation cases.

1.2. Retention Schedules
- Financial Ledger Entries: Retained for a minimum of 10 years in compliance with Central Bank statutory mandates.
- Investigation Dossiers and SAR Filings: Retained indefinitely in WORM (Write Once, Read Many) tamper-evident storage.
- Session Telemetry & Ephemeral Telemetry: Retained for 180 days before automated partitioning purge.

# Section 2: Role-Based Access Control (RBAC) Permissions

2.1. System Persona Permissions
- ADMINISTRATOR: Full system provisioning, staff user management, system risk model tuning, global audit log inspection.
- FRAUD_ANALYST: Triage alert queue, review customer support security cases, inspect device profiles, execute standard queries.
- INVESTIGATOR / SENIOR_INVESTIGATOR: Full case management, execute multi-agent AI forensic pipelines, generate SAR filings, sign off on case dispositions.
- AUDITOR: Read-only access across all audit logs, evidence ledgers, and past case resolutions without modification capabilities.
- CUSTOMER: Restricted strictly to own banking dashboard, P2P transfers, beneficiary management, and own support tickets.

# Section 3: Dual Persistence Architecture and Source of Truth

3.1. PostgreSQL as Single Source of Truth
PostgreSQL 17 is the authoritative ground truth for all financial transactions, account balances, and customer profiles. Every balance computation derives strictly from immutable double-entry ledger entries.

3.2. Neo4j as Derived Graph Projection
Neo4j 5 is a specialized derived topological projection. It does NOT store the authoritative financial ledger. Graph projections are updated synchronously or asynchronously from verified PostgreSQL events. In any event of discrepancy, PostgreSQL records always take absolute precedence.
