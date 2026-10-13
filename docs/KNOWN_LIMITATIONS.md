# ⚠️ Omerta.ai — Known Limitations & Operational Considerations

**Release Version:** v2.0-rc  
**Last Updated:** October 2026  

---

## 1. External Infrastructure & Third-Party Providers

1. **Third-Party Commercial VPN / Threat Intelligence IP APIs**:
   - The platform includes rule-based telemetry evaluation and local ASN/ISP matching (`evaluate_vpn_risk`).
   - Live integration with external enterprise IP intelligence providers (e.g., MaxMind GeoIP2 Precision, IPQualityScore, Spur.us) requires customer-provided API credentials configured in environment variables (`GEOIP_API_KEY`, `IPQS_API_KEY`).
   - When external provider credentials are not set, the platform fails safely into local heuristic detection rather than assuming the connection is clean.

2. **Graph Database Projection (Neo4j)**:
   - While all core financial transactions, balances, and ledger entries reside exclusively in PostgreSQL as the authoritative source of truth, multi-hop visualization (`/network`) relies on projected graph topology in Neo4j.
   - If Neo4j is temporarily stopped or unreachable, the graph intelligence agent degrades gracefully, logging `AgentExecutionStatus.DEGRADED`, and the core banking ledger continues to operate without interruption.

3. **Live SMTP Mail Delivery**:
   - Live email delivery for confirmation links (`TransactionConfirmationToken`) relies on configured SMTP credentials (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`).
   - In offline test environments or when SMTP credentials are unset, the service generates and logs single-use token hashes in local audit logs while returning tokens in test receipts to facilitate end-to-end integration testing.

4. **Production LLM / Agentic RAG Service**:
   - Multi-agent forensic dossier generation (LangGraph) can run with remote providers (Gemini, OpenAI, Groq) or local Ollama instances.
   - In offline demonstrations without external API keys configured, deterministic specialist risk scoring and rule engines provide the complete risk evaluation.

---

## 2. Browser & Development Limitations

1. **Local Vite Dev Server Port Co-Existence**:
   - The development environment defaults frontend to port `5173` and backend FastAPI to port `8000`.
   - The explicit CORS whitelist in `apps/api/main.py` is configured for ports `5173`, `3000`, and `8000`. Custom domain deployments require updating `ALLOWED_ORIGINS` via environment variables.

2. **Single-Session Policy**:
   - By design, logging in from a new device invalidates the prior active session for the same user to prevent credential sharing and session hijacking.
   - Users testing multi-role scenarios simultaneously should use separate browser profiles or incognito windows for customer and administrator accounts.
