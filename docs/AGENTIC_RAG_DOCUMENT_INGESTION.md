# Omerta.ai — Banking Knowledge Base, Ingestion Pipeline & RBAC Retrieval

## 1. Corpus Architecture & Authoritative Starter Documents

The Knowledge Base houses simulated banking policies, procedures, and regulatory guidance across six essential operational domains:

1. **Banking Operations Policy & Ledger Standards (`DOC-OPS-001`, Version 2):**
   - **Section 1:** Account Lifecycle and Account Status (ACTIVE, DORMANT, SUSPENDED, BLOCKED, CLOSED, KYC rules).
   - **Section 2:** Transfer Processing and Double-Entry Accounting (`account_ledger_entries`, atomic concurrency, row-level locks).
   - **Section 3:** Transaction Limits and Verification (Daily ceilings, structuring, and smurfing velocity indicators).
   - **Section 4:** Security Holds and Access Restoration (3 consecutive password strikes, non-logout BLOCKED state, manual restoration protocol).
   - **Section 5:** Reconciliation and Audit Procedures (Ledger balance verification, settlement exception resolution).
2. **Identity & Account Security (`DOC-SEC-001`):** MFA enforcement, failed password lockouts, device fingerprinting, and security hold restoration.
3. **AML / CFT & Financial Crime Intelligence (`DOC-AML-001`):** Structuring indicators, smurfing typologies, rapid inflow/outflow bursts, mule networks, and mandatory FATF Red Flags.
4. **Compliance & Forensic Case Management (`DOC-CMP-001`):** Evidence sufficiency requirements, four-eyes review, case closure thresholds, and supervisory escalations.
5. **AI Investigation Governance (`DOC-GOV-001`):** Permitted uses of AI, non-accusatory findings, citation requirements, and human-in-the-loop compliance decisions.
6. **System & Data Classification (`DOC-SYS-001`):** Role-based access control (RBAC), data classification levels, audit trail immutability, and retention periods.

All documents are stored in markdown format in `infrastructure/knowledge/documents/` with YAML frontmatter specifying `document_id`, `version`, `allowed_roles`, and `classification`.

---

## 2. Role-Based Access Control (RBAC) & Metadata Filtering

Every document defines an authorized audience in its YAML frontmatter:
```yaml
document_id: DOC-OPS-001
version: 2
classification: INTERNAL
allowed_roles: ["CUSTOMER", "FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
```

During retrieval:
- `user_role` is passed from the server-side JWT authentication context.
- If the user's role is not present in `allowed_roles` (and is not `ADMINISTRATOR`), the candidate chunk is dropped prior to reranking and narrative synthesis.
- Unauthorized roles receive an empty result set—restricted content never reaches the LLM context.

---

## 3. Retrieval Safeguards & Relevance Thresholds

To eliminate fabricated citations and irrelevant context stuffing:
1. **Relevance Threshold:** Chunks with lexical similarity score below `0.05` are filtered out.
2. **Zero Padding Rule:** If no indexed section meets the threshold, retrieval returns an empty list. The narrative engine is instructed to honestly report insufficient evidence rather than padding with unrelated chunks.
3. **Admin Debug Mode (`search_documents_debug`):** Available to authorized administrators to inspect candidate counts, query normalization, similarity scores, and RBAC filtering decisions without leaking unauthorized text.
4. **Exact Section Retrieval (`get_document_section`):** Supports deterministic direct lookup of specific document IDs and section titles (e.g., `DOC-OPS-001` Section 2).

---

## 4. Ingestion Command Line

To ingest or re-index the starter corpus:

```powershell
uv run python -m infrastructure.knowledge.ingest
```
Or via script:
```powershell
uv run python -c "import asyncio, pathlib; from infrastructure.database.session import get_engine; from sqlalchemy.ext.asyncio import AsyncSession; from infrastructure.knowledge.ingest import ingest_starter_corpus; asyncio.run(ingest_starter_corpus(AsyncSession(get_engine(), expire_on_commit=False), pathlib.Path('infrastructure/knowledge/documents').resolve()))"
```
