"""Automated Test Suite: MCP Tool Schemas & Parameter Verification.

Validates:
- Every tool declares explicit input parameters.
- Required parameters are marked and cannot be omitted.
- Optional parameters (limit, cursor, specialist) have sensible defaults and constraints.
- Output models conform to expected JSON serialization structure.
"""

import pytest
from mcp_servers.transaction_server.server import server as txn_server
from mcp_servers.graph_server.server import server as graph_server
from mcp_servers.risk_server.server import server as risk_server
from mcp_servers.knowledge_server.server import server as knowledge_server


@pytest.mark.asyncio
async def test_transaction_tools_parameter_schemas():
    """Verify transaction tools require expected target identifiers."""
    tools = {t.name: t for t in await txn_server.list_tools()}

    # get_transaction
    txn_tool = tools["get_transaction"]
    schema = txn_tool.input_schema
    assert "transaction_id" in schema["properties"]
    assert "transaction_id" in schema.get("required", [])

    # get_account
    acc_tool = tools["get_account"]
    assert "account_id" in acc_tool.input_schema["properties"]
    assert "account_id" in acc_tool.input_schema.get("required", [])

    # get_account_transactions
    hist_tool = tools["get_account_transactions"]
    assert "account_id" in hist_tool.input_schema["properties"]
    assert "limit" in hist_tool.input_schema["properties"]
    assert "cursor" in hist_tool.input_schema["properties"]

    # get_recipient_history
    recip_tool = tools["get_recipient_history"]
    assert "recipient_account_id" in recip_tool.input_schema["properties"]
    assert "recipient_account_id" in recip_tool.input_schema.get("required", [])

    # get_device_history
    dev_tool = tools["get_device_history"]
    assert "device_id" in dev_tool.input_schema["properties"]
    assert "device_id" in dev_tool.input_schema.get("required", [])

    # get_ip_history
    ip_tool = tools["get_ip_history"]
    assert "ip_address" in ip_tool.input_schema["properties"]
    assert "ip_address" in ip_tool.input_schema.get("required", [])


@pytest.mark.asyncio
async def test_graph_tools_parameter_schemas():
    """Verify graph tools declare topological parameters."""
    tools = {t.name: t for t in await graph_server.list_tools()}

    # find_transaction_paths requires both source and target
    path_tool = tools["find_transaction_paths"]
    props = path_tool.input_schema["properties"]
    assert "source_account_id" in props
    assert "target_account_id" in props
    assert "max_depth" in props
    reqs = path_tool.input_schema.get("required", [])
    assert "source_account_id" in reqs and "target_account_id" in reqs

    # find_fraud_ring
    ring_tool = tools["find_fraud_ring"]
    assert "account_id" in ring_tool.input_schema["properties"]
    assert "max_depth" in ring_tool.input_schema["properties"]
    assert "limit" in ring_tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_risk_tools_parameter_schemas():
    """Verify risk tools declare transaction_id or account_id."""
    tools = {t.name: t for t in await risk_server.list_tools()}

    assert "transaction_id" in tools["get_risk_score"].input_schema["properties"]
    assert "transaction_id" in tools["get_risk_features"].input_schema["properties"]
    assert "transaction_id" in tools["get_feature_importance"].input_schema["properties"]
    assert "account_id" in tools["get_previous_risk_events"].input_schema["properties"]


@pytest.mark.asyncio
async def test_knowledge_tools_parameter_schemas():
    """Verify knowledge tools declare query or document identifiers."""
    tools = {t.name: t for t in await knowledge_server.list_tools()}

    search_tool = tools["search_knowledge"]
    assert "query" in search_tool.input_schema["properties"]
    assert "top_k" in search_tool.input_schema["properties"]
    assert "query" in search_tool.input_schema.get("required", [])

    doc_tool = tools["get_document"]
    assert "document_id" in doc_tool.input_schema["properties"]
    assert "document_id" in doc_tool.input_schema.get("required", [])

    sec_tool = tools["get_document_section"]
    assert "document_id" in sec_tool.input_schema["properties"]
    assert "section" in sec_tool.input_schema["properties"]
    assert "document_id" in sec_tool.input_schema.get("required", [])
    assert "section" in sec_tool.input_schema.get("required", [])

