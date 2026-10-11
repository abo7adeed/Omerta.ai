# Omerta.ai — Agentic RAG Security Model & Tool Registry Protection

## 1. Immutable Read-Only Security Boundary

The AI Assistant is an analytical investigation copilot with an immutable read-only boundary. Under no circumstances can the model modify financial balances, execute mutations, change ticket statuses, or bypass authorization.

### Prohibited Capabilities
- **No Arbitrary SQL:** The LLM cannot formulate, pass, or execute arbitrary SQL strings (`execute_sql`, `raw_sql`, etc. are blocked at registry level).
- **No Arbitrary Cypher:** Unrestricted Cypher queries are strictly prohibited. Graph retrieval is limited to parameterized functions with bounded depth (`max_depth <= 3`) and collection limits (`limit <= 25`).
- **No Arbitrary Code Execution:** Execution of Python code, shell commands, `eval`, or dynamic code is completely non-existent.
- **No Mutation Statements:** Statements containing `INSERT`, `UPDATE`, `DELETE`, `DROP`, `TRUNCATE`, `ALTER`, `GRANT`, or `REVOKE` are blocked with `AgentToolExecutionError(code="MUTATION_PROHIBITED")`.

---

## 2. Tool Allowlist Registry (`domain/agentic_rag/tools/registry.py`)

All model tool invocations are dispatched through `invoke_agent_tool`. The registry maintains an explicit allowlist of 21 typed read-only tools:

### Approved Tools
1. **Document Tools:** `search_documents`, `get_document_section`, `get_document_metadata`, `search_documents_debug`.
2. **PostgreSQL Tools:** `get_transaction`, `get_account`, `get_customer`, `find_customers_by_name`, `get_transaction_summary`, `get_risk_distribution`, `compare_transaction_periods`, `get_bounded_transaction_dataset`, `get_customer_sessions`, `get_investigation_case_summary`.
3. **Neo4j Graph Tools:** `find_connected_accounts`, `get_shared_devices`, `get_shared_ips`, `find_transaction_paths`, `summarize_account_network`, `find_fraud_signals`, `get_graph_schema_overview`.

### Argument Validation Invariants
- Every tool is bound to a strict Pydantic argument schema with `model_config = ConfigDict(extra="forbid")`.
- Extra parameters, unknown fields, oversized limits, and invalid entity prefixes trigger immediate rejection.

---

## 3. Input & Output Forensic Guardrails

The guardrail engine (`domain/agentic_rag/guardrails.py`) enforces:
1. **Instruction Override & Jailbreak Defense:** Rejects attempts to ignore system guidelines, exfiltrate credentials, or request mutation capabilities.
2. **Educational Inquiry Distinction:** Permits legitimate analyst questions discussing database concepts (e.g., *"How does Omerta protect against SQL injection attacks like DROP TABLE?"*) while blocking actual execution payloads.
3. **PII and PAN Masking:** Credit/debit card numbers matching payment PAN regexes are automatically redacted to `****-****-****-****` before LLM processing.
4. **Non-Accusatory Output Safety:** Replaces inflammatory terms (e.g., "criminal", "fraudster") with objective forensic phrasing ("individual under investigation", "subject").

---

## 4. Multi-Tenant Session Security & Isolation

Conversational memory is secured against unauthorized cross-user access:
- **Server-Side Identity:** User identity is extracted exclusively from the authenticated JWT token (`sub`), never trusted from client payloads.
- **Strict User Isolation:** `AgenticMemoryManager.get_session`, `list_user_sessions`, and `delete_session` require matching `user_id`. Users cannot list, inspect, or delete another investigator's sessions.
- **Path Traversal Defense:** Session IDs are strictly validated with `^[a-zA-Z0-9_\-]+$`. Relative path sequences (`..`, `/`, `\`) raise validation errors and are rejected.

---

## 5. Chart Artifact Authorization

Matplotlib vector charts stored in `apps/api/static/artifacts/charts/` are served via `/api/v1/agentic-rag/artifacts/{artifact_id}`:
- **Path Confinement:** Resolved paths are verified to strictly reside within `ARTIFACTS_DIR`.
- **Regex Validation:** Artifact identifiers must match `^[a-zA-Z0-9_\-]+$`.
- **JWT Protection:** Unauthenticated requests receive HTTP 401.
