"""Specialist Agent Role-Based Access Control (RBAC), Authentication, and Least-Privilege Scoping."""

from __future__ import annotations

import hashlib
import hmac
import os
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from mcp_servers.common.errors import (
    AuthenticationRequiredError,
    UnauthorizedToolAccessError,
)

# Secret key for HMAC token signing and verification
MCP_AUTH_SECRET = os.getenv("MCP_AUTH_SECRET", "omerta_mcp_secure_internal_token_secret_2026")

# ContextVar for internal in-process authenticated execution context
_trusted_specialist: ContextVar[str | None] = ContextVar("trusted_specialist", default=None)


@contextmanager
def authenticated_specialist(specialist: str):
    """Context manager: bind an authenticated specialist identity to the current task/coroutine."""
    token = _trusted_specialist.set(normalize_specialist_name(specialist))
    try:
        yield
    finally:
        _trusted_specialist.reset(token)


def get_trusted_specialist() -> str | None:
    """Return the currently bound trusted specialist identity if set."""
    return _trusted_specialist.get()


def generate_specialist_token(specialist: str, secret: str | None = None) -> str:
    """Generate a tamper-proof HMAC-SHA256 authenticated token for a specialist."""
    canonical = normalize_specialist_name(specialist)
    sec = (secret or MCP_AUTH_SECRET).encode("utf-8")
    sig = hmac.new(sec, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"mcp_v1.{canonical}.{sig}"


def verify_specialist_token(token: str, secret: str | None = None) -> tuple[bool, str | None]:
    """Verify an HMAC-SHA256 token and return (is_valid, canonical_specialist)."""
    if not token or not isinstance(token, str):
        return False, None
    parts = token.split(".")
    if len(parts) != 3 or parts[0] != "mcp_v1":
        return False, None
    _, specialist, sig = parts
    sec = (secret or MCP_AUTH_SECRET).encode("utf-8")
    expected_sig = hmac.new(sec, specialist.encode("utf-8"), hashlib.sha256).hexdigest()
    if hmac.compare_digest(sig, expected_sig):
        return True, normalize_specialist_name(specialist)
    return False, None

# Least-privilege tool permissions mapping: Specialist Name -> Set of authorized tool names
SPECIALIST_TOOL_PERMISSIONS: dict[str, set[str]] = {
    "TransactionHistoryAgent": {
        "get_transaction",
        "get_account_transactions",
        "get_recipient_history",
    },
    "BankingRulesAgent": {
        "get_transaction",
        "get_account",
        "get_previous_risk_events",
    },
    "BehavioralAnalysisAgent": {
        "get_account",
        "get_account_transactions",
    },
    "AccountTakeoverAgent": {
        "get_transaction",
        "get_device_history",
        "get_ip_history",
        "get_risk_features",
    },
    "DeviceNetworkAgent": {
        "get_device_history",
        "get_ip_history",
        "find_shared_devices",
        "find_shared_ips",
    },
    "GraphIntelligenceAgent": {
        "get_account_neighbors",
        "find_connected_accounts",
        "find_shared_devices",
        "find_shared_ips",
        "find_transaction_paths",
        "find_fraud_ring",
    },
    "MLRiskAgent": {
        "get_risk_score",
        "get_risk_features",
        "get_feature_importance",
    },
    "MerchantIntelligenceAgent": {
        "get_account",
        "get_account_transactions",
    },
    "IdentitySecurityAgent": {
        "get_account",
        "get_previous_risk_events",
    },
    "FinalDecisionAgent": {
        "search_knowledge",
        "get_document",
        "get_document_section",
        "get_transaction",
        "get_account",
    },
    "InvestigatorAgent": {
        "search_knowledge",
        "get_document",
        "get_document_section",
        "get_transaction",
        "get_account",
        "screen_entity_against_watchlists",
    },
    "SanctionsScreeningAgent": {
        "screen_entity_against_watchlists",
        "search_knowledge",
        "get_document",
    },
    # System / Orchestrator role has full read access across all tools
    "Orchestrator": {
        "get_transaction",
        "get_account",
        "get_account_transactions",
        "get_recipient_history",
        "get_device_history",
        "get_ip_history",
        "get_account_neighbors",
        "find_connected_accounts",
        "find_shared_devices",
        "find_shared_ips",
        "find_transaction_paths",
        "find_fraud_ring",
        "get_risk_score",
        "get_risk_features",
        "get_feature_importance",
        "get_previous_risk_events",
        "search_knowledge",
        "get_document",
        "get_document_section",
        "screen_entity_against_watchlists",
    },
}

# Alias normalization map
_NAME_ALIASES: dict[str, str] = {
    "banking_rules_agent": "BankingRulesAgent",
    "banking_rules_specialist": "BankingRulesAgent",
    "transaction_history_agent": "TransactionHistoryAgent",
    "transaction_history_specialist": "TransactionHistoryAgent",
    "behavioral_analysis_agent": "BehavioralAnalysisAgent",
    "account_takeover_agent": "AccountTakeoverAgent",
    "device_network_agent": "DeviceNetworkAgent",
    "graph_intelligence_agent": "GraphIntelligenceAgent",
    "ml_risk_agent": "MLRiskAgent",
    "merchant_intelligence_agent": "MerchantIntelligenceAgent",
    "identity_security_agent": "IdentitySecurityAgent",
    "final_decision_agent": "FinalDecisionAgent",
    "investigator_agent": "InvestigatorAgent",
    "sanctions_screening_agent": "SanctionsScreeningAgent",
    "sanctions_screening_specialist": "SanctionsScreeningAgent",
    "sanctions_agent": "SanctionsScreeningAgent",
    "system": "Orchestrator",
    "admin": "Orchestrator",
    "orchestrator": "Orchestrator",
}


def normalize_specialist_name(name: str) -> str:
    """Normalize specialist name or alias to canonical form."""
    cleaned = name.strip()
    return _NAME_ALIASES.get(cleaned.lower(), cleaned)


def check_specialist_permission(specialist: str | None, tool_name: str) -> bool:
    """Check if a specialist is authorized to call the specified tool.

    Fails closed:
    - Missing specialist (None or empty): returns False
    - Unknown specialist: returns False
    - Specialist without tool in its allowlist: returns False
    - Authorized specialist with tool in allowlist: returns True
    """
    if not specialist:
        return False

    canonical = normalize_specialist_name(specialist)
    allowed = SPECIALIST_TOOL_PERMISSIONS.get(canonical)
    if allowed is None:
        return False

    return tool_name in allowed


def enforce_specialist_permission(
    specialist: str | None,
    tool_name: str,
    auth_token: str | None = None,
) -> str:
    """Authenticate the caller and enforce least-privilege tool authorization.

    Fails closed:
    1. If missing specialist identity (no specialist, no auth_token, no trusted context):
       Raises AuthenticationRequiredError.
    2. If auth_token is provided:
       Validates HMAC token. If invalid: raises AuthenticationRequiredError.
       If valid: resolves authenticated identity.
    3. If trusted context is active:
       Resolves identity from context.
    4. If only an unauthenticated specialist string is provided without auth_token or trusted context:
       Does not trust caller-provided string for execution:
       - If the specialist is unknown or unauthorized for the tool, fails closed with UnauthorizedToolAccessError.
       - If the specialist would be authorized, rejects with AuthenticationRequiredError because strings alone are not authentication.
    5. If the resolved specialist is not authorized for tool_name:
       Raises UnauthorizedToolAccessError.

    Returns the verified specialist identity on success.
    """
    # Check in-process trusted context
    trusted = _trusted_specialist.get()

    # Check auth_token
    token_spec = None
    if auth_token:
        is_valid, verified_spec = verify_specialist_token(auth_token)
        if not is_valid:
            raise AuthenticationRequiredError(
                detail="Invalid or tampered MCP authentication token."
            )
        token_spec = verified_spec

    # Resolve effective authenticated identity
    authenticated_identity: str | None = None
    if token_spec:
        # If caller passed specialist that contradicts token, reject
        if specialist:
            canonical_spec = normalize_specialist_name(specialist)
            if token_spec != "Orchestrator" and canonical_spec != token_spec:
                raise UnauthorizedToolAccessError(
                    specialist=canonical_spec,
                    tool_name=tool_name,
                    detail=f"Token specialist '{token_spec}' does not match requested specialist '{canonical_spec}'.",
                )
            authenticated_identity = canonical_spec
        else:
            authenticated_identity = token_spec
    elif trusted:
        authenticated_identity = trusted

    # If caller provided neither token nor trusted context:
    if authenticated_identity is None:
        if not specialist:
            # Missing specialist identity: deny
            raise AuthenticationRequiredError(
                detail="Missing specialist identity. Anonymous MCP calls are strictly prohibited."
            )

        canonical = normalize_specialist_name(specialist)
        # Unknown specialist: deny
        if canonical not in SPECIALIST_TOOL_PERMISSIONS:
            raise UnauthorizedToolAccessError(
                specialist=canonical,
                tool_name=tool_name,
                detail=f"Unknown specialist agent: '{canonical}'.",
            )

        # Unauthorized tool: deny
        if not check_specialist_permission(canonical, tool_name):
            raise UnauthorizedToolAccessError(
                specialist=canonical,
                tool_name=tool_name,
            )

        # The specialist string is in the matrix for this tool, BUT caller provided no token or context:
        # "Do not trust a caller-provided specialist string as authentication."
        raise AuthenticationRequiredError(
            detail=f"Specialist '{canonical}' must authenticate via valid auth_token or trusted context. Plain specialist strings are not trusted.",
            recovery=f"Authenticate using a signed token: auth_token=generate_specialist_token('{canonical}').",
        )

    # We have an authenticated identity: verify least-privilege permission
    if not check_specialist_permission(authenticated_identity, tool_name):
        raise UnauthorizedToolAccessError(
            specialist=authenticated_identity,
            tool_name=tool_name,
        )

    return authenticated_identity

