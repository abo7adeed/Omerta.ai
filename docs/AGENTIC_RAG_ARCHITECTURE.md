# Omerta.ai — Agentic RAG Architecture & System Topology

## 1. Executive Summary

The Omerta.ai Agentic RAG and AI Financial Analyst platform extends the core anti-financial-crime engine into an interactive, multi-source cognitive copilot. Designed specifically for forensic investigators and compliance officers, the system combines structured relational banking ledgers, entity relationship graph topology, curated regulatory and policy documents, and deterministic mathematical calculations into a single, evidence-grounded workflow.

LLMs are never permitted to execute free-form arbitrary SQL, unrestricted Cypher, or raw Python. Instead, language models (hosted on Groq or local test mocks) are strictly bounded to semantic intent interpretation, parameter extraction, and final structured narrative synthesis. All analytical metrics and charts are computed deterministically.

---

## 2. Logical Architecture

```text
                           Authenticated User
                                    │
                                    ▼
                      Omerta.ai Frontend (React / Vite)
                                    │
                                    ▼
                 FastAPI Endpoint (/api/v1/agentic-rag/query)
                                    │
                         Authentication + RBAC
                                    │
                                    ▼
                     LangGraph Orchestrator Workflow
    ┌───────────────────────────────┼───────────────────────────────┐
    ▼                               ▼                               ▼
Document RAG (TF-IDF)       PostgreSQL Ledger                Neo4j Graph
• Operations Manuals        • Transactions & Balances       • Shared Devices & IPs
• AML/CFT Typologies        • Accounts & Customers          • Fund Flow Paths
• Security Directives       • Time-range Aggregates         • Co-located Accounts
    └───────────────────────────────┬───────────────────────────────┘
                                    │
                                    ▼
                          Normalized Evidence
                         (SHA-256 Provenance)
                                    │
                                    ▼
                         Evidence Sufficiency Gate
                                    │
            ┌───────────────────────┴───────────────────────┐
            ▼                                               ▼
Deterministic Analytics Service               Groq Synthesis / Fallback
• Sums, Counts, Averages                      • Structured Narrative
• Safe % Change (zero-guard)                  • Verifiable Citations
• Anomaly Standard Deviations                 • Response Blocks
            │                                               │
            ▼                                               ▼
Matplotlib Visualization Engine                    Strict Citation Verification
• Sapphire & Gold Styling                                   │
• Secure Disk Artifacts                                     │
            └───────────────────────┬───────────────────────┘
                                    │
                                    ▼
                      AgenticRAGResponse (Pydantic)
                                    │
                                    ▼
             Inline Rich Rendering (KPIs, Tables, Charts)
```

---

## 3. Core Subsystems

### 3.1 LangGraph Orchestration State Machine (`apps/agentic_rag/`)
The decision pipeline is modeled as an inspectable, deterministic state graph:
- `validate_request`: Performs boundary checks, extracts entity tokens (e.g., `TXN-001`, `ACC-1001`, `DEV-001`).
- `resolve_identity_and_permissions`: Reads server-side authentication context, enforces user roles.
- `understand_query_and_intent`: Routes to relevant sources using word-boundary NLP and regex heuristics.
- `retrieve_selected_sources`: Concurrently or conditionally queries Document RAG, PostgreSQL, and Neo4j.
- `normalize_evidence`: Converts heterogeneous payloads into `NormalizedEvidence` with cryptographic content hashes.
- `rerank_document_evidence`: Reranks policy chunks using TF-IDF cosine similarity, title overlap, and exact phrase matching.
- `check_evidence_sufficiency`: Evaluates whether retrieved data satisfies user intent.
- `execute_validated_analysis`: Computes statistics, time-series aggregations, and percentage changes deterministically.
- `generate_chart_if_required`: Renders high-resolution PNG charts via Matplotlib and registers secure artifact IDs.
- `synthesize_structured_response`: Invokes Groq LLM (or deterministic fallback) with strict citation instructions.
- `validate_citations_and_results`: Validates that 100% of generated citations map directly to verified evidence.

### 3.2 Information Sources
1. **Document Knowledge Base:** Curated internal banking documents indexed into PostgreSQL `knowledge_documents` and `knowledge_chunks` tables.
2. **PostgreSQL Relational Ledger:** Authoritative source of financial truth. Read-only parameterized service methods.
3. **Neo4j Graph Topology:** Derived graph projection representing accounts, shared devices, shared IP subnets, and transaction transfer hops.
4. **Deterministic Analytics Engine:** Python `Decimal` and `float` calculations with zero-division protection and strict rounding.
