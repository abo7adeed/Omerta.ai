# Omerta.ai — Banking Knowledge Base & Ingestion Pipeline

## 1. Corpus Architecture

The Knowledge Base houses simulated banking policies, procedures, and regulatory guidance across six essential operational domains:

1. **Banking Operations (`DOC-OPS-001`):** Account lifecycle, double-entry ledger settlement, transfer rules, exception handling, and reconciliation.
2. **Identity & Account Security (`DOC-SEC-001`):** MFA enforcement, failed password lockouts, 3-strike escalation, device fingerprinting, and security hold restoration.
3. **AML / CFT & Financial Crime Intelligence (`DOC-AML-001`):** Structuring indicators, smurfing typologies, rapid inflow/outflow bursts, mule networks, and mandatory FATF Red Flags.
4. **Compliance & Forensic Case Management (`DOC-CMP-001`):** Evidence sufficiency requirements, four-eyes review, case closure thresholds, and supervisory escalations.
5. **AI Investigation Governance (`DOC-GOV-001`):** Permitted uses of AI, non-accusatory findings, citation requirements, and human-in-the-loop compliance decisions.
6. **System & Data Classification (`DOC-SYS-001`):** Role-based access control (RBAC), data classification levels, audit trail immutability, and retention periods.

All documents are stored in markdown format in `infrastructure/knowledge/documents/` with YAML frontmatter.

---

## 2. Ingestion Engine Pipeline

The ingestion service (`infrastructure/knowledge/ingest.py`) implements a 12-stage validation and indexing process:

```text
Source File (.md, .txt, .pdf, .docx)
               │
               ▼
1. File Type and Size Validation
               │
               ▼
2. Access Classification Check
               │
               ▼
3. Text & Header Extraction
               │
               ▼
4. Page / Section Metadata Tagging
               │
               ▼
5. Section-Aware Chunking (Heading-based)
               │
               ▼
6. Stable Chunk ID Generation (DOC-SECTION-INDEX)
               │
               ▼
7. Cryptographic SHA-256 Content Hashing
               │
               ▼
8. Term-Frequency Vector Extraction
               │
               ▼
9. Document Versioning & Upsert
               │
               ▼
10. Chunk Pruning & Replacement
               │
               ▼
11. Ingestion Audit Record
               │
               ▼
12. Ready for Hybrid Lexical/Semantic Retrieval
```

---

## 3. Supported File Formats

- **Markdown (`.md`):** Native parser with YAML frontmatter extraction and `#`, `##`, `###` heading chunking.
- **Plain Text (`.txt`):** Paragraph-based chunking with stable sequential indexing.
- **PDF (`.pdf`):** Processed via `pypdf` with page-number extraction and clean text fallback.
- **DOCX (`.docx`):** Processed via `python-docx` with style-aware heading hierarchy and clean XML fallback.

---

## 4. Ingestion Command Line

To ingest or re-index the starter corpus:

```powershell
uv run python -c "import asyncio, pathlib; from infrastructure.database.session import get_engine; from sqlalchemy.ext.asyncio import AsyncSession; from infrastructure.knowledge.ingest import ingest_starter_corpus; asyncio.run(ingest_starter_corpus(AsyncSession(get_engine(), expire_on_commit=False), pathlib.Path('infrastructure/knowledge/documents').resolve()))"
```
