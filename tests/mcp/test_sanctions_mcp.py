"""Tests for Sanctions & Watchlist Screening MCP Server and Tools.

Verifies:
- MCP tool registration and schema exposure
- Strict read-only semantics (no SQL/Cypher/shell injections)
- Fail-closed specialist RBAC and token authentication
- Structured error payloads and recovery metadata
"""

import pytest
from mcp_servers.common.errors import SecurityValidationError, UnauthorizedToolAccessError, AuthenticationRequiredError
from mcp_servers.common.specialist_rbac import generate_specialist_token, check_specialist_permission
from mcp_servers.sanctions_server.server import server as sanctions_mcp_server
from mcp_servers.sanctions_server.tools import screen_entity_against_watchlists


@pytest.mark.asyncio
async def test_sanctions_server_registration():
    """Sanctions server registers screen_entity_against_watchlists tool."""
    assert sanctions_mcp_server.name == "omerta-sanctions-server"
    tools = await sanctions_mcp_server.list_tools()
    tool_names = [t.name for t in tools]
    assert "screen_entity_against_watchlists" in tool_names


def test_sanctions_rbac_permissions():
    """RBAC allowlist grants tool only to authorized specialist agents."""
    assert check_specialist_permission("SanctionsScreeningAgent", "screen_entity_against_watchlists") is True
    assert check_specialist_permission("InvestigatorAgent", "screen_entity_against_watchlists") is True
    assert check_specialist_permission("Orchestrator", "screen_entity_against_watchlists") is True

    # Unauthorized specialists should fail closed
    assert check_specialist_permission("TransactionHistoryAgent", "screen_entity_against_watchlists") is False
    assert check_specialist_permission("BehavioralAnalysisAgent", "screen_entity_against_watchlists") is False
    assert check_specialist_permission("MLRiskAgent", "screen_entity_against_watchlists") is False
    assert check_specialist_permission(None, "screen_entity_against_watchlists") is False


@pytest.mark.asyncio
async def test_sanctions_anonymous_access_denied():
    """Anonymous calls without specialist authentication are rejected."""
    result = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        specialist=None,
    )
    assert result.get("error") == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_sanctions_unauthorized_specialist_denied():
    """Specialists without permission are denied access."""
    token = generate_specialist_token("MLRiskAgent")
    result = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        specialist="MLRiskAgent",
        auth_token=token,
    )
    assert result.get("error") == "UNAUTHORIZED_TOOL_ACCESS"


@pytest.mark.asyncio
async def test_sanctions_tampered_token_denied():
    """Caller with invalid or forged token is rejected."""
    result = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        specialist="InvestigatorAgent",
        auth_token="mcp_v1.InvestigatorAgent.forged_signature_hex",
    )
    assert result.get("error") == "AUTHENTICATION_REQUIRED"


@pytest.mark.asyncio
async def test_sanctions_sql_injection_rejected():
    """SQL mutation injection in name is intercepted and rejected."""
    token = generate_specialist_token("SanctionsScreeningAgent")
    result = await screen_entity_against_watchlists(
        name="'; DROP TABLE customers; --",
        specialist="SanctionsScreeningAgent",
        auth_token=token,
    )
    assert result.get("error") in ("SECURITY_VIOLATION", "INVALID_INPUT")


@pytest.mark.asyncio
async def test_sanctions_shell_injection_rejected():
    """Shell command injection in name or ID is blocked."""
    token = generate_specialist_token("SanctionsScreeningAgent")
    result = await screen_entity_against_watchlists(
        name="Ahmed `powershell -c whoami`",
        specialist="SanctionsScreeningAgent",
        auth_token=token,
    )
    assert result.get("error") in ("SECURITY_VIOLATION", "INVALID_INPUT")


@pytest.mark.asyncio
async def test_sanctions_empty_name_validation():
    """Blank or whitespace-only name returns INVALID_INPUT."""
    token = generate_specialist_token("SanctionsScreeningAgent")
    result = await screen_entity_against_watchlists(
        name="   ",
        specialist="SanctionsScreeningAgent",
        auth_token=token,
    )
    assert result.get("error") == "INVALID_INPUT"

