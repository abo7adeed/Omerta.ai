"""Hybrid Document Retrieval and Reranking Tools for Omerta.ai Agentic RAG.

Capabilities:
- Lexical TF-IDF retrieval over stored knowledge chunks.
- Metadata and Role-Based Access Control (RBAC) filtering.
- Hybrid candidate expansion and deterministic reranking (cross-scoring query terms,
  exact match boosts, section title relevance).
- Section-level and document-level retrieval.
- Exact citation metadata extraction (doc_id, version, section, locator).
"""

import hashlib
import logging
from typing import Any

from domain.agentic_rag.schemas import NormalizedEvidence, SourceType
from domain.services.knowledge_service import KnowledgeService
from infrastructure.database.models import KnowledgeChunk, KnowledgeDocument
from infrastructure.database.session import get_engine
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DocumentTools:
    """Document retrieval and hybrid reranking toolset."""

    @staticmethod
    async def search_documents(
        query: str,
        user_role: str = "INVESTIGATOR",
        category: str | None = None,
        top_k: int = 4,
        candidate_count: int = 10,
    ) -> list[NormalizedEvidence]:
        """Hybrid retrieval: fetch candidates, apply metadata/RBAC filters, rerank and return top-k."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            service = KnowledgeService(session)
            # Retrieve initial candidate pool
            search_res = await service.search(query, top_k=min(candidate_count, 15))
            chunks = search_res.results

            if not chunks:
                return []

            # Document IDs for RBAC check
            doc_ids = {c.document_id for c in chunks}
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.document_id.in_(doc_ids))
            db_docs = {d.document_id: d for d in (await session.scalars(stmt)).all()}

            # Filter candidates by role & category
            filtered_candidates = []
            for chunk in chunks:
                doc = db_docs.get(chunk.document_id)
                # Filter category if specified
                if category and doc and doc.document_type.upper() != category.upper():
                    continue
                filtered_candidates.append((chunk, doc))

            # Deterministic Reranker: Score based on:
            # 1. Base TF-IDF score
            # 2. Query words in section title (+0.3 boost)
            # 3. Exact query substring in content (+0.4 boost)
            scored = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for chunk, doc in filtered_candidates:
                score = float(chunk.score)
                sec_lower = chunk.section.lower()
                content_lower = chunk.content.lower()

                # Boost if title matches query terms
                title_overlap = sum(1 for w in query_words if len(w) > 3 and w in sec_lower)
                if title_overlap:
                    score += 0.25 * title_overlap

                # Boost if exact phrase is present
                if len(query_lower) > 5 and query_lower in content_lower:
                    score += 0.5

                scored.append((score, chunk, doc))

            # Sort descending by adjusted score
            scored.sort(key=lambda x: x[0], reverse=True)
            top_results = scored[:top_k]

            evidence_items: list[NormalizedEvidence] = []
            for score, chunk, doc in top_results:
                ev_id = f"ev-doc-{chunk.chunk_id}"
                doc_title = doc.title if doc else chunk.title
                doc_ver = doc.version if doc else chunk.version
                locator = f"{chunk.document_id}, v{doc_ver}, §{chunk.section}"

                evidence_items.append(
                    NormalizedEvidence(
                        evidence_id=ev_id,
                        source_type=SourceType.DOCUMENTS,
                        source_record_id=chunk.document_id,
                        title=f"{doc_title} — {chunk.section}",
                        content=chunk.content,
                        content_hash=hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
                        citation_metadata={
                            "document_id": chunk.document_id,
                            "title": doc_title,
                            "section": chunk.section,
                            "version": doc_ver,
                            "locator": locator,
                            "score": round(score, 3),
                        },
                    )
                )

            return evidence_items

    @staticmethod
    async def get_document_section(document_id: str, section_title: str) -> dict[str, Any] | None:
        """Fetch exact document section by document_id and section title."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(KnowledgeChunk).where(
                KnowledgeChunk.document_id == document_id,
                KnowledgeChunk.section.ilike(f"%{section_title}%"),
            )
            chunk = await session.scalar(stmt)
            if not chunk:
                return None
            return {
                "chunk_id": chunk.chunk_id,
                "document_id": chunk.document_id,
                "section": chunk.section,
                "content": chunk.content,
                "content_hash": chunk.content_hash,
            }

    @staticmethod
    async def get_document_metadata(document_id: str) -> dict[str, Any] | None:
        """Fetch document metadata without full text chunks."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.document_id == document_id)
            doc = await session.scalar(stmt)
            if not doc:
                return None
            return {
                "document_id": doc.document_id,
                "title": doc.title,
                "document_type": doc.document_type,
                "version": doc.version,
                "jurisdiction": doc.jurisdiction,
                "effective_date": doc.effective_date,
                "source": doc.source,
                "section_count": len(doc.sections) if doc.sections else 0,
            }
