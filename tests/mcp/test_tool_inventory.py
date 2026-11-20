"""Automated Test Suite: MCP Tool Inventory & Server Verification.

Validates:
- All 4 MCP servers exist and are initialized.
- Exactly 19 tools are registered across the platform.
- Tool-to-server mappings match expected architectural catalog.
- Descriptions and metadata are non-empty and informative.
"""

import pytest
from mcp_servers.transaction_server.server import server as txn_server
from mcp_servers.graph_server.server import server as graph_server
from mcp_servers.risk_server.server import server as risk_server
from mcp_servers.knowledge_server.server import server as knowledge_server


@pytest.mark.asyncio
async def test_all_four_servers_exist():
    """Verify all 4 MCP servers are defined with valid names and titles."""
    servers = [txn_server, graph_server, risk_server, knowledge_server]
    assert len(servers) == 4

    assert txn_server.name == "omerta-transaction-server"
    assert graph_server.name == "omerta-graph-server"
    assert risk_server.name == "omerta-risk-server"
    assert knowledge_server.name == "omerta-knowledge-server"

    for s in servers:
        assert s.title is not None and len(s.title) > 0
        assert s.description is not None and len(s.description) > 0
        assert s.version is not None


@pytest.mark.asyncio
async def test_transaction_server_tool_inventory():
    """Verify transaction server registers exactly 6 read-only ledger tools."""
    tools = await txn_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "get_transaction",
        "get_account",
        "get_account_transactions",
        "get_recipient_history",
        "get_device_history",
        "get_ip_history",
    }
    assert tool_names == expected
    assert len(tools) == 6

    for t in tools:
        assert t.description is not None
        assert "read-only" in t.description.lower() or "read-only" in txn_server.description.lower()


@pytest.mark.asyncio
async def test_graph_server_tool_inventory():
    """Verify graph server registers exactly 6 read-only relationship intelligence tools."""
    tools = await graph_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "get_account_neighbors",
        "find_connected_accounts",
        "find_shared_devices",
        "find_shared_ips",
        "find_transaction_paths",
        "find_fraud_ring",
    }
    assert tool_names == expected
    assert len(tools) == 6


@pytest.mark.asyncio
async def test_risk_server_tool_inventory():
    """Verify risk server registers exactly 4 risk calculation and fact tools."""
    tools = await risk_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "get_risk_score",
        "get_risk_features",
        "get_feature_importance",
        "get_previous_risk_events",
    }
    assert tool_names == expected
    assert len(tools) == 4


@pytest.mark.asyncio
async def test_knowledge_server_tool_inventory():
    """Verify knowledge server registers exactly 3 policy and typology retrieval tools."""
    tools = await knowledge_server.list_tools()
    tool_names = {t.name for t in tools}

    expected = {
        "search_knowledge",
        "get_document",
        "get_document_section",
    }
    assert tool_names == expected
    assert len(tools) == 3


@pytest.mark.asyncio
async def test_total_tool_count_is_nineteen():
    """Verify system-wide total of registered MCP tools equals exactly 19."""
    txn_tools = await txn_server.list_tools()
    graph_tools = await graph_server.list_tools()
    risk_tools = await risk_server.list_tools()
    knowledge_tools = await knowledge_server.list_tools()

    total = len(txn_tools) + len(graph_tools) + len(risk_tools) + len(knowledge_tools)
    assert total == 19

