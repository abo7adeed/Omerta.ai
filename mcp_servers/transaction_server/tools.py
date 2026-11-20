"""Tool functions for the Transaction MCP server.

Thin bridge: JSON tool-call arguments in, JSON-serializable payload out.
Each tool opens its own session from the application engine, delegates to the
domain service, and maps domain errors to predictable structured payloads.
All tools are strictly READ-ONLY.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from domain.errors import DomainError
from domain.services.transaction_service import TransactionService
from infrastructure.database.session import get_mcp_engine
from mcp_servers.common.security import validate_safe_identifier
from mcp_servers.common.specialist_rbac import enforce_specialist_permission
from mcp_servers.common.token_optimization import (
    decode_cursor,
    encode_cursor,
    validate_and_clamp_limit,
)
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


async def get_transaction(
    transaction_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve full transaction facts by external transaction id."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(transaction_id, "transaction_id")
        enforce_specialist_permission(specialist, "get_transaction", auth_token=auth_token)
        service = TransactionService(session)
        result = await service.get_transaction(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_account(
    account_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve account facts by external account id."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "get_account", auth_token=auth_token)
        service = TransactionService(session)
        result = await service.get_account(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_account_transactions(
    account_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve the account's transaction history (newest first)."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "get_account_transactions", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        offset = decode_cursor(cursor)
        service = TransactionService(session)
        result = await service.get_account_transactions(safe_id, clamped_limit)
        payload = result.model_dump(mode="json")
        count = payload.get("count", len(payload.get("items", [])))
        truncated = payload.get("truncated", False)
        payload["pagination"] = {
            "offset": offset,
            "returned": count,
            "limit": clamped_limit,
            "has_more": truncated,
            "next_cursor": encode_cursor(offset + count) if truncated else None,
        }
        return payload

    return await _execute(handler)


async def get_recipient_history(
    recipient_account_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve transactions where the account is the recipient."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(recipient_account_id, "recipient_account_id")
        enforce_specialist_permission(specialist, "get_recipient_history", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        offset = decode_cursor(cursor)
        service = TransactionService(session)
        result = await service.get_recipient_history(safe_id, clamped_limit)
        payload = result.model_dump(mode="json")
        count = payload.get("count", len(payload.get("items", [])))
        truncated = payload.get("truncated", False)
        payload["pagination"] = {
            "offset": offset,
            "returned": count,
            "limit": clamped_limit,
            "has_more": truncated,
            "next_cursor": encode_cursor(offset + count) if truncated else None,
        }
        return payload

    return await _execute(handler)


async def get_device_history(
    device_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve transactions performed from a device."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(device_id, "device_id")
        enforce_specialist_permission(specialist, "get_device_history", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        offset = decode_cursor(cursor)
        service = TransactionService(session)
        result = await service.get_device_history(safe_id, clamped_limit)
        payload = result.model_dump(mode="json")
        count = payload.get("count", len(payload.get("items", [])))
        truncated = payload.get("truncated", False)
        payload["pagination"] = {
            "offset": offset,
            "returned": count,
            "limit": clamped_limit,
            "has_more": truncated,
            "next_cursor": encode_cursor(offset + count) if truncated else None,
        }
        return payload

    return await _execute(handler)


async def get_ip_history(
    ip_address: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Retrieve transactions performed from an IP address."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(ip_address, "ip_address")
        enforce_specialist_permission(specialist, "get_ip_history", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        offset = decode_cursor(cursor)
        service = TransactionService(session)
        result = await service.get_ip_history(safe_id, clamped_limit)
        payload = result.model_dump(mode="json")
        count = payload.get("count", len(payload.get("items", [])))
        truncated = payload.get("truncated", False)
        payload["pagination"] = {
            "offset": offset,
            "returned": count,
            "limit": clamped_limit,
            "has_more": truncated,
            "next_cursor": encode_cursor(offset + count) if truncated else None,
        }
        return payload

    return await _execute(handler)
