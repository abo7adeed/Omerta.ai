# Omerta.ai — MCP Security Architecture & Invariant Specifications

## 1. Security Invariant & Zero-Write Policy

Omerta.ai is a high-assurance financial fraud and AML platform. Because autonomous LLMs and specialist agents execute tools dynamically to gather evidence, the MCP infrastructure enforces a non-negotiable **Strict Read-Only Invariant**:

> **THE STRICT READ-ONLY INVARIANT**:
> No agent, workflow, MCP tool, or external caller shall ever be capable of altering, inserting, updating, deleting, or compromising financial ledgers, transactional histories, graph topologies, risk stores, or system configurations through the MCP interface.

Every MCP tool is strictly an information-gathering sensor. State modifications (such as case status changes, restriction freezes, SAR filings, and ledger double-entry bookkeeping) can **only** be executed through authenticated, audited administrative workflow endpoints that require explicit human approval.

---

## 2. Prohibited Operations Matrix

The following operations are categorically prohibited and actively blocked across all layers:

### 2.1 PostgreSQL Prohibited Operations
- `INSERT` (Record creation)
- `UPDATE` (Record mutation)
- `DELETE` (Record deletion)
- `DROP` (Schema/Table destruction)
- `ALTER` (Schema mutation)
- `TRUNCATE` (Table purging)
- `CREATE` (Object creation)
- `GRANT` / `REVOKE` (Permission tampering)
- Arbitrary raw SQL execution or multi-statement batching (`--`, `;`, `UNION SELECT`)

### 2.2 Neo4j Prohibited Operations
- `CREATE` (Node / Relationship creation)
- `MERGE` (Conditional upsert)
- `SET` (Property / Label modification)
- `DELETE` / `DETACH DELETE` (Graph pruning)
- `REMOVE` (Property / Label removal)
- `DROP` (Constraint / Index deletion)
- Arbitrary Cypher execution or administrative procedures (`CALL dbms...`, `CALL apoc.cypher.run...`)

### 2.3 Operating System & Subprocess Prohibited Operations
- Shell execution (`powershell.exe`, `cmd.exe`, `sh`, `bash`, `zsh`)
- Subprocess invocation (`subprocess.Popen`, `os.system`, `os.spawn`)
- Filesystem writes / deletions outside temporary test sandbox
- Environment variable mutation or credential retrieval (`os.environ`)
- Network socket binding or reverse tunneling

---

## 3. Defense-in-Depth Architecture

To guarantee the read-only invariant against prompt injections, adversarial hallucinations, and zero-day tool exploits, Omerta.ai implements a 5-tier defense-in-depth model:

```
[ Tier 1: Agent Prompt & Contract Boundary ]
                   │
                   ▼
[ Tier 2: MCP Adapter Input Validation & Pattern Defense ]
  - Regex syntax checks on identifiers
  - Prohibited mutation keyword rejection (SQL / Cypher / Shell)
  - Result limit clamping (max 100)
                   │
                   ▼
[ Tier 3: Specialist Role-Based Scoping (RBAC) ]
  - Caller identity & specialist role verification
  - Least-privilege matrix enforcement
                   │
                   ▼
[ Tier 4: Domain Service & ORM Query Parameterization ]
  - Typed Pydantic schema validation
  - SQLAlchemy 2.0 async select statements only
  - Neo4j parameterized Cypher drivers (Zero string concatenation)
                   │
                   ▼
[ Tier 5: Database Connection Sandboxing & Transaction Rollback ]
  - Dedicated short-lived read sessions
  - Explicit rollback in `finally` blocks
  - Database user connection roles restricted to SELECT in production
```

---

## 4. Injection Defense Specifications

### 4.1 SQL Injection & Mutation Defense
All tool arguments undergo pattern matching against regex and token scanners in `mcp_servers/common/security.py`:
- Rejects any input containing SQL mutation verbs: `\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE)\b` (case-insensitive).
- Rejects SQL comment characters and statement delimiters: `;`, `--`, `/*`, `*/`.
- Rejects SQL extraction keywords: `UNION\s+ALL\s+SELECT`, `UNION\s+SELECT`, `INFORMATION_SCHEMA`.

### 4.2 Cypher Injection & Mutation Defense
Graph parameters (e.g. `account_id`, `source_account_id`, `target_account_id`) are validated to ensure:
- Strict alphanumeric and delimiter conformity: `^[A-Za-z0-9_\-\.]{1,64}$`.
- Rejection of Cypher write keywords: `\b(CREATE|MERGE|SET|DELETE|DETACH|REMOVE|DROP)\b`.
- Rejection of procedure execution: `\bCALL\b`, `\bapoc\b`, `\bdbms\b`.

### 4.3 Shell & Subprocess Execution Defense
Arguments are scanned for OS command injection vectors:
- Rejection of command chaining characters: `&`, `|`, `;`, `$`, `` ` ``, `\n`.
- Rejection of directory traversal: `../`, `..\\`.
- Rejection of binary / interpreter invocations: `powershell`, `cmd`, `bash`, `sh`, `curl`, `wget`, `python`.

---

## 5. Specialist Role-Based Access Control (RBAC)

To implement the principle of least privilege, each forensic specialist agent is assigned an explicit permission profile:

```
Specialist Agent                 Authorized MCP Tool Groups
──────────────────────────────   ────────────────────────────────────────────────
TransactionHistoryAgent       -> Transaction Server (get_transaction, get_account_transactions, get_recipient_history)
BankingRulesAgent             -> Transaction Server (get_transaction, get_account), Risk Server (get_previous_risk_events)
BehavioralAnalysisAgent       -> Transaction Server (get_account, get_account_transactions)
AccountTakeoverAgent          -> Transaction Server (get_transaction, get_device_history, get_ip_history), Risk Server (get_risk_features)
DeviceNetworkAgent            -> Transaction Server (get_device_history, get_ip_history), Graph Server (find_shared_devices, find_shared_ips)
GraphIntelligenceAgent        -> Graph Server (ALL 6 graph tools)
MLRiskAgent                   -> Risk Server (get_risk_score, get_risk_features, get_feature_importance)
MerchantIntelligenceAgent     -> Transaction Server (get_account, get_account_transactions)
IdentitySecurityAgent         -> Transaction Server (get_account), Risk Server (get_previous_risk_events)
FinalDecisionAgent            -> Knowledge Server (ALL 3 knowledge tools), Read access to shared state evidence
```

If an agent attempts to invoke a tool outside its authorized scope, the tool interceptor immediately halts execution and returns:
```json
{
  "error": "UNAUTHORIZED_TOOL_ACCESS",
  "detail": "Specialist 'BankingRulesAgent' is not authorized to execute tool 'find_fraud_ring'.",
  "recovery": "Refer to the specialist permission matrix. Request analysis from GraphIntelligenceAgent."
}
```

---

## 6. Audit Trail & Observability

Every tool execution emits an immutable audit event:
1. **In-Memory Ring Buffer**: `MCP_AUDIT_LOG` captures the last 50 calls for live visualization in the administrative UI.
2. **Distributed Tracing (Langfuse)**: Captures caller ID, arguments, execution duration, and sanitized return payloads.
3. **Structured Logging**: Emits machine-readable logs with `investigation_id`, `tool_name`, and latency metrics, while strictly suppressing passwords, hashes, API keys, and PII.

