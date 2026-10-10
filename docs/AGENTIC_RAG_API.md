# Omerta.ai — Agentic RAG API Specification & Contracts

## 1. Overview

The Agentic RAG API exposes endpoints under the `/api/v1/agentic-rag` prefix. All requests require valid JWT Bearer authentication.

---

## 2. Endpoints

### 2.1 Execute Analysis Query
`POST /api/v1/agentic-rag/query`

#### Request Body (`AgenticRAGRequest`)
```json
{
  "question": "Show daily transaction volume and plot a trend chart over the last week.",
  "entity_ids": ["ACC-1001"],
  "conversation_id": "conv-test-001"
}
```

#### Response Body (`AgenticRAGResponse`)
```json
{
  "status": "ANSWERED",
  "answer": "### Financial Analysis Summary\n- Total Volume: 145,000.00 EGP...",
  "citations": [
    {
      "citation_id": "cit-001",
      "evidence_id": "ev-db-summary-7",
      "source_type": "postgresql",
      "title": "Transaction Ledger Summary",
      "locator": "LEDGER-AGGREGATE: Last 7 Days",
      "excerpt": "Total volume: 145000.00 EGP across 12 transactions."
    }
  ],
  "evidence_ids": ["ev-db-summary-7"],
  "sources_used": ["postgresql"],
  "response_blocks": [
    {
      "type": "metric",
      "metrics": [
        {
          "label": "Total Volume (7 Days)",
          "value": 145000.0,
          "unit": "EGP",
          "period": "Last 7 Days"
        }
      ]
    },
    {
      "type": "chart",
      "chart": {
        "artifact_id": "chart_a1b2c3d4",
        "title": "Daily Transaction Volume Trend (EGP)",
        "chart_type": "line",
        "file_url": "/api/v1/agentic-rag/artifacts/chart_a1b2c3d4",
        "points_count": 7
      }
    },
    {
      "type": "text",
      "content": "Narrative explanation of findings..."
    }
  ],
  "limitations": [
    "AI findings are forensic assessments and must be corroborated by an authorized investigator."
  ]
}
```

---

### 2.2 Retrieve Chart Artifact
`GET /api/v1/agentic-rag/artifacts/{artifact_id}`

Returns the binary PNG chart image (`image/png`). Protected against path traversal.

---

### 2.3 Telemetry & Operational Health
`GET /api/v1/agentic-rag/status`

Returns subsystem health, database connections, and indexed document counts.
