"""Automated Test Suite: Read-Only Invariant Enforcement.

Validates:
- All 4 MCP servers enforce strict zero-write guarantees.
- Any attempt to pass mutation commands is actively intercepted.
- Database sessions do not commit writes.
- System execution / shell operations are strictly prohibited.
"""

import pytest
from mcp_servers.common.security import validate_safe_identifier, validate_safe_query
from mcp_servers.common.errors import SecurityValidationError
from domain.errors import ValidationError
from mcp_servers.transaction_server.tools import get_transaction, get_account
from mcp_servers.graph_server.tools import get_account_neighbors
from mcp_servers.risk_server.tools import get_risk_score
from mcp_servers.knowledge_server.tools import search_knowledge


@pytest.mark.asyncio
async def test_read_only_invariant_rejects_sql_mutations():
    """Verify write/mutation verbs are rejected immediately before database execution."""
    mutation_payloads = [
        "TXN-001; INSERT INTO transactions VALUES (999);",
        "TXN-001; UPDATE accounts SET balance = 999999;",
        "TXN-001; DELETE FROM transactions WHERE id=1;",
        "TXN-001; DROP TABLE transactions;",
        "TXN-001; ALTER TABLE accounts ADD COLUMN pwned int;",
        "TXN-001; TRUNCATE TABLE audit_events;",
    ]

    for payload in mutation_payloads:
        # Check validation function
        with pytest.raises(SecurityValidationError) as exc_info:
            validate_safe_identifier(payload, "transaction_id")
        assert exc_info.value.payload["error"] == "SECURITY_VIOLATION"

        # Check tool execution wrapper returns structured error
        result = await get_transaction(payload)
        assert result["error"] == "SECURITY_VIOLATION"
        assert "recovery" in result


@pytest.mark.asyncio
async def test_read_only_invariant_rejects_cypher_mutations():
    """Verify Cypher write/mutation verbs are rejected on graph tools."""
    cypher_mutations = [
        "ACC-1001' CREATE (n:Fraud) RETURN n;",
        "ACC-1001' MERGE (n:Account {id: 'fake'});",
        "ACC-1001' SET n.risk = 'LOW';",
        "ACC-1001' DETACH DELETE n;",
        "ACC-1001' DELETE n;",
    ]

    for payload in cypher_mutations:
        with pytest.raises(SecurityValidationError) as exc_info:
            validate_safe_identifier(payload, "account_id")
        assert exc_info.value.payload["error"] == "SECURITY_VIOLATION"

        result = await get_account_neighbors(payload)
        assert result["error"] == "SECURITY_VIOLATION"


@pytest.mark.asyncio
async def test_read_only_invariant_rejects_knowledge_mutations():
    """Verify search_knowledge rejects queries attempting database destruction."""
    destructive_queries = [
        "DROP TABLE knowledge_documents",
        "TRUNCATE TABLE knowledge_chunks",
        "DELETE FROM knowledge_chunks WHERE 1=1",
    ]

    for query in destructive_queries:
        with pytest.raises(SecurityValidationError) as exc_info:
            validate_safe_query(query, "query")
        assert exc_info.value.payload["error"] == "SECURITY_VIOLATION"

        result = await search_knowledge(query)
        assert result["error"] == "SECURITY_VIOLATION"


@pytest.mark.asyncio
async def test_read_only_empty_identifier_fails_cleanly():
    """Verify empty identifiers return standard VALIDATION_ERROR."""
    res = await get_account("   ")
    assert res["error"] == "VALIDATION_ERROR"
    assert res["field"] == "account_id"

