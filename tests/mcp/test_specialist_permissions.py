"""Automated Test Suite: Specialist Agent Permissions & Least-Privilege Scoping.

Validates:
- Strict role-based tool access for all 10 Phase 10 specialist agents.
- Least-privilege boundary enforcement across MCP servers.
- Denial of unauthorized tool access with UNAUTHORIZED_TOOL_ACCESS payload.
- System/Orchestrator unrestricted read access.
"""

import pytest
from mcp_servers.common.specialist_rbac import (
    SPECIALIST_TOOL_PERMISSIONS,
    check_specialist_permission,
    enforce_specialist_permission,
)
from mcp_servers.common.errors import UnauthorizedToolAccessError
from mcp_servers.transaction_server.tools import get_transaction, get_account_transactions
from mcp_servers.graph_server.tools import find_fraud_ring
from mcp_servers.risk_server.tools import get_risk_score
from mcp_servers.knowledge_server.tools import search_knowledge


def test_specialist_permission_matrix_structure():
    """Verify all 10 Phase 10 specialists exist in the permission registry."""
    expected_specialists = {
        "TransactionHistoryAgent",
        "BankingRulesAgent",
        "BehavioralAnalysisAgent",
        "AccountTakeoverAgent",
        "DeviceNetworkAgent",
        "GraphIntelligenceAgent",
        "MLRiskAgent",
        "MerchantIntelligenceAgent",
        "IdentitySecurityAgent",
        "FinalDecisionAgent",
        "InvestigatorAgent",
        "Orchestrator",
    }
    for spec in expected_specialists:
        assert spec in SPECIALIST_TOOL_PERMISSIONS
        assert len(SPECIALIST_TOOL_PERMISSIONS[spec]) > 0


def test_banking_rules_agent_permissions():
    """BankingRulesAgent must only access ledger facts and prior alerts, not graph or ML."""
    assert check_specialist_permission("BankingRulesAgent", "get_transaction") is True
    assert check_specialist_permission("BankingRulesAgent", "get_account") is True
    assert check_specialist_permission("BankingRulesAgent", "get_previous_risk_events") is True

    # Denied tools
    assert check_specialist_permission("BankingRulesAgent", "find_fraud_ring") is False
    assert check_specialist_permission("BankingRulesAgent", "get_risk_score") is False
    assert check_specialist_permission("BankingRulesAgent", "search_knowledge") is False


def test_graph_intelligence_agent_permissions():
    """GraphIntelligenceAgent must access graph tools, not ML risk or raw knowledge."""
    for tool in [
        "get_account_neighbors",
        "find_connected_accounts",
        "find_shared_devices",
        "find_shared_ips",
        "find_transaction_paths",
        "find_fraud_ring",
    ]:
        assert check_specialist_permission("GraphIntelligenceAgent", tool) is True

    assert check_specialist_permission("GraphIntelligenceAgent", "get_risk_score") is False
    assert check_specialist_permission("GraphIntelligenceAgent", "search_knowledge") is False


def test_ml_risk_agent_permissions():
    """MLRiskAgent must access risk model tools, not graph tools."""
    assert check_specialist_permission("MLRiskAgent", "get_risk_score") is True
    assert check_specialist_permission("MLRiskAgent", "get_risk_features") is True
    assert check_specialist_permission("MLRiskAgent", "get_feature_importance") is True

    assert check_specialist_permission("MLRiskAgent", "find_fraud_ring") is False
    assert check_specialist_permission("MLRiskAgent", "get_account_transactions") is False


def test_orchestrator_has_full_access():
    """Orchestrator role must have full read permission across all 19 tools."""
    all_tools = [
        "get_transaction", "get_account", "get_account_transactions", "get_recipient_history",
        "get_device_history", "get_ip_history", "get_account_neighbors", "find_connected_accounts",
        "find_shared_devices", "find_shared_ips", "find_transaction_paths", "find_fraud_ring",
        "get_risk_score", "get_risk_features", "get_feature_importance", "get_previous_risk_events",
        "search_knowledge", "get_document", "get_document_section",
    ]
    for tool in all_tools:
        assert check_specialist_permission("Orchestrator", tool) is True


def test_enforce_specialist_permission_raises_unauthorized():
    """enforce_specialist_permission raises UnauthorizedToolAccessError on violation."""
    with pytest.raises(UnauthorizedToolAccessError) as exc_info:
        enforce_specialist_permission("BankingRulesAgent", "find_fraud_ring")

    payload = exc_info.value.payload
    assert payload["error"] == "UNAUTHORIZED_TOOL_ACCESS"
    assert payload["specialist"] == "BankingRulesAgent"
    assert payload["tool"] == "find_fraud_ring"
    assert "recovery" in payload


@pytest.mark.asyncio
async def test_tool_execution_enforces_specialist_boundary():
    """Tool invocation returns UNAUTHORIZED_TOOL_ACCESS payload when specialist is disallowed."""
    # BankingRulesAgent is disallowed from calling find_fraud_ring
    res = await find_fraud_ring("ACC-1001", specialist="BankingRulesAgent")
    assert res["error"] == "UNAUTHORIZED_TOOL_ACCESS"
    assert res["specialist"] == "BankingRulesAgent"
    assert res["tool"] == "find_fraud_ring"

    # TransactionHistoryAgent is disallowed from calling get_risk_score
    res_risk = await get_risk_score("TXN-001", specialist="TransactionHistoryAgent")
    assert res_risk["error"] == "UNAUTHORIZED_TOOL_ACCESS"

