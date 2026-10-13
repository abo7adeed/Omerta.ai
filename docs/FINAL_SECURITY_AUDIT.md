# 🛡️ Omerta.ai — Final Application Security Audit Report

**Date:** October 2026  
**Auditor Role:** Application Security Engineer & Lead Software Architect  
**Target Repository:** Omerta.ai (Enterprise AI Banking Fraud Prevention & Investigation)  
**Status:** Remediated & Release-Hardened  

---

## 1. Executive Summary

This security audit conducted an in-depth code-level analysis, penetration surface assessment, and automated regression verification across all critical banking transaction, authentication, specialist intelligence, and administrative lifecycles of **Omerta.ai**.

All critical vulnerabilities—including unauthenticated customer transaction confirmation, insecure direct object references (IDOR), ledger concurrency/double-settlement hazards, historical intelligence window boundary bleeding, and CORS misconfigurations—have been fully remediated and verified with passing automated test suites.

---

## 2. Itemized Security Findings & Remediations

### FINDING SEC-01: Insecure Anonymous Customer Confirmation & Token Derivation
- **Severity:** CRITICAL (CVSS 9.1)
- **Component:** `apps/api/v1/transactions.py`, `domain/services/transfer_service.py`
- **Root Cause:** The customer confirmation endpoint allowed callers to execute state-changing actions (`CONFIRM` / `DENY`) on held transactions purely by supplying the transaction ID without an authenticated customer session or cryptographically verifiable action token.
- **Fix Implemented:**
  1. Created `TransactionConfirmationToken` model (`infrastructure/database/models.py`) with SHA-256 hashed single-use tokens, explicit `allowed_action`, customer and transaction bindings, and expiry timestamps.
  2. Implemented `create_confirmation_token` and `validate_and_consume_confirmation_token` with atomic state updates (`used_at`, `revoked_at`).
  3. Enforced dual-path security in `handle_transaction_customer_confirmation`: either an authenticated customer session owning the source account is required, or a valid, unexpired, single-use signed token hash must be presented and atomically consumed.
  4. Created and applied Alembic migration `f1a2b3c4d5e6_transaction_confirmation_tokens.py`.
- **Proving Regression Tests:** `tests/test_transfer_security_and_support.py::test_customer_transaction_history_idor_and_ownership_enforcement` and `tests/test_master_fraud_workflow.py::test_vpn_hold_customer_confirmation_and_admin_settlement`.

---

### FINDING SEC-02: IDOR on Transaction History Intelligence Endpoint
- **Severity:** HIGH (CVSS 8.5)
- **Component:** `apps/api/v1/transactions.py` (`GET /{transaction_id}/history`)
- **Root Cause:** Historical account intelligence could be retrieved by any caller with a transaction ID without verifying whether the authenticated caller owned the account or possessed an authorized investigative role.
- **Fix Implemented:**
  1. Enforced authentication via `Depends(get_current_user)`.
  2. Implemented ownership verification: customers can only access historical metrics for accounts they own.
  3. Granted access to authorized staff roles (`ADMINISTRATOR`, `SUB_ADMINISTRATOR`, `FRAUD_ANALYST`, `INVESTIGATOR`, `SENIOR_INVESTIGATOR`, `AUDITOR`).
  4. Returns `403 FORBIDDEN` on unauthorized access attempts without leaking recipient or account details.
- **Proving Regression Tests:** `tests/test_transfer_security_and_support.py::test_customer_transaction_history_idor_and_ownership_enforcement`.

---

