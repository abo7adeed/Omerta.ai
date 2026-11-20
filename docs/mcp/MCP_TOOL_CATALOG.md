# Omerta.ai — MCP Tool Catalog & Standardized Contracts

## 1. Overview & Standard Contract Specifications

The Omerta.ai Model Context Protocol (MCP) infrastructure provides 19 strictly read-only tools across 4 specialized servers. Each tool adheres to the following contract standards:

1. **Strict Read-Only Guarantee**: Zero state modification. All operations are non-destructive queries against PostgreSQL, Neo4j, or in-memory models.
2. **Deterministic Envelopes**: All outputs are JSON-serializable dictionaries conforming to Pydantic domain models.
3. **Bounded Collections**: Collection queries default to `limit=20` and clamp strictly to `MAX_LIMIT=100` to prevent token exhaustion.
4. **Actionable Error Envelopes**: Errors return machine-readable codes with contextual recovery guidance:
   ```json
   {
     "error": "ERROR_CODE",
     "detail": "Human-readable explanation.",
     "recovery": "Actionable instructions for the autonomous agent.",
     "resource": "Optional resource identifier"
   }
   ```
5. **Specialist Role-Based Access Control (RBAC)**: Tools enforce least-privilege scoping, permitting execution only to authorized specialist agents.

---

## 2. Transaction MCP Server (`omerta-transaction-server`)

### 2.1 `get_transaction`
- **Purpose**: Retrieve full factual record of a financial transaction.
- **When to Use**: When an investigation needs the base facts (amount, currency, status, sender, recipient, timestamp, device, IP) of a target transfer.
- **Parameters**:
  - `transaction_id` (`str`, required): The external transaction reference (e.g. `"TXN-001"`). Must match regex `^[A-Za-z0-9_\-\.]{1,64}$`.
- **Output Schema**:
  ```json
  {
    "transaction_id": "TXN-001",
    "sender": { "external_id": "ACC-1001", "customer_name": "Alice Smith", "country": "US", "risk_level": "LOW" },
    "recipient": { "external_id": "ACC-9001", "customer_name": "Bob Jones", "country": "US", "risk_level": "HIGH" },
    "amount": "8400.00",
    "currency": "USD",
    "transaction_type": "WIRE",
    "status": "COMPLETED",
    "timestamp": "2026-10-12T14:30:00Z",
    "device": { "external_id": "DEV-123", "device_type": "MOBILE", "risk_level": "MEDIUM" },
    "ip": { "address": "192.0.2.1", "country": "US", "risk_level": "LOW" },
    "is_new_device": true,
    "is_new_ip": true,
    "data_source": "POSTGRES"
  }
  ```
- **Error Codes**: `TRANSACTION_NOT_FOUND`, `VALIDATION_ERROR`, `PROHIBITED_MUTATION_ATTEMPT`.
- **Recovery Guidance**: "Verify the transaction ID format. Ensure the transaction exists in the ledger before retrying."
- **Authorized Specialists**: `TransactionHistoryAgent`, `BankingRulesAgent`, `AccountTakeoverAgent`, `FinalDecisionAgent`, `InvestigatorAgent`.

### 2.2 `get_account`
- **Purpose**: Retrieve account ledger state, KYC customer details, and risk status.
- **When to Use**: To assess an account's overall posture, account age, balance, and KYC risk level.
- **Parameters**:
  - `account_id` (`str`, required): The external account identifier (e.g. `"ACC-1001"`).
- **Output Schema**:
  ```json
  {
    "account_id": "ACC-1001",
    "customer_name": "Alice Smith",
    "account_type": "CHECKING",
    "country": "US",
    "created_at": "2025-01-15T09:00:00Z",
    "status": "ACTIVE",
    "risk_level": "LOW",
    "data_source": "POSTGRES"
  }
  ```
- **Error Codes**: `ACCOUNT_NOT_FOUND`, `VALIDATION_ERROR`.
- **Recovery Guidance**: "Check the account identifier syntax. If looking up by customer name, resolve account ID first."
- **Authorized Specialists**: `BankingRulesAgent`, `BehavioralAnalysisAgent`, `MerchantIntelligenceAgent`, `IdentitySecurityAgent`, `FinalDecisionAgent`.

### 2.3 `get_account_transactions`
- **Purpose**: Retrieve chronological transaction history for an account (newest first).
- **When to Use**: To analyze account spending patterns, calculate velocity, and spot burst activity.
- **Parameters**:
  - `account_id` (`str`, required): The external account identifier.
  - `limit` (`int`, optional, default 20, max 100): Number of transactions to return.
  - `cursor` (`str`, optional): Pagination cursor from prior response.
