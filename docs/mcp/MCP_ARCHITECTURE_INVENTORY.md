# Omerta.ai — MCP Architecture & Infrastructure Inventory

## 1. Executive Summary

Omerta.ai operates an advanced multi-agent financial fraud investigation and Anti-Money Laundering (AML) platform. The platform is architected around a dual-engine architecture:
- **Relational Ledger & Entity Store**: PostgreSQL (handling accounts, double-entry ledgers, transactions, audit logs, and knowledge chunks).
- **Graph Topology & Financial Relationships**: Neo4j (modeling financial transaction graphs, shared device networks, shared IP clusters, and mule rings).
- **Orchestration & Workflow**: LangGraph state machine orchestrating deterministic data gathering, specialized forensic analysis, and evidence-referenced LLM reporting.
- **Agent Integration Layer**: Model Context Protocol (MCP) servers exposing strictly read-only, sandboxed forensic tools to autonomous specialists and external LLMs.

This document establishes the comprehensive technical inventory of all MCP servers, their registered tools, database access patterns, specialist agent mappings, security invariants, identified weaknesses, and baseline test execution.

---

## 2. MCP Server Inventory

The platform hosts four standalone read-only MCP servers built on the Model Context Protocol (MCP stdio & JSON-RPC 2.0 protocol layer, integrated via `mcp.server.mcpserver.MCPServer`):

| Server ID | Server Name | Category | Primary Data Store | Total Tools | Status | Transport |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `transaction_server` | `omerta-transaction-server` | Ledger & Entities | PostgreSQL | 6 | Active | stdio / In-Process |
| `graph_server` | `omerta-graph-server` | Graph Topology | Neo4j | 6 | Active | stdio / In-Process |
| `risk_server` | `omerta-risk-server` | Risk & Machine Learning | PostgreSQL + Mock Provider | 4 | Active | stdio / In-Process |
| `knowledge_server` | `omerta-knowledge-server` | AML Policy & Regulations | PostgreSQL (TF-IDF Corpus) | 3 | Active | stdio / In-Process |
| **Total** | | | | **19 Tools** | | |

---

## 3. Comprehensive Tool Inventory & Server Mapping

### 3.1 Transaction MCP Server (`mcp_servers/transaction_server`)
- **Server Instance**: `server` in `mcp_servers.transaction_server.server`
- **Domain Service**: `domain.services.transaction_service.TransactionService`
- **Data Source**: PostgreSQL (`transactions`, `accounts`, `devices`, `ip_addresses`)
- **Read-Only Invariant**: Read queries via SQLAlchemy ORM / Core select statements.

| Tool Name | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `get_transaction` | `transaction_id: str` | `TransactionOut` | Retrieve full transaction facts (amount, currency, sender, recipient, device, IP, timestamps) by external ID. |
| `get_account` | `account_id: str` | `AccountOut` | Retrieve account facts, KYC customer details, risk tier, and balance facts by account ID. |
| `get_account_transactions` | `account_id: str`, `limit: int?` | `TransactionHistory` | Retrieve historical transactions where the account participated as sender or recipient (newest first). |
| `get_recipient_history` | `recipient_account_id: str`, `limit: int?` | `TransactionHistory` | Retrieve historical inbound transfers where the account acted as beneficiary (mule/layering pattern analysis). |
| `get_device_history` | `device_id: str`, `limit: int?` | `DeviceActivity` | Retrieve transaction history originating from a specific hardware device ID (identifies multi-account device sharing). |
| `get_ip_history` | `ip_address: str`, `limit: int?` | `IPActivity` | Retrieve transaction history originating from a specific IP address (identifies shared network infrastructure/VPN). |

### 3.2 Graph MCP Server (`mcp_servers/graph_server`)
- **Server Instance**: `server` in `mcp_servers.graph_server.server`
- **Domain Service**: `domain.services.graph_service.GraphService`
- **Data Source**: Neo4j Graph Database (Projected financial relationship graph)
- **Read-Only Invariant**: Read-only Cypher queries (`MATCH ... RETURN`).

| Tool Name | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `get_account_neighbors` | `account_id: str`, `limit: int?` | `AccountNeighborsOut` | Direct topological neighbors of an account node (connected accounts, transactions, devices, IP nodes). |
| `find_connected_accounts` | `account_id: str`, `limit: int?` | `ConnectedAccountsOut` | Accounts connected via 1-hop transactions, shared hardware devices, or common IP addresses. |
| `find_shared_devices` | `account_id: str`, `limit: int?` | `SharedDevicesOut` | Devices shared between the target account and other distinct accounts (syndicate signal). |
| `find_shared_ips` | `account_id: str`, `limit: int?` | `SharedIPsOut` | IP addresses shared between the target account and other distinct accounts (botnet/farm signal). |
| `find_transaction_paths` | `source_account_id: str`, `target_account_id: str`, `max_depth: int?` | `TransactionPathsOut` | Bounded multi-hop fund flow paths (1-5 depth) connecting originator and beneficiary accounts. |
| `find_fraud_ring` | `account_id: str`, `max_depth: int?`, `limit: int?` | `FraudRingSignalsOut` | Structural cluster signals (shared infrastructure, pass-through velocity) - returns structural evidence, not verdicts. |