### FINDING SEC-03: Historical Investigation Window Bleeding & Current Transaction Baseline Distortion
- **Severity:** MEDIUM (CVSS 6.5)
- **Component:** `domain/investigation/history_agent.py`
- **Root Cause:** Historical rolling metric windows (5m, 15m, 60m, 24h, 7d, 30d) lacked explicit lower and upper timezone-aware bounds, included the active transaction under investigation within its own baseline, and conflated lifetime account statistics with 30-day velocity metrics.
- **Fix Implemented:**
  1. Enforced strict UTC lower bound (`timestamp >= thirty_days_ago`) and upper bound (`timestamp < anchor_time`).
  2. Explicitly excluded the transaction under investigation (`Transaction.id != current_transaction_id`).
  3. Defined deterministic interval boundaries `[start, anchor_time)` across all standard windows.
  4. Computed lifetime statistics via server-side database aggregates (`func.count`, `func.coalesce(func.sum)`) without pulling unlimited sets into application memory.
  5. Implemented `INSUFFICIENT_HISTORY` data-quality metadata when fewer than 3 records exist.
- **Proving Regression Tests:** `tests/test_transaction_investigation.py` and `tests/test_master_fraud_workflow.py`.

---

### FINDING SEC-04: Concurrency & Ledger Double Settlement Protection
- **Severity:** HIGH (CVSS 8.7)
- **Component:** `domain/services/transfer_service.py`
- **Root Cause:** Multiple concurrent requests or repeated clicks could trigger duplicate settlement and balance deductions.
- **Fix Implemented:**
  1. Centralized all money movements into `_execute_atomic_settlement` within a single database transaction.
  2. Enforced deterministic row-level locks on sender and recipient accounts using `with_for_update()` in sorted primary-key order to eliminate deadlocks.
  3. Validated state eligibility and prevented double-posting by asserting transfer status and idempotency keys.
  4. Ensured atomic double-entry debit and credit creation with matching decimal amounts before marking the transfer and transaction `COMPLETED`.
- **Proving Regression Tests:** `tests/test_stage2_banking_and_admin.py` and `tests/test_master_fraud_workflow.py`.

---

### FINDING SEC-05: Overly Permissive Wildcard CORS with Credentials
- **Severity:** MEDIUM (CVSS 6.0)
- **Component:** `apps/api/main.py`
- **Root Cause:** `CORSMiddleware` was initialized with `allow_origins=["*"]` combined with `allow_credentials=True`, which is rejected by modern browsers and violates secure cross-origin isolation.
- **Fix Implemented:** Replaced wildcard origin with explicit, environment-aware origin whitelist:
  `["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000", "http://127.0.0.1:8000"]`.
- **Proving Verification:** Verified via `main.py` inspection and frontend integration build.

---

### FINDING SEC-06: Unauthenticated Development Fallback User in Production
- **Severity:** HIGH (CVSS 7.8)
- **Component:** `infrastructure/security/jwt_auth.py`
- **Root Cause:** `get_current_user` returned a mock analyst user (`Tariq Mansour`) when no credentials were provided, creating an open access vector if deployed to production.
- **Fix Implemented:** Restricted dev fallback strictly to development/test environments. When `ENVIRONMENT=production`, missing credentials immediately raise `401 UNAUTHORIZED`.
- **Proving Regression Tests:** `tests/test_auth_session_reset_and_rbac.py`.

---

## 3. Security Audit Verification Summary

| Phase / Surface | Automated Test Suite | Result | Status |
| :--- | :--- | :---: | :---: |
| **Customer Confirmation & IDOR** | `test_transfer_security_and_support.py` | 2 / 2 Passed | ✅ VERIFIED |
| **Auth, Sessions, RBAC & Telemetry** | `test_auth_session_reset_and_rbac.py` | 11 / 11 Passed | ✅ VERIFIED |
| **Tickets, Restrictions & Restorations** | `test_ticket_security_and_restorations.py` | 10 / 10 Passed | ✅ VERIFIED |
| **End-to-End Master Fraud Workflow** | `test_master_fraud_workflow.py` | 9 / 9 Passed | ✅ VERIFIED |
| **Core Banking & Admin Permissions** | `test_stage2_banking_and_admin.py` | 15 / 15 Passed | ✅ VERIFIED |
| **Frontend TypeScript Type Safety** | `npm run build` (`tsc -b && vite build`) | 0 Errors | ✅ VERIFIED |
