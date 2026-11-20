"""Tool functions for the Risk MCP server (read-only, mock provider).

Same bridge pattern as Phases 5/6: JSON in, JSON out, domain errors as
structured payloads, unexpected failures logged without secrets.
All tools strictly enforce read-only invariants.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from domain.errors import DomainError
from domain.services.risk_service import RiskService
from infrastructure.database.session import get_mcp_engine
from mcp_servers.common.security import validate_safe_identifier
from mcp_servers.common.specialist_rbac import enforce_specialist_permission
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _execute(handler: Callable[[AsyncSession], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
    """Run a risk service call with a session; normalize errors."""
    session = AsyncSession(get_mcp_engine(), expire_on_commit=False)
    try:
        return await handler(session)
    except DomainError as exc:
        logger.info("risk tool domain error: %s", exc.payload)
        return exc.payload
    except Exception:
        logger.exception("risk tool failed")
        return {"error": "INTERNAL_ERROR", "detail": "unexpected server error"}
    finally:
        await session.close()


async def get_risk_score(
    transaction_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Deterministic mock risk score with explicit MOCK provenance."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(transaction_id, "transaction_id")
        enforce_specialist_permission(specialist, "get_risk_score", auth_token=auth_token)
        result = await RiskService(session).get_risk_score(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_risk_features(
    transaction_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Features derived from PostgreSQL facts (nothing fabricated)."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(transaction_id, "transaction_id")
        enforce_specialist_permission(specialist, "get_risk_features", auth_token=auth_token)
        result = await RiskService(session).get_risk_features(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_feature_importance(
    transaction_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Mock feature contributions - NOT SHAP, NOT a trained model."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(transaction_id, "transaction_id")
        enforce_specialist_permission(specialist, "get_feature_importance", auth_token=auth_token)
        result = await RiskService(session).get_feature_importance(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)


async def get_previous_risk_events(
    account_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Stored alert facts for an account; empty result when none exist."""

    async def handler(session: AsyncSession) -> dict[str, Any]:
        safe_id = validate_safe_identifier(account_id, "account_id")
        enforce_specialist_permission(specialist, "get_previous_risk_events", auth_token=auth_token)
        result = await RiskService(session).get_previous_risk_events(safe_id)
        return result.model_dump(mode="json")

    return await _execute(handler)
