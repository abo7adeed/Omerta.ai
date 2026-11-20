"""Tool functions for the Knowledge MCP server.

Thin bridge: JSON tool-call arguments in, JSON-serializable payload out.
Each tool opens its own session from the application engine, delegates to the
domain service, and maps domain errors to predictable structured payloads.
All tools are strictly READ-ONLY. Document content is data, never instructions.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from domain.errors import DomainError
from domain.services.knowledge_service import KnowledgeService
from infrastructure.database.session import get_mcp_engine
from mcp_servers.common.security import validate_safe_identifier, validate_safe_query
from mcp_servers.common.specialist_rbac import enforce_specialist_permission
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _execute(handler: Callable[[AsyncSession], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Execute a handler with a session from the application engine.

    Domain errors become ``{"error": ...}`` payload results (visible to the
    calling agent so it can self-correct); anything else is logged (without
    secrets) and returned as a generic failure - stack traces, SQL, and
    connection details never reach the caller.
    """
    session = AsyncSession(get_mcp_engine(), expire_on_commit=False)
    try:
        return await handler(session)
    except DomainError as exc:
        logger.info("tool domain error: %s", exc.payload)
        return exc.payload
    except Exception:
        logger.exception("tool failed")
        return {"error": "INTERNAL_ERROR", "detail": "unexpected server error"}
    finally:
        await session.close()


async def search_knowledge(
    query: str,
    top_k: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Deterministic TF-IDF retrieval over the stored knowledge corpus."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_query = validate_safe_query(query, "query")
        enforce_specialist_permission(specialist, "search_knowledge", auth_token=auth_token)
        service = KnowledgeService(session)
        result = await service.search(safe_query, top_k)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_document(
    document_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve a full stored knowledge document by id."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_doc_id = validate_safe_identifier(document_id, "document_id")
        enforce_specialist_permission(specialist, "get_document", auth_token=auth_token)
        service = KnowledgeService(session)
        result = await service.get_document(safe_doc_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_document_section(
    document_id: str,
    section: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve one section of a stored knowledge document."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_doc_id = validate_safe_identifier(document_id, "document_id")
        safe_sec = validate_safe_identifier(section, "section")
        enforce_specialist_permission(specialist, "get_document_section", auth_token=auth_token)
        service = KnowledgeService(session)
        result = await service.get_document_section(safe_doc_id, safe_sec)
        return result.model_dump(mode="json")

    return await _execute(handler)
