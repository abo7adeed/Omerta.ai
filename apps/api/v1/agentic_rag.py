"""Agentic RAG and AI Financial Analyst API Router for Omerta.ai.

Endpoints:
1. POST /api/v1/agentic-rag/query
   Executes agentic multi-source retrieval (PostgreSQL, Neo4j, Document RAG),
   deterministic financial analysis, Matplotlib visualization, and synthesized response.
2. GET /api/v1/agentic-rag/artifacts/{artifact_id}
   Secure authenticated chart artifact delivery with traversal protection.
3. GET /api/v1/agentic-rag/status
   Operational telemetry for RAG sources, databases, and analytics modules.
"""

import logging
from pathlib import Path
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse

from apps.agentic_rag.graph import execute_agentic_rag
from domain.agentic_rag.memory import AgenticMemoryManager
from domain.agentic_rag.schemas import (
    AgenticRAGRequest,
    AgenticRAGResponse,
    CreateSessionRequest,
    SessionSummary,
)
from domain.agentic_rag.visualization import ARTIFACTS_DIR
from infrastructure.security.jwt_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agentic-rag", tags=["Agentic RAG & Financial Analysis"])

_ARTIFACT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]+$")


@router.post(
    "/query",
    response_model=AgenticRAGResponse,
    summary="Execute Agentic RAG and Financial Analysis Query",
    description="Processes natural-language questions through LangGraph orchestrator, querying PostgreSQL, Neo4j, and Document KB as appropriate.",
)
async def query_agentic_rag(
    request: AgenticRAGRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AgenticRAGResponse:
    """Execute authenticated Agentic RAG query with session memory."""
    user_role = current_user.get("role", "INVESTIGATOR")
    user_id = str(current_user.get("sub", "default_investigator"))

    session_id = request.conversation_id or f"sess-{user_id[:8]}"
    request.conversation_id = session_id

    try:
        response = await execute_agentic_rag(
            request=request,
            user_role=user_role,
            user_id=user_id,
        )
        response.conversation_id = session_id

        # Persist conversation turn into session memory
        try:
            AgenticMemoryManager.add_turn(
                session_id=session_id,
                user_id=user_id,
                user_query=request.question,
                response_data=response.model_dump(),
                thought_steps=response.thought_steps,
                charts=[c.model_dump() for c in response.charts],
                warnings=response.warnings,
            )
        except Exception as mem_exc:
            logger.warning("Could not persist session turn: %s", mem_exc)

        return response
    except Exception as exc:
        logger.exception("Agentic RAG execution failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "AGENTIC_RAG_FAILURE", "message": str(exc)},
        )


@router.get(
    "/sessions",
    response_model=list[SessionSummary],
    summary="List Chat Sessions",
    description="Returns all conversation sessions for the authenticated investigator, sorted by last updated.",
)
async def list_chat_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List chat sessions for the active user."""
    user_id = str(current_user.get("sub", "default_investigator"))
    return AgenticMemoryManager.list_user_sessions(user_id=user_id)


@router.get(
    "/sessions/{session_id}",
    summary="Get Chat Session Detail",
    description="Returns full sequential messages, metrics, charts, and reasoning traces for a specific session.",
)
async def get_chat_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve full session detail including message turns."""
    user_id = str(current_user.get("sub", "default_investigator"))
    session = AgenticMemoryManager.get_session(session_id, user_id=user_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' does not exist or access is denied."},
        )
    return session.model_dump()


@router.post(
    "/sessions",
    summary="Create New Chat Session",
    description="Initializes a new empty investigation session like ChatGPT New Chat.",
)
async def create_chat_session(
    payload: CreateSessionRequest | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Initialize a new chat session."""
    user_id = str(current_user.get("sub", "default_investigator"))
    title = payload.title if payload else None
    new_sess = AgenticMemoryManager.create_session(user_id=user_id, title=title)
    return new_sess.model_dump()


@router.delete(
    "/sessions/{session_id}",
    summary="Delete Chat Session",
    description="Permanently removes a conversation session and its stored history.",
)
async def delete_chat_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a chat session."""
    user_id = str(current_user.get("sub", "default_investigator"))
    success = AgenticMemoryManager.delete_session(session_id, user_id=user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' not found or could not be deleted."},
        )
    return {"status": "DELETED", "session_id": session_id}



@router.get(
    "/artifacts/{artifact_id}",
    summary="Retrieve Secure Chart Artifact",
    description="Delivers generated Matplotlib PNG charts with authentication and path-traversal protection.",
)
async def get_chart_artifact(
    artifact_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> FileResponse:
    """Serve validated PNG chart artifact."""
    if not _ARTIFACT_ID_PATTERN.match(artifact_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_ARTIFACT_ID", "message": "Artifact ID contains illegal characters."},
        )

    file_path = (ARTIFACTS_DIR / f"{artifact_id}.png").resolve()

    # Enforce path containment
    try:
        if not file_path.is_relative_to(ARTIFACTS_DIR):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCESS_DENIED", "message": "Illegal artifact path access."},
            )
    except AttributeError:
        # Python < 3.9 fallback if is_relative_to is not present
        if ARTIFACTS_DIR not in file_path.parents and file_path != ARTIFACTS_DIR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "ACCESS_DENIED", "message": "Illegal artifact path access."},
            )

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "ARTIFACT_NOT_FOUND", "message": f"Artifact '{artifact_id}' does not exist."},
        )

    return FileResponse(
        path=str(file_path),
        media_type="image/png",
        filename=f"{artifact_id}.png",
    )