### 3.3 Risk MCP Server (`mcp_servers/risk_server`)
- **Server Instance**: `server` in `mcp_servers.risk_server.server`
- **Domain Service**: `domain.services.risk_service.RiskService`
- **Data Source**: PostgreSQL facts + Deterministic Risk Scoring Provider (`mock-risk-v1`)
- **Read-Only Invariant**: Zero-write evaluation; derives risk features strictly from persisted database facts.

| Tool Name | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `get_risk_score` | `transaction_id: str` | `RiskScoreOut` | Deterministic transaction risk score with explicit provenance (`source=MOCK`, `model_version=mock-risk-v1`). |
| `get_risk_features` | `transaction_id: str` | `RiskFeatures` | Feature vector derived strictly from PostgreSQL facts (velocity, age, new device/IP markers). |
| `get_feature_importance` | `transaction_id: str` | `FeatureImportanceOut` | Feature contribution weights explaining the calculated score. |
| `get_previous_risk_events`| `account_id: str` | `PreviousRiskEventsOut`| Stored historical alerts and risk incidents for the target account (returns empty list if none). |

### 3.4 Knowledge MCP Server (`mcp_servers/knowledge_server`)
- **Server Instance**: `server` in `mcp_servers.knowledge_server.server`
- **Domain Service**: `domain.services.knowledge_service.KnowledgeService`
- **Data Source**: PostgreSQL (`knowledge_documents`, `knowledge_chunks`)
- **Read-Only Invariant**: Read-only TF-IDF deterministic keyword and section retrieval.

| Tool Name | Parameters | Return Type | Description |
| :--- | :--- | :--- | :--- |
| `search_knowledge` | `query: str`, `top_k: int?` | `KnowledgeSearchOut` | Deterministic TF-IDF keyword search over AML policies, FATF typologies, and regulations with complete citation provenance. |
| `get_document` | `document_id: str` | `KnowledgeDocumentOut` | Retrieve full regulatory or policy document text and metadata by document ID. |
| `get_document_section` | `document_id: str`, `section: str`| `KnowledgeSectionOut` | Retrieve an exact, isolated section of a knowledge document (e.g. Mule Account Typologies). |

---

## 4. Multi-Agent Architecture & Specialist-to-Tool Mapping

Omerta.ai deploys two complementary multi-agent orchestration architectures:
1. **LangGraph Investigation Pipeline** (`apps/investigator/`): A deterministic StateGraph executing 8 sequential stages, loading transaction facts, account context, graph topology, risk scores, and regulatory context before invoking the `InvestigatorAgent` for evidence-referenced synthesis.
2. **Phase 10 Forensic Specialist Swarm** (`domain/investigation/specialist_agents.py` & `history_agent.py`): Ten specialized forensic agents evaluating distinct facets of financial crime.

### Specialist-to-Tool Access Matrix

| Specialist Agent | Responsibility | Authorized MCP Tools | Prohibited Domains |
| :--- | :--- | :--- | :--- |
| **Transaction History Specialist** (`TransactionHistoryAgent`) | Analyzes 6 rolling velocity windows (5m, 15m, 60m, 24h, 7d, 30d). | `get_transaction`, `get_account_transactions`, `get_recipient_history` | Graph, Risk ML, Knowledge |
| **Banking Rules Specialist** (`BankingRulesAgent`) | Evaluates 16 deterministic statutory banking rules (`BANKING_RULES_REGISTRY`). | `get_transaction`, `get_account`, `get_previous_risk_events` | Graph, Cypher, Shell |
| **Behavioral Analysis Specialist** (`BehavioralAnalysisAgent`) | Evaluates baseline deviations, burst velocity, and volume anomalies. | `get_account`, `get_account_transactions` | Graph topology, Knowledge |
| **Account Takeover Specialist** (`AccountTakeoverAgent`) | Evaluates credential changes, new device/IP markers, and login anomalies. | `get_transaction`, `get_device_history`, `get_ip_history`, `get_risk_features` | Knowledge, Graph |
| **Device & Network Specialist** (`DeviceNetworkAgent`) | Analyzes device fingerprints, proxy/VPN networks, and IP subnet clusters. | `get_device_history`, `get_ip_history`, `find_shared_devices`, `find_shared_ips` | Risk scoring, Knowledge |
| **Graph Intelligence Specialist** (`GraphIntelligenceAgent`) | Analyzes Neo4j topology, multi-hop transaction paths, and mule rings. | `get_account_neighbors`, `find_connected_accounts`, `find_shared_devices`, `find_shared_ips`, `find_transaction_paths`, `find_fraud_ring` | Raw SQL, Shell, Knowledge |
| **ML Risk Specialist** (`MLRiskAgent`) | Evaluates LightGBM model inferences, feature importance, and risk features. | `get_risk_score`, `get_risk_features`, `get_feature_importance` | Graph queries, Shell |
| **Merchant Intelligence Specialist** (`MerchantIntelligenceAgent`) | Distinguishes P2P transfers from commercial merchant activity. | `get_account`, `get_account_transactions` | Graph, Risk ML |
| **Identity & Security Specialist** (`IdentitySecurityAgent`) | Checks KYC restrictions, compliance restrictions, and security tickets. | `get_account`, `get_previous_risk_events` | Graph, Cypher |
| **Final Decision Specialist** (`FinalDecisionAgent` / `InvestigatorAgent`) | Synthesizes all specialist findings, computes authoritative score, and issues report. | `search_knowledge`, `get_document`, `get_document_section` (+ read-only access to state evidence) | Any database mutation |

