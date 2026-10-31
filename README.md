# 🛡️ Omerta.ai — Next-Gen AI Agentic Financial Crime & Banking Platform

<div align="center">

![Omerta.ai Banner](https://img.shields.io/badge/Omerta.ai-Autonomous_AML_&_Fraud_Defense-0A192F?style=for-the-badge&logo=shield&logoColor=29C5D9)

**Enterprise-Grade Autonomous Financial Crime Investigation, Real-Time AML Fraud Prevention, Multi-Agent Forensics, and Secure Core Banking Platform.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19.2-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.5+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.3-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16_Alpine-336791?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Neo4j 5](https://img.shields.io/badge/Neo4j-5.26_Graph-008CC1?style=flat-square&logo=neo4j&logoColor=white)](https://neo4j.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=flat-square&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Protocol_Ready-8A2BE2?style=flat-square)](https://modelcontextprotocol.io)
[![SMTP](https://img.shields.io/badge/SMTP-Live_STARTTLS-EA4335?style=flat-square&logo=gmail&logoColor=white)](https://gmail.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

[Architecture](#-system-architecture) • [Features](#-core-capabilities--innovations) • [Credentials](#-master-credentials--accounts-reference-sheet) • [Quickstart Guide](#-installation--quickstart-guide) • [API Reference](#-api-endpoints-reference) • [Testing](#-test-suite--verification) • [Full Summary Spec](docs/SYSTEM_SUMMARY.md)

</div>

---

## 🌟 Executive Summary

Traditional fraud detection platforms rely on static rule engines that flag suspicious activity after the fact, burdening human analysts with manual evidence collection across disjointed tools.

**Omerta.ai** bridges modern fintech core banking with autonomous agentic artificial intelligence:
- 💳 **Secure Double-Entry Banking Core**: Concurrent-safe, multi-currency ledger (`account_ledger_entries`) with deterministic row-level locks (`SELECT ... FOR UPDATE` ordered by account ID) preventing deadlocks and race conditions.
- 🔐 **Dual-Password Security & Non-Logout 3-Strikes Hold**: Segregates account login from transfer authorization; 3 wrong transfer passwords lock transfers on a security hold while preserving user session access.
- 🔑 **Cryptographic Step-Up Confirmation**: High-risk and verification-hold transactions issue time-limited, single-use SHA-256 tokens (`TransactionConfirmationToken`) preventing unauthorized release and replay attacks.
- ⏱️ **Multi-Window Rolling Velocity Engine**: Evaluates strict temporal windows (`5m`, `15m`, `60m`, `24h`, `7d`, `30d`) strictly bounded `[start, anchor_time)` to eliminate future data leakage, paired with database aggregates for lifetime account velocity.
- 🌐 **Intelligent Telemetry Classification**: Differentiates domestic Egyptian IP telemetry (held for customer verification) from foreign datacenter/hosting IP proxies (immediately blocked with HTTP 403).
- 🕸️ **Universal Search & Multi-Hop Network Topology (`/network`)**: Real-time entity-relationship graph computing itemized money inflows (*"from where got money"*) and outflows (*"where money went"*).
- 📱 **Device Intelligence & Localhost Co-Location (`/devices`)**: Detects multiple accounts sharing the same physical hardware, elevating risk to **HIGH** (2 accounts) or **CRITICAL** ($\ge 3$ accounts).
- 💬 **WhatsApp-Style Support Desk & Identity Verification (`/portal/support`, `/support-cases`)**: End-to-end case resolution, Egyptian National ID card verification, and administrative transfer restorations.
- 🤖 **Multi-Agent Forensic Consensus (LangGraph + MCP)**: Specialized sub-agents (Identity, Telemetry, Velocity, Compliance) autonomously construct auditable SAR dossiers and evidence-backed regulatory reports.

---

## 🏗️ System Architecture

```mermaid
flowchart TB
    subgraph ClientLayer [" 💻 Client Layer & Telemetry "]
        ReactSPA[" React 19 + TypeScript + Vite SPA "]
        CustomerPortal[" 👤 Customer Banking Portal "]
        AdminHub[" 🛡️ Compliance & Forensic Command Center "]
        TelemetryStream[" 📡 Device, IP & Geolocation Telemetry "]
    end

    subgraph APIGateway [" ⚡ FastAPI Gateway (Port 8000) "]
        AuthService[" 🔐 JWT Auth & Session Enforcement "]
        BankingRouter[" 💳 Core Banking & Double-Entry Transfers "]
        SupportRouter[" 💬 2-Way Support Ticket & Recovery Router "]
        NetworkRouter[" 🕸️ Subgraph & Fund Tracing Router "]
        AdminRouter[" ⚙️ Staff Management & Risk Tuning "]
        InvestigatorRouter[" 🧠 Case Management & AI Forensics "]
    end

    subgraph MultiAgentEngine [" 🤖 LangGraph Multi-Agent Forensic Engine "]
        Orchestrator[" 🧠 Lead Forensic Orchestrator "]
        IdentityAgent[" 🪪 Identity & KYC Agent "]
        TelemetryAgent[" 🌐 Telemetry & VPN Velocity Agent "]
        VelocityAgent[" 📈 Transaction Pattern & Velocity Agent "]
        ComplianceAgent[" 📜 AML Regulatory & Typology Agent "]
    end

    subgraph MCPServers [" 🔌 Model Context Protocol (MCP) Tool Servers "]
        TxnMCP[" 📊 Transaction MCP Server "]
        GraphMCP[" 🕸️ Neo4j Graph MCP Server "]
        RiskMCP[" 🎯 Risk Engine MCP Server "]
        KnowledgeMCP[" 📚 AML Typology RAG MCP Server "]
    end

    subgraph PersistenceLayer [" 🗄️ Dual Enterprise Persistence Layer "]
        PostgresDB[(" 🐘 PostgreSQL 16 (Port 15432)\n• Double-Entry Financial Ledger\n• Accounts, Users, Tickets & Audit Logs\n• SELECT FOR UPDATE Concurrency Locks ")]
        Neo4jGraph[(" 🌐 Neo4j Graph 5.26 (Port 17687)\n• Entity Relationship Graph\n• Mule Networks & Layering Rings\n• Shared Hardware & IP Clusters ")]
    end

    subgraph ExternalServices [" 📧 External Relay Services "]
        GmailSMTP[" 📧 Gmail SMTP Relay (STARTTLS :587)\n• Password Reset Links\n• Security Notices "]
        LLMProvider[" 🧠 Groq / OpenAI LLM APIs "]
    end

    ReactSPA --> APIGateway
    CustomerPortal --> APIGateway
    AdminHub --> APIGateway
    TelemetryStream --> APIGateway

    APIGateway --> MultiAgentEngine
    APIGateway --> PersistenceLayer
    APIGateway --> ExternalServices

    MultiAgentEngine --> MCPServers
    MultiAgentEngine --> LLMProvider

    MCPServers --> PostgresDB
    MCPServers --> Neo4jGraph
```

---

## 🚀 Core Capabilities & Innovations

### 🏦 1. Double-Entry Core Banking Platform
- **Immutable Financial Ledger:** High-precision monetary storage across currencies (**EGP, USD, EUR, GBP**) using strictly balanced double-entry accounting (`account_ledger_entries`).
- **Atomic Concurrency Protection:** Pessimistic row-level locking (`SELECT ... FOR UPDATE`) guarantees race condition safety and prevents double-spending.
- **National Flag Picker & Currency Validation:** International phone and country pickers with automatic recipient validation and real-time fee calculation.

```mermaid
sequenceDiagram
    autonumber
    actor Sender as 👤 Sender Customer
    participant UI as 💻 React Web App
    participant API as 🛡️ FastAPI Gateway
    participant DB as 🐘 PostgreSQL (:15432)
    participant Risk as 🎯 Risk Engine

    Sender->>UI: Enter Recipient, Amount & Transfer Password
    UI->>API: POST /api/v1/customer/transfers
    API->>DB: Verify Transfer Password & Active Status
    API->>Risk: Evaluate Flow Velocity & Device Risk
    alt Valid Password & Low/Moderate Risk
        API->>DB: BEGIN Transaction
        API->>DB: SELECT sender & recipient FOR UPDATE (Row Locks)
        API->>DB: Debit Sender Account & Insert DEBIT Ledger Entry
        API->>DB: Credit Recipient Account & Insert CREDIT Ledger Entry
        API->>DB: Update Balance Snapshots
        API->>DB: COMMIT Transaction
        API-->>UI: HTTP 201 Created (Transfer Completed)
    else Invalid Transfer Password (Strike 1 or 2)
        API->>DB: Increment failed_transfer_attempts
        API-->>UI: HTTP 401 Unauthorized (Warning: Strike X of 3)
    else Invalid Transfer Password (Strike 3)
        API->>DB: Set customer.transfer_status = 'BLOCKED'
        API->>DB: Create Automated Support Ticket (FORGOT_PASSWORD)
        API-->>UI: HTTP 403 Forbidden (Transfers Blocked - Security Hold)
    end
```

---

### 🔐 2. Dual-Password Protection & 3-Strikes Non-Logout Hold
- **Separation of Passwords:** Distinct **Account Login Password** (for portal access) and **Transfer Password** (for moving money).
- **Non-Logout Security Hold:** If a user fails the transfer password 3 consecutive times, only outbound transfers are placed on `BLOCKED` status. The user's active session is **NOT** terminated, allowing them to open a support case and upload verification documents.
- **Audited Recovery Workflow:** Compliance officers review the case, verify National ID photos, and restore transfer permissions with mandatory password reset flags.

---

### 🕸️ 3. Financial Crime & Multi-Hop Network Topology (`/network`)
- **Universal Search Engine:** Search by customer full name (`Haaland`, `Mohamed El-Sayed`), username, account number (`ACC-0033EC2B`), National ID, device ID, or IP address.
- **Bidirectional Fund Tracing:** Computes itemized inbound funding sources (*"From where got money"*) and outbound routing (*"Where money went"*) with exact transfer amounts.
- **Pass-Through Conduit & Structuring Detection:** Automatically identifies rapid flow-through velocity (`inflow >= 2,000 EGP`, `ratio > 0.65`) and fan-in smurfing patterns, rendering dynamic **CRITICAL Risk** red pulsing nodes.

```mermaid
graph LR
    subgraph InboundLayer [" Inbound Feeder Accounts "]
        A1[" ACC-8391F376\n(Abdelrahman Haaland Belii) "]
        A2[" ACC-1001\n(Ziad Karim) "]
    end

    subgraph FocalNode [" Focus Account (Conduit) "]
        Target[" 🚨 ACC-0033EC2B\n(Abdelrahman Haaland)\nCRITICAL RISK "]
    end

    subgraph OutboundLayer [" Outbound Destinations "]
        B1[" ACC-5E929093\n(Rahmaa Shaban) "]
    end

    subgraph HardwareLayer [" Shared Infrastructure "]
        DevNode[" 📱 DEV-DESKTOP-LINUX\n⚠️ Shared by 3 Accounts\nCRITICAL RISK "]
    end

    A1 -- "4,500 EGP" --> Target
    A2 -- "2,000 EGP" --> Target
    Target -- "5,000 EGP" --> B1
    A1 -. "Co-Located" .- DevNode
    Target -. "Co-Located" .- DevNode
    B1 -. "Co-Located" .- DevNode
```

---

### 📱 4. Device Intelligence & Localhost Co-Location (`/devices`)
- **Hardware Footprinting:** Detects and links accounts sharing physical hardware based on user-agent signatures and network endpoints.
- **Dynamic Risk Escalation:**
  - **1 Account**: Standard hardware (**LOW Risk**).
  - **2 Accounts**: Multi-account hopping (**HIGH Risk**).
  - **$\ge 3$ Accounts**: Hardware syndicate (**CRITICAL Risk** with `⚠️ MULTI-ACCOUNT (X ACCOUNTS)` badge).
- **Deep Entity Inspector:** Inspect all associated bank accounts, historical login sessions, and transactions tied to any device.

---

### 💬 5. Dual-Sided Support Desk & Case Management
- **Customer Portal (`/portal/support`)**: WhatsApp-style timeline chat for opening tickets, sending messages, uploading attachments (e.g. National ID cards), and tracking resolution status.
- **Compliance Console (`/support-cases`)**: Staff dashboard with real-time KPI metrics, triage filtering, staff replies, one-click identity approval, and transfer access restoration dialogs.

---

### ✨ 6. Multi-Agent AI Forensic Investigation
When an alert triggers or risk score exceeds 40, the **LangGraph Agentic Orchestrator** summons a consensus panel of specialized AI agents:
- **Identity & KYC Agent:** Evaluates customer profile, National ID match, and historical account age.
- **Telemetry Agent:** Assesses IP geolocation, impossible travel velocity (> 800 km/h), and VPN/proxy routing.
- **Velocity Agent:** Evaluates rapid layering, smurfing, and pass-through conduit ratios.
- **Compliance Agent:** Validates FATF typologies and automatically drafts auditable SAR filings with SHA-256 evidence hashing.

---

## 🔑 Master Credentials & Accounts Reference Sheet

Use these pre-seeded accounts to explore all roles and permissions:

| Role | Persona Name | Login Email / Username | Password | Account / Identifier | Initial Balance | Purpose & Permissions |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`ADMINISTRATOR`** | **Dr. Sarah Al-Rashid** | `admin@omerta.ai` / `admin` | `AdminPass123!` | System Super Admin | N/A | Full platform oversight, staff provisioning, risk tuning |
| **`FRAUD_ANALYST`** | **Tariq Mansour** | `analyst@omerta.ai` / `analyst` | `AnalystPass123!` | Operations Hub | N/A | Alert triage, support ticket resolution, risk reviews |
| **`INVESTIGATOR`** | **Laila El-Kady** | `investigator@omerta.ai` / `investigator` | `InvestigatorPass123!` | Senior Forensics | N/A | SAR generation, multi-agent AI execution, case sign-off |
| **`AUDITOR`** | **Omar Farooq** | `auditor@omerta.ai` / `auditor` | `AuditorPass123!` | Audit Console | N/A | Read-only compliance audit trails and evidence verification |
| **`CUSTOMER`** | **Ziad Karim** | `ziad@omerta.ai` / `ziad_k` | `Customer@2026!` | `OMR-1092-4821` | 50,000.00 EGP | P2P transfers, support tickets, beneficiary management |
| **`CUSTOMER`** | **Layla Hassan** | `layla@omerta.ai` / `layla_h` | `Customer@2026!` | `OMR-3847-1920` | 25,000.00 EGP | Multi-currency checking account, transfer recipient |
| **`CUSTOMER`** | **Amira El-Sayed** | `amira@omerta.ai` / `amira_e` | `Customer@2026!` | `OMR-7193-8402` | 120,000.00 EGP | Wealth banking profile, velocity test scenarios |
| **`CUSTOMER`** | **Omar Farouk** | `omar@omerta.ai` / `omar_f` | `Customer@2026!` | `OMR-9481-5632` | 15,000.00 EGP | Moderate risk testing customer profile |
| **`CUSTOMER`** | **Nour Mansour** | `nour@omerta.ai` / `nour_m` | `Customer@2026!` | `OMR-5238-7104` | 80,000.00 EGP | High risk business customer profile |

---

## 🛠️ Installation & Quickstart Guide

Follow these steps to run the complete platform from scratch after pulling from GitHub:

### 1. Prerequisites
- **Python 3.12+** and [uv](https://docs.astral.sh/uv/) (Fast Python package manager)
- **Node.js 20+** and `npm`
- **Docker & Docker Compose**

---

### 2. Clone & Configure Environment

```bash
# Clone the repository
git clone https://github.com/abo7adeed/Omerta.ai.git
cd Omerta.ai

# Create your .env file
cp .env.example .env
```

Ensure your `.env` contains:
```ini
# PostgreSQL (Port 15432)
DATABASE_URL=postgresql+asyncpg://omerta:omerta_dev_password@localhost:15432/omerta

# Neo4j Graph Database
NEO4J_URI=bolt://localhost:17687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=omerta_dev_password

# SMTP Live Email Dispatch (Optional Gmail App Password)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=abdomostafa13571234@gmail.com
SMTP_PASSWORD=your_16_char_gmail_app_password

# LLM Provider (Groq / OpenAI)
LLM_PROVIDER=groq
LLM_MODEL=openai/gpt-oss-20b
LLM_API_KEY=your_groq_api_key
```

---

### 3. Start Database Containers

```bash
docker compose up -d postgres neo4j
```

---

### 4. Backend Setup & Seed Database

```bash
# 1. Install Python dependencies
uv sync

# 2. Apply database migrations
uv run alembic upgrade head

# 3. Populate deterministic seed scenarios & accounts
uv run python -m infrastructure.database.seed
```
*(To reset and re-seed from scratch anytime, run: `uv run python -m infrastructure.database.seed --reset`)*

---

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run build
cd ..
```

---

### 6. Run Backend & Frontend

Open two terminal tabs:

#### Terminal 1 — FastAPI Backend (Port 8000)
```bash
uv run uvicorn apps.api.main:app --reload --port 8000
```
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

#### Terminal 2 — React Frontend (Port 5173)
```bash
cd frontend
npm run dev
```
- Web Application: `http://localhost:5173`

---

## 📡 API Endpoints Reference

### 🔐 Authentication & Session Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Register customer with dual login/transfer passwords and National ID |
| `POST` | `/api/v1/auth/login` | Authenticate user, check single-active-session and VPN telemetry |
| `POST` | `/api/v1/auth/logout` | Terminate session and clean active tokens |
| `GET` | `/api/v1/auth/me` | Fetch active user profile, customer context, and RBAC permissions |
| `POST` | `/api/v1/auth/forgot-password` | Dispatch live SMTP password reset email with cryptographic JWT token |
| `POST` | `/api/v1/auth/reset-password` | Verify token and update login password |

### 💳 Transaction Execution & AML Scoring Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/v1/transactions` | Submit transaction for real-time risk scoring (`APPROVED`, `HELD`, `BLOCKED`, `REJECTED`) |
| `POST` | `/api/v1/transactions/{id}/customer-confirmation` | Submit single-use SHA-256 confirmation token to release `HELD` transactions |
| `GET` | `/api/v1/transactions/{id}/history` | Cryptographically audited transaction event trail with IDOR protection |
| `GET` | `/api/v1/customer/lookup` | Instant recipient account and KYC name verification |

### 💳 Customer Banking & Support Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/customer/dashboard` | Retrieve accounts, total balances, and recent ledger entries |
| `POST` | `/api/v1/customer/transfers` | Execute password-protected transfer with 3-strikes security hold |
| `GET` | `/api/v1/customer/transfers` | Paginated transfer history |
| `GET` | `/api/v1/customer/tickets` | List customer support cases |
| `POST` | `/api/v1/customer/tickets` | Open new support inquiry or upload identity document |
| `POST` | `/api/v1/customer/tickets/{id}/messages` | Post message or attachment to support ticket timeline |
| `POST` | `/api/v1/customer/security/reset-transfer-password` | Set new transfer password following staff restoration |

### 🛡️ Compliance & Forensic Endpoints
| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/network/graph` | Fetch dynamic entity-relationship subgraph with itemized fund flows |
| `GET` | `/api/v1/network/suggestions` | Instant search auto-complete across customers, devices, and IPs |
| `GET` | `/api/v1/devices` | Paginated device intelligence with multi-account co-location counters |
| `GET` | `/api/v1/devices/{id}` | Deep inspection of accounts and transactions linked to a hardware device |
| `GET` | `/api/v1/tickets` | Staff queue of all support and security cases |
| `POST` | `/api/v1/tickets/{id}/restore-transfer` | Compliance officer action restoring customer transfer permissions |
| `POST` | `/api/v1/tickets/{id}/verify-identity` | Approve/reject customer National ID verification submission |

---


---

## ⚖️ LLM-as-a-Judge Evaluation & Langfuse Tracing

Omerta.ai features a production-minded **LLM-as-a-Judge evaluation and deterministic validation layer** integrated with LangGraph and Langfuse. It evaluates the factual quality, reasoning rigor, and regulatory completeness of completed investigations without human compliance replacement.

```
Omerta Investigation → LangGraph Agents → Result + Verified Evidence
                                                  ↓
                                        Deterministic Validation (Factual Checks)
                                                  ↓
                                        LLM-as-a-Judge (5 Rubric Dimensions)
                                                  ↓
                                        Langfuse Trace Association & Scores
                                                  ↓
                                        Optional Compliance Officer Review
```

### 🎯 5 Core Evaluation Dimensions (1–5 Scale)

1. **Evidence Grounding (1–5)**: Validates that all claims, transaction IDs, account numbers, amounts, dates, and device footprints match verified evidence. Detects hallucinations or fabricated entities.
2. **Reasoning Quality (1–5)**: Assesses logical progression, prevents leaps in logic, and ensures structural graph signals (e.g., shared devices) are not presented as proven criminal guilt.
3. **Investigation Completeness (1–5)**: Ensures all available and relevant evidence tiers (ledger, graph, risk, device) were queried. Missing unavailable information is never penalized.
4. **Report Quality (1–5)**: Evaluates clarity, structured executive synthesis, and compliance analyst utility adhering to Omerta schemas.
5. **Overall Quality (1–5)**: Holistic synthesis of the 4 pillars determining production-readiness.

> **Advisory Guardrail**: Scores evaluate investigation rigor and never authorize financial actions or determine criminal guilt.

### 🛡️ Deterministic Validation Engine

Independent of LLM judgments, the deterministic validator verifies:
- **Transaction & Account IDs**: Matches referenced IDs against verified ledger records.
- **Amounts & Currency**: Detects numerical contradictions (e.g. tenfold discrepancies like $85,000 vs $8,500).
- **Graph Topology**: Verifies claimed shared devices, IPs, and corporate relationships against Neo4j projections.
- **Referential Integrity**: Ensures all findings reference valid evidence IDs.

### ⚙️ Configuration (.env)

```bash
# Enable/Disable LLM evaluation (default: false)
OMERTA_EVALUATION_ENABLED=false

# Dedicated Judge Model (optional: falls back to platform provider)
OMERTA_EVALUATION_PROVIDER=groq     # groq | openai | ollama | fake
OMERTA_EVALUATION_MODEL=openai/gpt-oss-20b
OMERTA_EVALUATION_API_KEY=gsk_...
OMERTA_EVALUATION_TIMEOUT=60.0
OMERTA_EVALUATION_MAX_RETRIES=2
OMERTA_EVALUATION_VERSION=1.0

# Langfuse Observability & Tracing
LANGFUSE_ENABLED=true
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
```

### 🚀 Running the Synthetic Benchmark

A synthetic benchmark covering 8 canonical AML investigation scenarios (normal, suspicious, and deliberate defects) is included:

```bash
# Run benchmark offline with deterministic fake judge
uv run python scripts/run_evaluation_benchmark.py --force-fake

# Run benchmark against configured cloud/local LLM judge
uv run python scripts/run_evaluation_benchmark.py --output benchmark_results.json
```

### 📊 Inspecting Results in Langfuse

When `LANGFUSE_ENABLED=true` and `OMERTA_EVALUATION_ENABLED=true`, each completed investigation trace automatically records:
- **Numerical Scores**: `evidence_grounding`, `reasoning_quality`, `investigation_completeness`, `report_quality`, `overall_quality` (1.0 - 5.0)
- **Categorical Scores**: `deterministic_validation` (`PASSED` | `FAILED`), `human_review_required` (`REQUIRED` | `NOT_REQUIRED`)
- **Metadata**: Judge model name, provider, latency (ms), and evaluation version.

### 💻 Running Tests

```bash
# Run all evaluation unit, integration, and API tests
uv run pytest tests/test_evaluation_system.py -v
```

## 🧪 Test Suite & Verification

The test suite validates core double-entry accounting invariants, row-locking race safety, single-session RBAC enforcement, single-use confirmation token security, and multi-agent consensus:

```bash
# 1. Master AML Fraud Workflow (Scoring, Velocity & Rules)
uv run pytest tests/test_master_fraud_workflow.py -v

# 2. Authentication, Single-Active-Session & RBAC
uv run pytest tests/test_auth_session_reset_and_rbac.py -v

# 3. Core Banking Double-Entry Ledger & Admin Provisioning
uv run pytest tests/test_stage2_banking_and_admin.py -v

# 4. Support Ticket Security, ID Cards & Identity Restorations
uv run pytest tests/test_ticket_security_and_restorations.py -v

# 5. Dual-Password Transfer Security & 3-Strikes Hold
uv run pytest tests/test_transfer_security_and_support.py -v

# 6. Network Topology Subgraph & Fund Tracing
uv run pytest tests/test_network_graph_and_fund_tracing.py -v

# 7. Frontend Production Type-Check & Bundle Build
npm --prefix frontend run build
```

---

<div align="center">

**Built for next-generation financial intelligence, zero-trust core banking, and autonomous crime defense.**

*Omerta.ai &copy; 2026. All rights reserved.*

</div>
