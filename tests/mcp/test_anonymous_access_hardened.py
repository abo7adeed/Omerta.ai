"""Integration & Security Tests: Fail-Closed Anonymous MCP Access Hardening.

Verifies across all 19 tools in the Omerta.ai MCP catalog:
1. Missing specialist identity (anonymous) is strictly DENIED with AUTHENTICATION_REQUIRED.
2. Caller-provided specialist string without authentication is strictly DENIED with AUTHENTICATION_REQUIRED.
3. Unknown specialist identity is strictly DENIED with UNAUTHORIZED_TOOL_ACCESS.
4. Tampered or corrupted auth_token is strictly DENIED with AUTHENTICATION_REQUIRED.
5. Authorized specialist with valid signed token succeeds or executes within least-privilege boundary.
6. In-process trusted execution context (`authenticated_specialist`) authorizes valid callers.
"""

import pytest
from mcp_servers.common.specialist_rbac import (
    generate_specialist_token,
    authenticated_specialist,
    check_specialist_permission,
    SPECIALIST_TOOL_PERMISSIONS,
)
import mcp_servers.transaction_server.tools as txn_tools
import mcp_servers.graph_server.tools as graph_tools
import mcp_servers.risk_server.tools as risk_tools
import mcp_servers.knowledge_server.tools as knowledge_tools

# Map of all 19 tools with executable sample arguments and an authorized specialist
CATALOG_19_TOOLS = [
    # Transaction Server (6 tools)
    (txn_tools.get_transaction, "get_transaction", {"transaction_id": "TXN-001"}, "TransactionHistoryAgent"),
    (txn_tools.get_account, "get_account", {"account_id": "ACC-1001"}, "BankingRulesAgent"),
    (txn_tools.get_account_transactions, "get_account_transactions", {"account_id": "ACC-1001"}, "TransactionHistoryAgent"),
    (txn_tools.get_recipient_history, "get_recipient_history", {"recipient_account_id": "ACC-1001"}, "TransactionHistoryAgent"),
    (txn_tools.get_device_history, "get_device_history", {"device_id": "DEV-1001"}, "AccountTakeoverAgent"),
    (txn_tools.get_ip_history, "get_ip_history", {"ip_address": "192.168.1.1"}, "AccountTakeoverAgent"),

    # Graph Server (6 tools)
    (graph_tools.get_account_neighbors, "get_account_neighbors", {"account_id": "ACC-1001"}, "GraphIntelligenceAgent"),
    (graph_tools.find_connected_accounts, "find_connected_accounts", {"account_id": "ACC-1001"}, "GraphIntelligenceAgent"),
    (graph_tools.find_shared_devices, "find_shared_devices", {"account_id": "ACC-1001"}, "GraphIntelligenceAgent"),
    (graph_tools.find_shared_ips, "find_shared_ips", {"account_id": "ACC-1001"}, "GraphIntelligenceAgent"),
    (graph_tools.find_transaction_paths, "find_transaction_paths", {"source_account_id": "ACC-1001", "target_account_id": "ACC-1002"}, "GraphIntelligenceAgent"),
    (graph_tools.find_fraud_ring, "find_fraud_ring", {"account_id": "ACC-1001"}, "GraphIntelligenceAgent"),

    # Risk Server (4 tools)
    (risk_tools.get_risk_score, "get_risk_score", {"transaction_id": "TXN-001"}, "MLRiskAgent"),
    (risk_tools.get_risk_features, "get_risk_features", {"transaction_id": "TXN-001"}, "MLRiskAgent"),
    (risk_tools.get_feature_importance, "get_feature_importance", {"transaction_id": "TXN-001"}, "MLRiskAgent"),
    (risk_tools.get_previous_risk_events, "get_previous_risk_events", {"account_id": "ACC-1001"}, "BankingRulesAgent"),

    # Knowledge Server (3 tools)
    (knowledge_tools.search_knowledge, "search_knowledge", {"query": "structuring mule account"}, "FinalDecisionAgent"),
    (knowledge_tools.get_document, "get_document", {"document_id": "DOC-AML-01"}, "FinalDecisionAgent"),
    (knowledge_tools.get_document_section, "get_document_section", {"document_id": "DOC-AML-01", "section": "SEC-01"}, "FinalDecisionAgent"),
]


