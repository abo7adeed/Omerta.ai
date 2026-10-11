# Omerta.ai — Agentic RAG Operations, Verification & Testing Guide

## 1. Prerequisites and Infrastructure

The Omerta.ai Agentic RAG system requires:
- **Python 3.12+** managed via `uv`.
- **PostgreSQL 16+** with relational banking tables and knowledge store schema (port `15432` in local dev).
- **Neo4j 5.x** graph database (ports `17474` HTTP / `17687` Bolt).
- **Node.js 20+** with npm for the React/Vite investigator frontend.
- **Groq API Key** (optional in development; deterministic synthesis operates automatically offline).

---

## 2. Environment Configuration

Add the following environment variables to your `.env` file:

```bash
# Database & Graph
DATABASE_URL=postgresql+asyncpg://omerta:omerta_dev_password@127.0.0.1:15432/omerta
NEO4J_URI=bolt://127.0.0.1:17687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=omerta_dev_password

# Authentication
JWT_SECRET=omerta_dev_jwt_secret_key_banking_intelligence_2026_super_secure

# Groq LLM Provider Configuration
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
GROQ_TIMEOUT_SECONDS=30
GROQ_MAX_RETRIES=2

# Document & Artifact Storage
ARTIFACTS_DIR=apps/api/static/artifacts/charts
```

---

## 3. Starting the Services

### 3.1 Start Docker Infrastructure
```powershell
docker compose up -d postgres neo4j
```

### 3.2 Run Database Migrations & Seed
```powershell
uv run alembic upgrade head
uv run python -m infrastructure.database.seed
```

### 3.3 Ingest Starter Knowledge Documents
```powershell
uv run python -m infrastructure.knowledge.ingest
```

### 3.4 Start FastAPI Backend
```powershell
uv run uvicorn apps.api.main:app --reload --port 8000
```

### 3.5 Start React Frontend
```powershell
cd frontend
npm run dev
```

---

## 4. Verification & Automated Test Procedures

### 4.1 Run Agentic RAG Regression Suite
Execute the dedicated 38-test Agentic RAG suite covering all security, routing, retrieval, citation, and graph guarantees:

```powershell
uv run pytest tests/test_agentic_rag.py -v
```

### 4.2 Run Frontend Production Build
Validate TypeScript typings and bundle compilation:

```powershell
cd frontend
npm run build
```

---

## 5. API Endpoints Reference

- `POST /api/v1/agentic-rag/query`: Processes natural-language questions through LangGraph orchestrator with session memory.
- `GET /api/v1/agentic-rag/sessions`: Lists conversation sessions belonging strictly to the authenticated user.
- `GET /api/v1/agentic-rag/sessions/{session_id}`: Retrieves full message history and thought steps for an authorized session.
- `POST /api/v1/agentic-rag/sessions`: Initializes a new empty investigation session.
- `DELETE /api/v1/agentic-rag/sessions/{session_id}`: Deletes an owned session.
- `GET /api/v1/agentic-rag/artifacts/{artifact_id}`: Delivers authenticated Matplotlib chart PNG images with traversal defenses.
- `GET /api/v1/agentic-rag/status`: Operational telemetry for RAG sources and database connectivity.
