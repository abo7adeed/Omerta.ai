"""Tool functions for the Sanctions and Watchlist Screening MCP server.

Enforces:
- Strict read-only semantics (no SQL/Cypher mutations, no shell commands)
- Input parameter sanitization and validation
- Specialist RBAC and caller authentication
- OpenSanctions external query with offline fallback
- Explainable entity resolution and multi-signal scoring
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from domain.errors import DomainError, ValidationError
from domain.services.entity_resolution_service import EntityResolutionService
from domain.services.opensanctions_service import OpenSanctionsService
from mcp_servers.common.errors import SecurityValidationError
from mcp_servers.common.security import (
    validate_safe_identifier,
    validate_safe_query,
)
from mcp_servers.common.specialist_rbac import enforce_specialist_permission

logger = logging.getLogger(__name__)

# Singletons for domain services
_os_service = OpenSanctionsService()
_er_service = EntityResolutionService()


async def screen_entity_against_watchlists(
    name: str,
    entity_type: str | None = "individual",
    countries: list[str] | None = None,
    birth_date: str | None = None,
    identification_number: str | None = None,
    threshold: float | None = 0.70,
    limit: int | None = 5,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    """Screen an entity against international sanctions and watchlists.

    Args:
        name: Full legal name or primary alias of the entity to screen (required).
        entity_type: Type of entity ('individual', 'company', 'organization', 'vessel', 'aircraft', 'any').
        countries: Optional list of ISO 2-letter country codes (e.g. ['US', 'EG']).
        birth_date: Optional ISO date of birth for individuals (e.g. '1982-05-14').
        identification_number: Optional national ID, passport, or tax number.
        threshold: Match confidence threshold between 0.1 and 1.0 (default 0.70).
        limit: Maximum number of ranked candidate matches to return (1-20, default 5).
        specialist: Authorized specialist agent name (e.g., 'SanctionsScreeningAgent').
        auth_token: Optional HMAC authentication token for specialist verification.

    Returns:
        Structured screening report with match indicators, confidence scores, and explainability.
    """
    start_time = time.time()

    # 1. Specialist RBAC & Caller Authentication Enforcement
    try:
        enforce_specialist_permission(specialist, "screen_entity_against_watchlists", auth_token=auth_token)
    except DomainError as exc:
        logger.warning("Sanctions MCP RBAC rejected caller '%s': %s", specialist, exc.message)
        return exc.payload

    # 2. Input Security Validation
    try:
        if not name or not isinstance(name, str) or not name.strip():
            return {
                "error": "INVALID_INPUT",
                "field": "name",
                "detail": "Entity name is required and cannot be empty.",
            }

        safe_name = validate_safe_query(name.strip(), field_name="name", max_length=256)

        safe_id = None
        if identification_number:
            if not isinstance(identification_number, str):
                return {
                    "error": "INVALID_INPUT",
                    "field": "identification_number",
                    "detail": "Identification number must be a string.",
                }
            safe_id = validate_safe_identifier(
                identification_number.strip(),
                field_name="identification_number",
                max_length=64,
            )

        # Validate and clamp parameters
        clamped_threshold = max(0.1, min(1.0, float(threshold or 0.70)))
        clamped_limit = max(1, min(20, int(limit or 5)))

        # Sanitize country codes
        safe_countries: list[str] = []
        if countries:
            for c in countries:
                if isinstance(c, str) and len(c.strip()) in (2, 3):
                    safe_countries.append(c.strip().upper())

    except (ValidationError, SecurityValidationError) as exc:
        logger.warning("Sanctions MCP security validation failed: %s", exc)
        return exc.payload
    except Exception as exc:
        logger.exception("Unexpected validation error in sanctions screening: %s", exc)
        return {"error": "INVALID_INPUT", "detail": str(exc)}

    # 3. Query Watchlists via OpenSanctions Domain Service
    try:
        candidates, source_used = await _os_service.search_watchlists(
            name=safe_name,
            entity_type=entity_type,
            countries=safe_countries,
            limit=25,
        )
    except Exception as exc:
        logger.exception("Watchlist search query failed: %s", exc)
        return {
            "error": "SOURCE_UNAVAILABLE",
            "detail": f"Failed to query watchlist sources: {str(exc)}",
        }

    # 4. Multi-Signal Scoring and Ranking via Entity Resolution Engine
    query_entity = {
        "name": safe_name,
        "entity_type": entity_type,
        "countries": safe_countries,
        "birth_date": birth_date.strip() if birth_date else None,
        "identification_number": safe_id,
    }

    ranked_matches = _er_service.resolve_and_rank(query_entity, candidates, limit=clamped_limit)

    # Filter to potential matches that meet or exceed threshold
    significant_matches = [m for m in ranked_matches if m["confidence_score"] >= clamped_threshold]

    match_found = len(significant_matches) > 0
    best_confidence = significant_matches[0]["confidence_score"] if significant_matches else (
        ranked_matches[0]["confidence_score"] if ranked_matches else 0.0
    )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    return {
        "query_echo": {
            "name": safe_name,
            "entity_type": entity_type,
            "countries": safe_countries,
            "birth_date": birth_date,
            "identification_number": safe_id,
            "threshold": clamped_threshold,
        },
        "match_found": match_found,
        "best_match_confidence": best_confidence,
        "review_required": match_found,  # Human review is always mandatory on a match
        "matched_entities": significant_matches if match_found else ranked_matches[:2],
        "total_candidates_analyzed": len(candidates),
        "execution_metadata": {
            "latency_ms": latency_ms,
            "source_queried": source_used,
            "timestamp": datetime.now(UTC).isoformat(),
            "status_code": "MATCH_FOUND" if match_found else "NO_MATCH",
        },
    }