---

## 5. Database Access Patterns & Transports

### 5.1 PostgreSQL Access Pattern
- **Driver**: `asyncpg` via SQLAlchemy 2.0 Async Engine (`postgresql+asyncpg://...`).
- **Connection Management**:
  - `infrastructure/database/session.py` provides application-wide `get_engine()`.
  - MCP tools open a dedicated, short-lived `AsyncSession(get_engine(), expire_on_commit=False)` per tool call.
  - On error or completion, sessions are cleanly closed with explicit rollback.
- **Access Level**: ORM entity queries (`select(...)`) and repository abstractions (`infrastructure.database.repository`).

### 5.2 Neo4j Access Pattern
- **Driver**: `neo4j.AsyncGraphDatabase` (Bolt protocol).
- **Client Management**:
  - `infrastructure/neo4j/client.py` maintains an `AsyncDriver` instance.
  - Queries execute via async sessions: `async with driver.session() as session: result = await session.run(query, params)`.
  - Queries are fully parameterized; no string interpolation of identifiers.

---

## 6. Existing Security Mechanisms & Identified Weaknesses

### 6.1 Existing Security Mechanisms
1. **Parameterized Queries**: Domain repositories use SQLAlchemy ORM parameters and Neo4j Cypher parameters.
2. **Identifier & Limit Clamping**: `validate_external_id` (checks string type, max 64 chars) and `validate_limit` (clamped between 1 and 100).
3. **Structured Domain Errors**: Domain services catch missing entities and raise `NotFoundError` or `ValidationError` instead of leaking database errors.
4. **Information Leakage Prevention**: `_execute` wrappers catch uncaught exceptions and return generic `{"error": "INTERNAL_ERROR", "detail": "unexpected server error"}`, preventing stack traces and connection strings from reaching LLM callers.

### 6.2 Identified Weaknesses & Gaps
1. **Lack of MCP Adapter Defense-in-Depth**:
   - The security invariants currently rely entirely on lower-level service functions. The outer MCP tool functions accept raw string arguments without validating whether an adversarial prompt injection contains SQL manipulation, Cypher mutation, or shell execution attempts.
2. **Missing Token Optimization & Cursor Pagination**:
   - While a `limit` integer is supported, tools do not return standardized pagination metadata (`has_more`, `next_cursor`, `returned`, `total_estimate`). Large result sets can exhaust LLM context windows or bloat agent costs.
3. **Absence of Specialist Role-Based Scoping**:
   - Any agent or API caller connecting to an MCP server can currently invoke any tool. There is no caller-identity validation or least-privilege scoping enforced at the tool boundary.
4. **Inconsistent Error Response Envelopes**:
   - While `DomainError` returns `{"error": ...}`, other error paths return varying structures. Standardized machine-readable error codes (`TRANSACTION_NOT_FOUND`, `UNAUTHORIZED_TOOL_ACCESS`, `RESULT_LIMIT_EXCEEDED`, `PROHIBITED_MUTATION_ATTEMPT`) are needed.

---

## 7. Baseline Test Execution Results

Prior to making any modifications to the codebase, the existing test suite was executed to establish an empirical baseline:

- **Unit Test Execution (`tests/test_master_fraud_workflow.py -k "test_banking_rules_registry or test_specialist_agent_schemas"`)**:
  - **Status**: **PASSED** (2 passed, 7 deselected in 2.91s).
  - Confirmed: 16 banking rules registered and specialist agent schemas validate cleanly in-memory.

- **Existing MCP Protocol Tests (`tests/test_*_mcp.py`)**:
  - **Status**: **53 ERRORS (INFRASTRUCTURE LIMITED)**.
  - **Root Cause**: The existing tests (`test_transaction_mcp.py`, `test_graph_mcp.py`, `test_risk_mcp.py`, `test_knowledge_mcp.py`) define session-scoped database fixtures (`test_engine`, `seeded_sync`) that attempt a TCP socket connection to PostgreSQL at `127.0.0.1:15432` and Neo4j at `127.0.0.1:17687`. In the current local test environment, Docker Desktop is stopped and starting the service requires elevated Windows administrator rights.
  - **Mitigation & Plan**:
    1. Document the limitation per Execution Rule 18.
    2. Build automated MCP unit and protocol test suites (`tests/mcp/`) that thoroughly test all tool contracts, schemas, read-only guards, SQL/Cypher/shell injection resistance, token pagination, and specialist RBAC permissions without requiring external container dependencies, while remaining fully compatible with real databases when running in CI/Docker environments.