- **Output Schema**:
  ```json
  {
    "items": [
      {
        "transaction_id": "TXN-001",
        "amount": "8400.00",
        "currency": "USD",
        "sender_account_id": "ACC-1001",
        "recipient_account_id": "ACC-9001",
        "transaction_type": "WIRE",
        "status": "COMPLETED",
        "timestamp": "2026-10-12T14:30:00Z",
        "is_new_device": true,
        "is_new_ip": true
      }
    ],
    "count": 1,
    "limit": 20,
    "truncated": false,
    "pagination": { "returned": 1, "has_more": false, "next_cursor": null }
  }
  ```
- **Error Codes**: `ACCOUNT_NOT_FOUND`, `RESULT_LIMIT_EXCEEDED`, `INVALID_PAGINATION_CURSOR`.
- **Authorized Specialists**: `TransactionHistoryAgent`, `BehavioralAnalysisAgent`, `MerchantIntelligenceAgent`, `FinalDecisionAgent`.

### 2.4 `get_recipient_history`
- **Purpose**: Retrieve historical transfers where the target account was the beneficiary.
- **When to Use**: Specifically to detect mule layering, funnel accounts, or sudden aggregation of incoming funds.
- **Parameters**:
  - `recipient_account_id` (`str`, required): Beneficiary account identifier.
  - `limit` (`int`, optional, default 20, max 100): Maximum rows to return.
- **Output Schema**: Identical envelope to `get_account_transactions`.
- **Error Codes**: `ACCOUNT_NOT_FOUND`, `RESULT_LIMIT_EXCEEDED`.
- **Authorized Specialists**: `TransactionHistoryAgent`, `BehavioralAnalysisAgent`, `FinalDecisionAgent`.

### 2.5 `get_device_history`
- **Purpose**: Retrieve transactions executed from a specific hardware device.
- **When to Use**: To determine if a device has been used across multiple distinct accounts (syndicate / bot device).
- **Parameters**:
  - `device_id` (`str`, required): Hardware device ID (e.g. `"DEV-123"`).
  - `limit` (`int`, optional, default 20, max 100).
- **Output Schema**:
  ```json
  {
    "device_id": "DEV-123",
    "items": [...],
    "count": 3,
    "unique_accounts": ["ACC-1001", "ACC-2002"]
  }
  ```
- **Authorized Specialists**: `AccountTakeoverAgent`, `DeviceNetworkAgent`, `FinalDecisionAgent`.

### 2.6 `get_ip_history`
- **Purpose**: Retrieve transactions executed from a specific IP address.
- **When to Use**: To analyze IP concentration, cloud hosting exits, or VPN proxy usage.
- **Parameters**:
  - `ip_address` (`str`, required): IPv4 or IPv6 address.
  - `limit` (`int`, optional, default 20, max 100).
- **Authorized Specialists**: `AccountTakeoverAgent`, `DeviceNetworkAgent`, `FinalDecisionAgent`.

---

## 3. Graph MCP Server (`omerta-graph-server`)

### 3.1 `get_account_neighbors`
- **Purpose**: Retrieve immediate topological neighbors of an account node in Neo4j.
- **When to Use**: Initial exploration of an account's graph cluster.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
  - `limit` (`int`, optional, default 20, max 100).
- **Output Schema**: Returns lists of connected `accounts`, `transactions`, `devices`, and `ips`.
- **Authorized Specialists**: `GraphIntelligenceAgent`, `FinalDecisionAgent`.

### 3.2 `find_connected_accounts`
- **Purpose**: Discover other accounts linked to the target by direct transaction, shared device, or shared IP.
- **When to Use**: To uncover hidden relationships and common infrastructure between seemingly unrelated entities.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
  - `limit` (`int`, optional, default 20, max 100).
- **Authorized Specialists**: `GraphIntelligenceAgent`, `FinalDecisionAgent`.

### 3.3 `find_shared_devices`
- **Purpose**: Find devices used by the target account that are also linked to other customer accounts.
- **When to Use**: Multi-accounting and fraud ring detection.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
  - `limit` (`int`, optional, default 20, max 100).
- **Authorized Specialists**: `DeviceNetworkAgent`, `GraphIntelligenceAgent`, `FinalDecisionAgent`.

### 3.4 `find_shared_ips`
- **Purpose**: Find IP addresses shared between the target account and other customer accounts.
- **When to Use**: Identifying bot farms, organized fraud rings, or shared VPN infrastructure.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
  - `limit` (`int`, optional, default 20, max 100).
- **Authorized Specialists**: `DeviceNetworkAgent`, `GraphIntelligenceAgent`, `FinalDecisionAgent`.

### 3.5 `find_transaction_paths`
- **Purpose**: Discover bounded multi-hop fund flow paths between two accounts in Neo4j.
- **When to Use**: Tracing funds through intermediary mule accounts or layering chains.
- **Parameters**:
  - `source_account_id` (`str`, required): Originator account.
  - `target_account_id` (`str`, required): Beneficiary account.
  - `max_depth` (`int`, optional, default 2, min 1, max 5): Traversal hop limit.
