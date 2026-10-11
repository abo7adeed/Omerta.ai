# Omerta.ai — Agentic RAG Architecture & System Topology

## 1. Executive Summary

The Omerta.ai Agentic RAG and AI Financial Analyst platform extends the core anti-financial-crime engine into an interactive, multi-source cognitive copilot. Designed specifically for forensic investigators, compliance officers, and financial crime analysts, the system integrates:
1. **Curated Document Knowledge Base:** Internal banking policies, double-entry ledger standards, system rules, operational procedures, compliance manuals, AML/CFT reference material, and regulatory documents.
2. **PostgreSQL Relational Ledger:** Authoritative source of structured financial facts (customers, accounts, double-entry ledger entries, transactions, review alerts).
3. **Neo4j Graph Topology:** Derived entity graph projection (accounts, devices, IP clusters, transfer flow paths, mule rings).
4. **Deterministic Analytical Execution Layer:** Mathematical aggregations, statistical summaries, period-over-period comparisons, and zero-mock visual analytics.

LLMs are never permitted to execute free-form arbitrary SQL, unrestricted Cypher, Python scripts, or shell commands. Language models (hosted on Groq or deterministic local fallbacks) are strictly bounded to semantic intent interpretation, parameter validation, and final structured narrative synthesis.

---

## 2. Logical Architecture

```text
                           Authenticated Investigator
                                     │
                                     ▼
                       Omerta.ai Frontend (React / Vite)
                                     │
                                     ▼
                  FastAPI Endpoint (/api/v1/agentic-rag/query)
                                     │
                          Authentication + RBAC Enforcement
                                     │
                                     ▼
                      LangGraph Orchestrator Workflow
   ┌─────────────────────────────────┼─────────────────────────────────┐
   ▼                                 ▼                                 ▼
Document Knowledge Base     PostgreSQL Relational Ledger      Neo4j Graph Topology
• DOC-OPS-001 (Operations)  • Authoritative Ledger Facts      • Shared Devices & IPs
• DOC-SEC-001 (Security)    • Customer & Account Profiles     • Bounded Transaction Paths
• DOC-AML-001 (Typologies)  • Deterministic Aggregates        • Fraud Rings & Clusters
• Role-Based Filtering      • Bounded Datasets (Limit <= 100) • Schema Overview Metadata
   └─────────────────────────────────┬─────────────────────────────────┘
                                     │
                                     ▼
                           Normalized Evidence
                   (Cryptographic SHA-256 Provenance)
                                     │
                                     ▼
                          Evidence Sufficiency Gate
                                     │
             ┌───────────────────────┴───────────────────────┐
             ▼                                               ▼
Deterministic Analytics Service               Groq Synthesis / Fallback Engine
• Decimal & Float Arithmetic                  • Professional Executive Markdown
• Zero-Division Safeguards                     • Seven-Pillar Graph Analysis
• Deterministic Comparisons                   • Non-Accusatory Guardrails
             │                                               │
             ▼                                               ▼
Matplotlib Visualization Engine               Cryptographic Citation Verification
• AREA, LINE, BAR, DONUT                      • Evidence ID Resolution
• Sapphire & Gold Styling                     • Source Type & Locator Match
• Truthful Zero-Mock Data Rule                • Canonical SHA-256 Hash Audit
             └───────────────────────┬───────────────────────┘
                                     │
                                     ▼
                      AgenticRAGResponse (Strict Contract)
                                     │
                                     ▼
              Collapsible 7-Stage Forensic Trace & Rich Blocks
```

---

## 3. Supported Natural-Language Intents

The intent understanding node (`understand_query_and_intent`) classifies inbound requests into 13 distinct analytical intents with explicit routing to authorized sources:

