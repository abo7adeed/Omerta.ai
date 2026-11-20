"""Tool functions for the Graph MCP server (read-only).

Same bridge pattern as the transaction server: JSON in, JSON out, domain
errors as structured payloads, unexpected failures logged without secrets.
All tools strictly enforce read-only graph invariants.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from domain.errors import DomainError
from domain.services.graph_service import GraphService
from mcp_servers.common.security import validate_safe_identifier
from mcp_servers.common.specialist_rbac import enforce_specialist_permission
from mcp_servers.common.token_optimization import validate_and_clamp_limit

logger = logging.getLogger(__name__)


async def _execute(handler: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
    """Run a graph service call and normalize errors to structured payloads."""
    try:
        result = await handler()
        if isinstance(result, dict):
            return result
        return result.model_dump(mode="json")
    except DomainError as exc:
        logger.info("graph tool domain error: %s", exc.payload)
        return exc.payload
    except Exception:
        logger.exception("graph tool failed")
        return {"error": "INTERNAL_ERROR", "detail": "unexpected server error"}


async def get_account_neighbors(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Direct graph neighbors of an account."""

    async def handler():
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "get_account_neighbors", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        return await GraphService().get_account_neighbors(safe_id, clamped_limit)

    return await _execute(handler)


async def find_connected_accounts(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Accounts connected via direct transaction, shared device, or shared IP."""

    async def handler():
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "find_connected_accounts", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        return await GraphService().find_connected_accounts(safe_id, clamped_limit)

    return await _execute(handler)


async def find_shared_devices(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Devices shared with other accounts (relationship signal)."""

    async def handler():
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "find_shared_devices", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        return await GraphService().find_shared_devices(safe_id, clamped_limit)

    return await _execute(handler)


async def find_shared_ips(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """IP addresses shared with other accounts (relationship signal)."""

    async def handler():
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "find_shared_ips", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        return await GraphService().find_shared_ips(safe_id, clamped_limit)

    return await _execute(handler)


async def find_transaction_paths(
    source_account_id: str,
    target_account_id: str,
    max_depth: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Bounded transaction paths between two accounts."""

    async def handler():
        safe_src = validate_safe_identifier(source_account_id, "source_account_id")
        safe_tgt = validate_safe_identifier(target_account_id, "target_account_id")
        enforce_specialist_permission(specialist, "find_transaction_paths", auth_token=auth_token)
        return await GraphService().find_transaction_paths(safe_src, safe_tgt, max_depth)

    return await _execute(handler)


async def find_fraud_ring(
    account_id: str,
    max_depth: int | None = None,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Structural signals (shared infra, pass-through) - evidence, not verdicts."""

    async def handler():
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "find_fraud_ring", auth_token=auth_token)
        clamped_limit = validate_and_clamp_limit(limit)
        return await GraphService().find_fraud_ring(safe_id, max_depth, clamped_limit)

    return await _execute(handler)


__all__ = [
    "find_connected_accounts",
    "find_fraud_ring",
    "find_shared_devices",
    "find_shared_ips",
    "find_transaction_paths",
    "get_account_neighbors",
]
