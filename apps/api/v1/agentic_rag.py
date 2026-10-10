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

from fastapi import APIRouter, Depends, HTTPException, status
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
    session = AgenticMemoryManager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "SESSION_NOT_FOUND", "message": f"Session '{session_id}' does not exist."},
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
