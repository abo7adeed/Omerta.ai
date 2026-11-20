"""Automated Test Suite: Cypher Security & Graph Mutation Defense.

Validates:
- Comprehensive defense against Cypher injection vectors in Neo4j.
- Rejection of node/relationship creation, updates, and deletions.
- Rejection of procedure execution (dbms, apoc).
- Consistent structured error envelopes.
"""

import pytest
from mcp_servers.common.security import validate_safe_identifier
from mcp_servers.common.errors import SecurityValidationError
from mcp_servers.graph_server.tools import (
    get_account_neighbors,
    find_connected_accounts,
    find_shared_devices,
    find_shared_ips,
    find_transaction_paths,
    find_fraud_ring,
)


@pytest.mark.parametrize(
    "attack_payload",
    [
        "ACC-1001' CREATE (n:Pwned {name: 'hacker'}) RETURN n;--",
        "ACC-1001' MERGE (n:AdminAccount {id: 'hack'}) RETURN n;--",
        "ACC-1001' MATCH (n) DETACH DELETE n;--",
        "ACC-1001' MATCH (a:Account) DELETE a;--",
        "ACC-1001' SET n.is_sanctioned = false;--",
        "ACC-1001' REMOVE n.risk_tier;--",
        "ACC-1001' DROP INDEX account_id_index;--",
        "ACC-1001' CALL dbms.procedures() YIELD name RETURN name;--",
        "ACC-1001' CALL apoc.export.csv.all('stolen.csv', {}) YIELD file;--",
    ],
)
def test_validate_safe_identifier_rejects_cypher_attacks(attack_payload: str):
    """Verify validator blocks all standard Cypher injection vectors."""
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_safe_identifier(attack_payload, "account_id")

    payload = exc_info.value.payload
    assert payload["error"] == "SECURITY_VIOLATION"
    assert "field" in payload
    assert "recovery" in payload


@pytest.mark.asyncio
async def test_graph_tools_intercept_cypher_injection():
    """Verify graph tools safely return error envelope for Cypher injection attempts."""
    attack = "ACC-1001' MATCH (n) DETACH DELETE n;--"

    res_nbr = await get_account_neighbors(attack)
    assert res_nbr["error"] == "SECURITY_VIOLATION"

    res_conn = await find_connected_accounts("ACC-1001' CREATE (n:Fake);--")
    assert res_conn["error"] == "SECURITY_VIOLATION"

    res_dev = await find_shared_devices("ACC-1001' SET n.pwned=true;--")
    assert res_dev["error"] == "SECURITY_VIOLATION"

    res_ips = await find_shared_ips("ACC-1001' MERGE (n:IP);--")
    assert res_ips["error"] == "SECURITY_VIOLATION"

    res_paths = await find_transaction_paths(attack, "ACC-9001")
    assert res_paths["error"] == "SECURITY_VIOLATION"

    res_ring = await find_fraud_ring("ACC-1001' CALL dbms.security.listUsers();--")
    assert res_ring["error"] == "SECURITY_VIOLATION"