| Intent | Authoritative Source | Description & Routing Example |
| :--- | :--- | :--- |
| `DOCUMENT_SEARCH` | Document KB | Queries operational policies, e.g., *"What does internal policy say about settlement exceptions?"* |
| `TRANSACTION_LOOKUP` | PostgreSQL | Retrieves specific verified transaction fact, e.g., *"Show details for transaction TXN-1001."* |
| `ACCOUNT_LOOKUP` | PostgreSQL | Inspects verified account details, e.g., *"Who is associated with account ACC-1001?"* |
| `CUSTOMER_LOOKUP` | PostgreSQL | Searches customer profiles by person name or ID; never cites policy documents. |
| `FINANCIAL_AGGREGATION` | PostgreSQL | Deterministic sum, count, average, e.g., *"How many transfers occurred in the last 30 days?"* |
| `PERIOD_COMPARISON` | PostgreSQL | Multi-period comparison with percentage change, e.g., *"Compare current volume vs prior month."* |
| `TREND_ANALYSIS` | PostgreSQL | Temporal transaction velocity and daily timeline analysis. |
| `GRAPH_EXPLORATION` | Neo4j | Inspects entity connectivity, e.g., *"Which accounts share a device with ACC-1001?"* |
| `RISK_ANALYSIS` | Neo4j + PostgreSQL | Analyzes structural risk indicators and corroborated ledger anomalies. |
| `VISUALIZATION` | PostgreSQL + Matplotlib | Renders dynamic vector charts grounded strictly in retrieved records. |
| `MULTI_SOURCE_INVESTIGATION` | All Authorized Sources | Cross-verifies policies against actual transactions or relational ledgers against graph paths. |
| `GENERAL_BANKING_QUESTION` | Document KB | General industry questions (e.g., double-entry mechanics). |
| `NEEDS_CLARIFICATION` | Interactive | Prompted when customer name is ambiguous or entity reference is missing. |

---

## 4. Immutable Read-Only Agent Boundary

The agent operates under an immutable read-only security boundary enforced by code, schemas, and database permissions:

1. **Explicit Tool Allowlist Registry:** Only tools explicitly registered in `READ_ONLY_TOOL_REGISTRY` can execute.
2. **Schema Invariants:** Every tool argument is validated against a strict Pydantic model with `extra="forbid"`.
3. **Prohibited Capabilities:**
   - No generic SQL execution (`execute_sql`, `run_sql`).
   - No generic Cypher execution (`run_cypher`).
   - No dynamic code execution (`eval`, Python runtime, shell commands).
   - No data mutation statements (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`).
4. **Input Injection Defense:** `ForensicGuardrails.evaluate_input` detects instruction overrides, secret exfiltration, and prohibited tool requests while permitting educational discussions of SQL defense concepts.

---

## 5. Seven-Pillar Graph Intelligence Framework

When Neo4j evidence is retrieved, the response engine formats analytical findings across seven forensic pillars:

1. **Graph Structure:** Node types (`Account`, `Transaction`, `Device`, `IP`) and relationship types (`SENT`, `RECEIVED_BY`, `USED_DEVICE`, `USED_IP`).
2. **Observed Pattern:** Exact shared devices, shared IP subnets, counterparties, or multi-hop transfer paths.
3. **Risk Interpretation:** Potential financial crime typologies (account takeover, mule network coordination, circular funds flow).
4. **Alternative Explanations:** Legitimate explanations (household device sharing, corporate proxies, VPNs, shared family accounts).
5. **Evidence Strength:** Distinction between an isolated structural signal and corroborated multi-source evidence.
6. **Missing Evidence:** Clear disclosure that graph connectivity alone does not prove fraudulent intent, beneficial ownership, or criminal culpability.
7. **Recommended Investigation:** Next steps for an authorized human investigator (device fingerprinting, transaction ledger audit, KYC re-verification).

---

## 6. Verifiable Citation & Provenance Guarantees

Every citation emitted by the system must satisfy four strict verification checks in `validate_citations_and_results`:
- `evidence_id` exactly matches an item in the request's retrieved evidence set.
- `source_type` matches the original evidence source (`DOCUMENTS`, `POSTGRESQL`, `NEO4J`).
- `locator` matches the retrieved record ID or document section heading.
- Canonical SHA-256 content hash matches the retrieved content.

Unverified, mismatched, or fabricated citations are rejected and recorded in the forensic trace.
