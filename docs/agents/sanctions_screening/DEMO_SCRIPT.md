# Omerta.ai — Sanctions & Watchlist Screening Agent
## Live Demonstration & Stakeholder Walkthrough Script

**Document Version:** 1.0.0  
**Target Audience:** Compliance Officers, MLROs, Executive Stakeholders, Security Auditors  
**System Components Demonstrated:** React Frontend, FastAPI Gateway, Sanctions MCP Server, Langflow Workflow  

---

## 1. Demonstration Environment Preparation

### Step 1: Start the Omerta Backend API
Open a PowerShell terminal in the repository root:
```powershell
.venv\Scripts\activate
uvicorn apps.api.main:app --port 8000 --reload
```
Verify the API is active:
```powershell
curl http://localhost:8000/api/v1/sanctions/health
```
*Expected Output:*
```json
{"status":"healthy","baseline_entity_count":8,"baseline_dataset_loaded":true}
```

### Step 2: Start the Omerta React Frontend
In a second terminal:
```powershell
cd frontend
npm run dev
```
Navigate your browser to `http://localhost:5173`.

---

## 2. Walkthrough Scenarios

### Scenario A: Cross-Lingual Arabic Screening & Transliteration
**Objective:** Show that the agent correctly matches Arabic script containing diacritics (Tashkeel) and morphological prefixes without false negatives.

1. Navigate to **Investigations** in the sidebar.
2. Click on **Forensic Investigation** or open any case dossier.
3. Switch to the **Sanctions & Watchlists** tab.
4. In the Legal Name field, enter the Arabic name with vowel diacritics:
   ```text
   مُحَمَّدُ السَّيِّد أحْمَد
   ```
5. Set Country to `EG`.
6. Click **Run Screening via MCP**.
7. **Observer Highlights:**
   - Notice the execution completes in **~12 ms**.
   - The top match card displays `Mohamed El-Sayed Ahmed` with a **96% Match Confidence** badge.
   - The green matched factor pills indicate:
     - *Name match (similarity: 0.95)*
     - *Country match: EG*
   - Official source citations are clickable, linking directly to the OFAC and OpenSanctions record pages.
   - The amber warning banner reminds the officer that **Human Review is Mandatory** before taking adverse action.

---

### Scenario B: Automated Case Participant Batch Screening
**Objective:** Demonstrate one-click screening of all parties (sender customer, recipient account, counterparties) involved in a live fraud investigation case.

1. On the **Investigations** page, locate case **`CASE-2026-001`** (or click any case file).
2. Click the arrow button to **Open Case Dossier**.
3. Select the **Sanctions & Watchlist Screening** tab inside the dossier.
4. Click **Screen Case Participants (CASE-2026-001)**.
5. **Observer Highlights:**
   - The agent automatically extracts the sender customer and recipient counterparty.
   - It invokes the Sanctions MCP tool under the authenticated identity `InvestigatorAgent`.
   - An immutable `AuditEvent` (`CASE_SANCTIONS_SCREENED`) is written to PostgreSQL.
   - The UI summarizes:
     - Total entities screened: `2`
     - Potential matches: `1`
     - Status: `ALERT_POTENTIAL_SANCTIONS_MATCH`
     - The officer is prompted for formal adjudication.

---

### Scenario C: Adversarial Security & Injection Defense
**Objective:** Prove to security auditors that malicious SQL or shell commands passed in user inputs are intercepted before execution.

1. In the **Legal Name** input field, enter an adversarial SQL mutation string:
   ```sql
   '; DROP TABLE customers; --
   ```
2. Click **Run Screening via MCP**.
3. **Observer Highlights:**
   - The request is immediately rejected with an error banner:
     `Prohibited SQL mutation detected in name: All MCP tools are strictly read-only.`
   - No database connections were opened, and zero state was altered.
   - Repeat with a shell command: `Viktor `powershell -c calc.exe`` — immediately rejected with `SECURITY_VIOLATION`.

---

### Scenario D: Offline / Zero-Network Resilience
**Objective:** Demonstrate that Omerta operates reliably in air-gapped or restricted network environments when the external OpenSanctions API is unreachable.

1. In PowerShell, query the tool directly while simulating an unreachable external host:
   ```powershell
   .venv\Scripts\python.exe -c "import asyncio; from mcp_servers.sanctions_server.tools import screen_entity_against_watchlists; from mcp_servers.common.specialist_rbac import generate_specialist_token; token = generate_specialist_token('SanctionsScreeningAgent'); res = asyncio.run(screen_entity_against_watchlists(name='Viktor Bout', specialist='SanctionsScreeningAgent', auth_token=token)); print('Source:', res['execution_metadata']['source_queried']); print('Match:', res['match_found'])"
   ```
2. **Observer Highlights:**
   - Output shows:
     `Source: LOCAL_BASELINE`  
     `Match: True`
   - Even with external internet connectivity blocked or 401/429 upstream status, the agent degrades gracefully to the bundled FollowTheMoney baseline dataset without crashing.

---

## 3. Reviewer Checklist & Sign-Off

- [x] Transliteration between Arabic and English matches accurately.
- [x] False positives with conflicting DOB (20-year age gap) are suppressed.
- [x] False positives with conflicting countries are penalized.
- [x] MCP server enforces signed token authentication (anonymous calls blocked).
- [x] All database and tool actions are strictly read-only.
- [x] Human review is strictly enforced (zero automated account freezes).
- [x] Observability logs in Langfuse redact customer PII.
- [x] Visual workflow in Langflow executes cleanly.

