"""Transaction MCP server: read-only investigation tools over PostgreSQL.

Exposes six tools via the Model Context Protocol. The server holds no data of
its own - every call flows through the domain service to PostgreSQL.
All operations are strictly READ-ONLY.

Run locally over stdio:
    uv run python -m mcp_servers.transaction_server.server
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.transaction_server import tools

server: MCPServer = MCPServer(
    name="omerta-transaction-server",
    title="Omerta.ai Transaction MCP Server",
    description=(
        "Read-only transaction, account, device, and IP investigation "
        "facts sourced from the Omerta.ai PostgreSQL database."
    ),
    version="0.2.0",
)


@server.tool(
    name="get_transaction",
    description=(
        "Get transaction facts (sender, recipient, amount, currency, device, IP, status) by external id. "
        "Read-only; rejects SQL/shell mutation vectors."
    ),
)
async def get_transaction(
    transaction_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_transaction(transaction_id, specialist=specialist, auth_token=auth_token)


@server.tool(
    name="get_account",
    description=(
        "Get account ledger facts and KYC profile by external account id, e.g. 'ACC-1001'. "
        "Read-only; strictly bounds input identifiers."
    ),
)
async def get_account(
    account_id: str,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_account(account_id, specialist=specialist, auth_token=auth_token)


@server.tool(
    name="get_account_transactions",
    description=(
        "Get an account's transaction history (newest first); sender or recipient side. "
        "Supports token-bounded limit (1-100) and cursor pagination. Read-only."
    ),
)
async def get_account_transactions(
    account_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_account_transactions(
        account_id, limit=limit, cursor=cursor, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="get_recipient_history",
    description=(
        "Get transactions where the account is the recipient (mule/layering analysis). "
        "Supports token-bounded limit (1-100) and cursor pagination. Read-only."
    ),
)
async def get_recipient_history(
    recipient_account_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_recipient_history(
        recipient_account_id, limit=limit, cursor=cursor, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="get_device_history",
    description=(
        "Get transactions from a device, e.g. 'DEV-123'; reveals shared-device multi-accounting patterns. "
        "Supports token-bounded limit (1-100) and cursor pagination. Read-only."
    ),
)
async def get_device_history(
    device_id: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_device_history(
        device_id, limit=limit, cursor=cursor, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="get_ip_history",
    description=(
        "Get transactions from an IP address; exposes shared network/proxy patterns. "
        "Supports token-bounded limit (1-100) and cursor pagination. Read-only."
    ),
)
async def get_ip_history(
    ip_address: str,
    limit: int | None = None,
    cursor: str | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_ip_history(
        ip_address, limit=limit, cursor=cursor, specialist=specialist, auth_token=auth_token
    )


def main() -> None:
    """Stdio entrypoint for local development."""
    server.run()


if __name__ == "__main__":
    main()