@router.get(
    "/status",
    summary="Agentic RAG System Status",
    description="Returns telemetry on RAG source availability, models, and ingestion statistics.",
)
async def get_system_status(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Operational status report of the Agentic RAG system."""
    import os
    from infrastructure.database.session import get_engine
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import AsyncSession
    from infrastructure.database.models import KnowledgeDocument, KnowledgeChunk

    doc_count = 0
    chunk_count = 0
    try:
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            doc_count = await session.scalar(select(func.count(KnowledgeDocument.id))) or 0
            chunk_count = await session.scalar(select(func.count(KnowledgeChunk.id))) or 0
    except Exception as exc:
        logger.warning("Could not fetch document counts: %s", exc)

    llm_provider = os.getenv("LLM_PROVIDER", "groq")
    groq_model = os.getenv("LLM_MODEL") or os.getenv("GROQ_MODEL_ID", "openai/gpt-oss-120b")
    has_api_key = bool(os.getenv("GROQ_API_KEY") or os.getenv("LLM_API_KEY"))

    return {
        "status": "OPERATIONAL",
        "sources": {
            "postgresql": "ONLINE",
            "neo4j": "ONLINE",
            "document_kb": {
                "status": "ONLINE",
                "indexed_documents": doc_count,
                "indexed_chunks": chunk_count,
            },
        },
        "llm": {
            "provider": llm_provider,
            "model_id": groq_model,
            "configured": has_api_key,
        },
        "analytics_engine": "ACTIVE",
        "visualization_engine": "ACTIVE",
    }


@router.get(
    "/documents",
    summary="List Knowledge Base Documents",
    description="Returns all ingested policy and governance documents in the vector knowledge store.",
)
async def list_knowledge_documents(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all indexed documents with chunk statistics."""
    from infrastructure.database.session import get_engine
    from sqlalchemy import select, func
    from sqlalchemy.ext.asyncio import AsyncSession
    from infrastructure.database.models import KnowledgeDocument, KnowledgeChunk

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        docs = (await session.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.document_id))).all()
        result = []
        for d in docs:
            chunk_cnt = await session.scalar(
                select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.document_id == d.document_id)
            ) or 0
            result.append({
                "document_id": d.document_id,
                "title": d.title,
                "document_type": d.document_type,
                "jurisdiction": d.jurisdiction,
                "effective_date": d.effective_date,
                "version": d.version,
                "source": d.source,
                "chunk_count": chunk_cnt,
            })
        return result


@router.post(
    "/documents/upload",
    summary="Upload Document to Knowledge Base Vector Store",
    description="Uploads a PDF, Markdown, DOCX, or text file into the knowledge base, chunks and indexes it into the vector database.",
)
async def upload_knowledge_document(
    file: UploadFile = File(...),
    category: str = Form("General"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Upload and index a new document into the knowledge store."""
    import shutil
    from infrastructure.database.session import get_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from infrastructure.knowledge.ingest import load_any_document, ingest_document_into_db

    allowed_exts = {".md", ".txt", ".pdf", ".docx"}
    filename = file.filename or "uploaded_document.txt"
    file_ext = Path(filename).suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "INVALID_FILE_TYPE", "message": f"Unsupported file type '{file_ext}'. Allowed formats: {list(allowed_exts)}"},
        )

    docs_dir = Path("infrastructure/knowledge/documents")
    docs_dir.mkdir(parents=True, exist_ok=True)
    clean_stem = re.sub(r"[^a-zA-Z0-9_\-]", "_", Path(filename).stem)
    target_path = docs_dir / f"{clean_stem}{file_ext}"

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as exc:
        logger.error("Failed to save uploaded file: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "SAVE_FAILED", "message": f"Could not save uploaded file: {str(exc)}"},
        )

    try:
        doc = load_any_document(target_path)
        if category:
            doc.category = category
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            chunks_count = await ingest_document_into_db(session, doc)
            await session.commit()

        logger.info("Successfully uploaded and indexed document %s (%d chunks)", doc.document_id, chunks_count)
        return {
            "success": True,
            "document_id": doc.document_id,
            "title": doc.title,
            "category": doc.category,
            "document_type": doc.document_type,
            "version": doc.version,
            "chunks_indexed": chunks_count,
            "content_hash": doc.content_hash,
            "message": f"Document '{doc.document_id}' successfully parsed, chunked, and stored in vector database ({chunks_count} chunks).",
        }
    except Exception as exc:
        logger.exception("Failed to parse and index uploaded document: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "INGESTION_FAILED", "message": f"Failed to parse and index document: {str(exc)}"},
        )


@router.delete(
    "/documents/{document_id}",
    summary="Delete Knowledge Base Document",
    description="Deletes an indexed document and its chunks from PostgreSQL, TF-IDF vector index, and disk.",
)
async def delete_knowledge_document(
    document_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete a document from the vector store."""
    from infrastructure.database.session import get_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from infrastructure.knowledge.ingest import delete_document_from_db

    clean_id = document_id.strip()
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        deleted = await delete_document_from_db(session, clean_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": f"Document '{clean_id}' was not found in knowledge store."},
            )
        await session.commit()

    logger.info("Successfully deleted document %s from knowledge store", clean_id)
    return {
        "success": True,
        "document_id": clean_id,
        "message": f"Document '{clean_id}' and all associated chunks were successfully deleted from vector database.",
    }

