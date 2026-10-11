"""Hybrid Document Retrieval and Reranking Tools for Omerta.ai Agentic RAG.

Capabilities:
- Lexical TF-IDF retrieval over stored knowledge chunks.
- Role-Based Access Control (RBAC) and classification filtering.
- Hybrid candidate expansion and deterministic reranking (cross-scoring query terms,
  exact match boosts, section title relevance).
- Section-level and document-level retrieval.
- Exact citation metadata extraction (doc_id, version, section, locator, SHA-256 hash).
- Retrieval debug mode for authorized audit inspections.
"""

import hashlib
import logging
from pathlib import Path
from typing import Any

from domain.agentic_rag.schemas import NormalizedEvidence, SourceType
from domain.services.knowledge_service import KnowledgeService
from infrastructure.database.models import KnowledgeChunk, KnowledgeDocument
from infrastructure.database.session import get_engine
from infrastructure.knowledge.ingest import parse_frontmatter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Trusted document metadata cache (parsed from frontmatter)
_DOC_METADATA_CACHE: dict[str, dict[str, Any]] = {}


def _load_document_metadata_cache() -> dict[str, dict[str, Any]]:
    """Load or refresh document metadata cache from source files."""
    global _DOC_METADATA_CACHE
    if not _DOC_METADATA_CACHE:
        docs_dir = Path("infrastructure/knowledge/documents").resolve()
        if docs_dir.exists():
            for p in docs_dir.glob("*.md"):
                try:
                    meta, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                    d_id = meta.get("document_id") or p.stem.upper().replace("_", "-")
                    _DOC_METADATA_CACHE[d_id] = meta
                except Exception as exc:
                    logger.debug("Failed parsing frontmatter for %s: %s", p.name, exc)
    return _DOC_METADATA_CACHE


def get_document_allowed_roles(doc_id: str) -> list[str]:
    """Retrieve allowed roles for document from trusted metadata or strict default."""
    cache = _load_document_metadata_cache()
    meta = cache.get(doc_id, {})
    roles = meta.get("allowed_roles")
    if roles and isinstance(roles, list):
        return [r.upper() for r in roles]

    # Explicit default policy:
    # Public & operational policies allow CUSTOMER; governance & specs require internal roles.
    if doc_id in ("DOC-OPS-001", "DOC-FATF-TYPOLOGIES"):
        return ["CUSTOMER", "FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]
    return ["FRAUD_ANALYST", "INVESTIGATOR", "ADMINISTRATOR", "AUDITOR"]


class DocumentTools:
    """Document retrieval and hybrid reranking toolset."""

    @staticmethod
    async def search_documents(
        query: str,
        user_role: str = "INVESTIGATOR",
        category: str | None = None,
        top_k: int = 4,
        candidate_count: int = 10,
        min_relevance_score: float = 0.05,
    ) -> list[NormalizedEvidence]:
        """Hybrid retrieval: fetch candidates, apply RBAC & category filters, rerank and return top-k."""
        user_role_upper = (user_role or "INVESTIGATOR").upper()

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            service = KnowledgeService(session)
            # Retrieve initial candidate pool bounded by service MAX_TOP_K (10)
            search_res = await service.search(query, top_k=min(candidate_count, 10))
            chunks = search_res.results

            if not chunks:
                return []

            # Load document entities for metadata verification
            doc_ids = {c.document_id for c in chunks}
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.document_id.in_(doc_ids))
            db_docs = {d.document_id: d for d in (await session.scalars(stmt)).all()}

            # Filter candidates by RBAC role & category
            filtered_candidates = []
            for chunk in chunks:
                doc = db_docs.get(chunk.document_id)

                # 1. Enforce RBAC Role Permissions
                allowed_roles = get_document_allowed_roles(chunk.document_id)
                if user_role_upper not in allowed_roles and user_role_upper != "ADMINISTRATOR":
                    logger.info("RBAC DENY: Role '%s' cannot view document '%s'", user_role_upper, chunk.document_id)
                    continue

                # 2. Filter category if specified
                if category and doc and doc.document_type.upper() != category.upper():
                    continue

                filtered_candidates.append((chunk, doc))

            if not filtered_candidates:
                return []

            # Deterministic Reranker: Score based on:
            # 1. Base TF-IDF score
            # 2. Query words in section title (+0.25 boost per significant word)
            # 3. Exact query substring in content (+0.5 boost)
            scored = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for chunk, doc in filtered_candidates:
                score = float(chunk.score)
                sec_lower = chunk.section.lower()
                content_lower = chunk.content.lower()

                # Boost if section title matches query terms
                title_overlap = sum(1 for w in query_words if len(w) > 3 and w in sec_lower)
                if title_overlap:
                    score += 0.25 * title_overlap

                # Boost if exact phrase is present
                if len(query_lower) > 5 and query_lower in content_lower:
                    score += 0.5

                # Require minimum relevance threshold to avoid returning irrelevant padding
                if score >= min_relevance_score:
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
                "allowed_roles": get_document_allowed_roles(doc.document_id),
                "section_count": len(doc.sections) if doc.sections else 0,
            }

    @staticmethod
    async def search_documents_debug(
        query: str,
        user_role: str = "INVESTIGATOR",
        top_k: int = 4,
    ) -> dict[str, Any]:
        """Debug mode for authorized administrators: reports candidate counts, filtering decisions, and scores."""
        user_role_upper = (user_role or "INVESTIGATOR").upper()
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            service = KnowledgeService(session)
            search_res = await service.search(query, top_k=10)
            candidates = search_res.results

            filtering_log = []
            accepted_candidates = []
            for c in candidates:
                allowed = get_document_allowed_roles(c.document_id)
                has_access = (user_role_upper in allowed) or (user_role_upper == "ADMINISTRATOR")
                decision = "ACCEPTED" if has_access else "REJECTED_RBAC"
                filtering_log.append({
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "section": c.section,
                    "score": c.score,
                    "allowed_roles": allowed,
                    "decision": decision,
                })
                if has_access:
                    accepted_candidates.append(c)

            return {
                "normalized_query": query.strip(),
                "initial_candidate_count": len(candidates),
                "rbac_permitted_count": len(accepted_candidates),
                "selected_top_k_count": min(len(accepted_candidates), top_k),
                "filtering_log": filtering_log,
            }