def test_verify_all_19_tools_registered():
    """Ensure our audit test covers all 19 MCP catalog tools."""
    assert len(CATALOG_19_TOOLS) == 19
    tool_names = {t[1] for t in CATALOG_19_TOOLS}
    assert len(tool_names) == 19


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_anonymous_call_denied(tool_fn, tool_name, kwargs, authorized_agent):
    """Anonymous invocations (missing specialist and missing auth_token) must FAIL CLOSED."""
    res = await tool_fn(**kwargs)
    assert res.get("error") == "AUTHENTICATION_REQUIRED", (
        f"Tool '{tool_name}' allowed anonymous execution! Result: {res}"
    )
    assert "detail" in res


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_unauthenticated_string_denied(tool_fn, tool_name, kwargs, authorized_agent):
    """Caller-provided specialist string without token must NOT be trusted as authentication."""
    res = await tool_fn(**kwargs, specialist=authorized_agent)
    assert res.get("error") == "AUTHENTICATION_REQUIRED", (
        f"Tool '{tool_name}' trusted an unverified caller string '{authorized_agent}'! Result: {res}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_unknown_specialist_denied(tool_fn, tool_name, kwargs, authorized_agent):
    """Passing an unknown or spoofed agent name must fail closed with UNAUTHORIZED_TOOL_ACCESS."""
    res = await tool_fn(**kwargs, specialist="RogueHackerAgent")
    assert res.get("error") == "UNAUTHORIZED_TOOL_ACCESS"
    assert res.get("specialist") == "RogueHackerAgent"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_tampered_token_denied(tool_fn, tool_name, kwargs, authorized_agent):
    """Passing a forged or tampered auth_token must be rejected."""
    tampered_token = f"mcp_v1.{authorized_agent}.deadbeefbadcafe123456"
    res = await tool_fn(**kwargs, specialist=authorized_agent, auth_token=tampered_token)
    assert res.get("error") == "AUTHENTICATION_REQUIRED"
    assert "Invalid or tampered" in res.get("detail", "")


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_authorized_specialist_with_signed_token_accepted(tool_fn, tool_name, kwargs, authorized_agent):
    """Passing a verified HMAC signed token authenticates the specialist successfully."""
    valid_token = generate_specialist_token(authorized_agent)
    res = await tool_fn(**kwargs, specialist=authorized_agent, auth_token=valid_token)
    # The request passed authentication and least-privilege RBAC.
    # Result is either successful data or normal domain response (e.g. NOT_FOUND / empty / result dict),
    # but MUST NOT be AUTHENTICATION_REQUIRED or UNAUTHORIZED_TOOL_ACCESS.
    assert res.get("error") != "AUTHENTICATION_REQUIRED", f"Authentication failed for {tool_name}: {res}"
    assert res.get("error") != "UNAUTHORIZED_TOOL_ACCESS", f"Authorization failed for {tool_name}: {res}"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_fn,tool_name,kwargs,authorized_agent", CATALOG_19_TOOLS)
async def test_trusted_context_authenticates_caller(tool_fn, tool_name, kwargs, authorized_agent):
    """Internal tasks running within authenticated_specialist context are securely authorized."""
    with authenticated_specialist(authorized_agent):
        res = await tool_fn(**kwargs)
        assert res.get("error") != "AUTHENTICATION_REQUIRED", f"Trusted context failed for {tool_name}: {res}"
        assert res.get("error") != "UNAUTHORIZED_TOOL_ACCESS", f"Trusted context unauthorized for {tool_name}: {res}"


@pytest.mark.asyncio
async def test_unauthorized_specialist_with_valid_token_rejected():
    """Even with a valid signed token, a specialist cannot invoke tools outside its allowlist."""
    # BankingRulesAgent is validly signed, but unauthorized for find_fraud_ring
    token = generate_specialist_token("BankingRulesAgent")
    res = await graph_tools.find_fraud_ring(
        account_id="ACC-1001",
        specialist="BankingRulesAgent",
        auth_token=token,
    )
    assert res.get("error") == "UNAUTHORIZED_TOOL_ACCESS"
    assert res.get("specialist") == "BankingRulesAgent"
    assert res.get("tool") == "find_fraud_ring"

