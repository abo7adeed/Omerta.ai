# Omerta.ai — Agentic RAG Operations & Deployment Guide

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

### 3.2 Run Database Migrations
```powershell
uv run alembic upgrade head
```

### 3.3 Ingest Starter Knowledge Documents
```powershell
uv run python -m infrastructure.knowledge.ingest
```

### 3.4 Start FastAPI Backend
```powershell
uv run uvicorn apps.api.main:app --reload --port 8000
```

### 3.5 Start Investigator Frontend
```powershell
cd frontend
npm run dev
```

The frontend will be available at `http://localhost:5173`, connecting to the backend at `http://localhost:8000`.

---

## 4. Operational Health & Diagnostics

The Agentic RAG service exposes a dedicated status and telemetry endpoint:

```http
GET /api/v1/agentic-rag/status
```

Response format:
```json
{
  "status": "OPERATIONAL",
  "version": "1.0.0",
  "sources": {
    "postgresql": "ONLINE",
    "neo4j": "ONLINE",
    "document_kb": {
      "status": "ONLINE",
      "indexed_documents": 6
    }
  },
  "modules": {
    "analytics_engine": "ACTIVE",
    "visualization_engine": "ACTIVE",
    "langgraph_orchestrator": "ACTIVE"
  }
}
```
