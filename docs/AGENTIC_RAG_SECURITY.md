# Omerta.ai — Security Invariants, RBAC, and Artifact Protection

## 1. Non-Negotiable Security Invariants

The Agentic RAG system enforces rigid defensive architecture:

1. **No Arbitrary SQL:** The LLM is never provided with dynamic query generation or database console access. All queries use pre-compiled, parameterized SQLAlchemy queries with bounded limit clauses.
2. **No Arbitrary Cypher:** Graph queries are strictly parameterized functions with hard limits on traversal depth (`max_depth <= 3`) and node collection caps (`limit <= 25`).
3. **No Arbitrary Code Execution:** The LLM cannot execute Python scripts or shell commands. Mathematical calculations run in dedicated, hardened deterministic modules.
4. **No Autonomous Financial Actions:** The agent is 100% read-only. It cannot initiate transfers, modify balances, freeze accounts, or change ticket states.
5. **No Secret Leakage:** Groq API keys and database credentials remain exclusively on the server. They are never serialized into responses or exposed in frontend bundles.

---

## 2. Role-Based Access Control (RBAC)

Retrieval operations enforce the user's effective role extracted from the validated server-side JWT:

| Role | Knowledge Base Scope | Ledger Scope | Graph Scope |
| :--- | :--- | :--- | :--- |
| **ADMINISTRATOR** | Full document access | Full read access | Full read access |
| **SENIOR_INVESTIGATOR** | Full document access | Full read access | Full read access |
| **INVESTIGATOR / FRAUD_ANALYST** | Policies, Procedures, Typologies | Assigned transactions & accounts | Shared devices, IPs, hops |
| **AUDITOR** | Read-only compliance & policies | Read-only audit logs | Read-only topology |

---

## 3. Chart Artifact Delivery & Traversal Defense

Matplotlib charts are generated into `apps/api/static/artifacts/charts/` as high-resolution PNG images. Delivery is guarded by:

- **Strict Regex Validation:** Artifact IDs must strictly match `^[a-zA-Z0-9_\-]+$`.
- **Directory Traversal Protection:** Relative path sequences (`..`, `/`, `\`) are blocked with HTTP `400 Bad Request`.
- **Realpath Confinement:** The canonical file path is resolved and verified to reside inside `ARTIFACTS_DIR`.
- **JWT Authorization:** Artifact retrieval requires an authenticated user session.