- **Output Schema**:
  ```json
  {
    "source_account_id": "ACC-1001",
    "target_account_id": "ACC-9001",
    "max_depth": 3,
    "paths": [
      { "length": 2, "nodes": ["ACC-1001", "ACC-5005", "ACC-9001"], "total_amount": "8400.00" }
    ]
  }
  ```
- **Authorized Specialists**: `GraphIntelligenceAgent`, `FinalDecisionAgent`.

### 3.6 `find_fraud_ring`
- **Purpose**: Detect structural clustering signals (shared hardware, shared IP, pass-through nodes).
- **When to Use**: Comprehensive syndicate and mule ring analysis.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
  - `max_depth` (`int`, optional, default 2, max 5).
  - `limit` (`int`, optional, default 20, max 100).
- **Authorized Specialists**: `GraphIntelligenceAgent`, `FinalDecisionAgent`.

---

## 4. Risk MCP Server (`omerta-risk-server`)

### 4.1 `get_risk_score`
- **Purpose**: Obtain deterministic transaction risk score and classification.
- **When to Use**: To obtain initial rule-based risk baseline (`LOW`, `MEDIUM`, `HIGH`).
- **Parameters**:
  - `transaction_id` (`str`, required): Target transaction ID.
- **Output Schema**:
  ```json
  {
    "transaction_id": "TXN-001",
    "risk_score": 0.85,
    "risk_level": "HIGH",
    "source": "MOCK",
    "model_version": "mock-risk-v1",
    "seeded_alert": "ALERT-001"
  }
  ```
- **Authorized Specialists**: `MLRiskAgent`, `FinalDecisionAgent`.

### 4.2 `get_risk_features`
- **Purpose**: Retrieve fact-derived risk features extracted strictly from PostgreSQL records.
- **When to Use**: To inspect the numerical and categorical inputs that feed risk models.
- **Parameters**:
  - `transaction_id` (`str`, required): Target transaction ID.
- **Authorized Specialists**: `MLRiskAgent`, `AccountTakeoverAgent`, `FinalDecisionAgent`.

### 4.3 `get_feature_importance`
- **Purpose**: Retrieve feature importance weights explaining the risk score calculation.
- **When to Use**: For explainability in SAR filing and forensic reporting.
- **Parameters**:
  - `transaction_id` (`str`, required): Target transaction ID.
- **Authorized Specialists**: `MLRiskAgent`, `FinalDecisionAgent`.

### 4.4 `get_previous_risk_events`
- **Purpose**: Retrieve prior historical alerts and suspicious activity reports for an account.
- **When to Use**: Checking recidivism or ongoing suspicious behavior.
- **Parameters**:
  - `account_id` (`str`, required): Target account ID.
- **Authorized Specialists**: `BankingRulesAgent`, `IdentitySecurityAgent`, `FinalDecisionAgent`.

---

## 5. Knowledge MCP Server (`omerta-knowledge-server`)

### 5.1 `search_knowledge`
- **Purpose**: Deterministic TF-IDF keyword retrieval over curated AML laws, regulations, and FATF typologies.
- **When to Use**: When an agent needs statutory AML thresholds, FATF red flags, or regulatory definitions.
- **Parameters**:
  - `query` (`str`, required, max 512 chars): Search query string.
  - `top_k` (`int`, optional, default 3, max 10): Number of relevant sections to retrieve.
- **Output Schema**:
  ```json
  {
    "query": "mule account layering",
    "top_k": 3,
    "total_found": 1,
    "results": [
      {
        "document_id": "DOC-FATF-TYPOLOGIES",
        "title": "FATF Guidance on Money Laundering Typologies",
        "section": "Mule Accounts",
        "jurisdiction": "GLOBAL",
        "effective_date": "2023-01-01",
        "version": "1.0",
        "content": "Mule accounts are characterized by rapid inbound transfers followed by immediate outbound dissipation...",
        "score": 0.82
      }
    ]
  }
  ```
- **Authorized Specialists**: `FinalDecisionAgent`, `InvestigatorAgent`.

### 5.2 `get_document`
- **Purpose**: Retrieve an entire regulatory or policy document by identifier.
- **When to Use**: When full context of an AML framework (e.g. BSA, FinCEN guidelines) is required.
- **Parameters**:
  - `document_id` (`str`, required): Document reference (e.g. `"DOC-FATF-TYPOLOGIES"`).
- **Authorized Specialists**: `FinalDecisionAgent`, `InvestigatorAgent`.

### 5.3 `get_document_section`
- **Purpose**: Retrieve a specific section of a stored knowledge document.
- **When to Use**: Targeted extraction of specific statutory clauses or AML thresholds.
- **Parameters**:
  - `document_id` (`str`, required): Document reference.
  - `section` (`str`, required): Section heading.
- **Authorized Specialists**: `FinalDecisionAgent`, `InvestigatorAgent`.

