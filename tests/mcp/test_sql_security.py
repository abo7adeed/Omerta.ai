"""Automated Test Suite: SQL Security & Injection Defense.

Validates:
- Comprehensive defense against SQL injection vectors.
- Multi-statement execution prevention.
- Information schema extraction prevention.
- Machine-readable error codes with actionable recovery instructions.
"""

import pytest
from mcp_servers.common.security import validate_safe_identifier
from mcp_servers.common.errors import SecurityValidationError
from mcp_servers.transaction_server.tools import (
    get_transaction,
    get_account,
    get_account_transactions,
    get_recipient_history,
    get_device_history,
    get_ip_history,
)


@pytest.mark.parametrize(
    "attack_payload",
    [
        "TXN-001; DROP TABLE transactions;--",
        "TXN-001' UNION SELECT username, password_hash, id FROM users;--",
        "TXN-001' UNION ALL SELECT * FROM accounts;--",
        "TXN-001'; UPDATE accounts SET balance = 10000000;--",
        "TXN-001'; INSERT INTO audit_events VALUES ('HACK');--",
        "TXN-001'; DELETE FROM transactions;--",
        "TXN-001'; TRUNCATE TABLE ledger;--",
        "TXN-001'; ALTER TABLE users ADD COLUMN is_admin boolean;--",
        "TXN-001'; GRANT ALL PRIVILEGES ON DATABASE omerta TO attacker;--",
        "TXN-001' AND 1=1 UNION SELECT table_name FROM INFORMATION_SCHEMA.TABLES;--",
    ],
)
def test_validate_safe_identifier_rejects_sql_attacks(attack_payload: str):
    """Verify validator blocks all standard SQL injection vectors."""
    with pytest.raises(SecurityValidationError) as exc_info:
        validate_safe_identifier(attack_payload, "transaction_id")

    payload = exc_info.value.payload
    assert payload["error"] == "SECURITY_VIOLATION"
    assert "field" in payload
    assert "recovery" in payload


@pytest.mark.asyncio
async def test_transaction_tools_intercept_sql_injection():
    """Verify transaction tools safely return error envelope for SQL injection attempts."""
    attack = "TXN-001; DROP TABLE transactions;--"

    res_txn = await get_transaction(attack)
    assert res_txn["error"] == "SECURITY_VIOLATION"

    res_acc = await get_account("ACC-1001' UNION SELECT null;--")
    assert res_acc["error"] == "SECURITY_VIOLATION"

    res_hist = await get_account_transactions("ACC-1001'; DELETE FROM accounts;--")
    assert res_hist["error"] == "SECURITY_VIOLATION"

    res_recip = await get_recipient_history("ACC-9001'; TRUNCATE accounts;--")
    assert res_recip["error"] == "SECURITY_VIOLATION"

    res_dev = await get_device_history("DEV-123'; DROP TABLE devices;--")
    assert res_dev["error"] == "SECURITY_VIOLATION"

    res_ip = await get_ip_history("192.0.2.1'; UPDATE users SET role='ADMIN';--")
    assert res_ip["error"] == "SECURITY_VIOLATION"

