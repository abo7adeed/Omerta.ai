"""Graph MCP server: read-only relationship intelligence over Neo4j.

Exposes six tools via MCP. All data comes from the projected Neo4j graph,
which itself is derived from PostgreSQL. All operations are strictly READ-ONLY.

Run locally over stdio:
    uv run python -m mcp_servers.graph_server.server
"""

from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.graph_server import tools

server: MCPServer = MCPServer(
    name="omerta-graph-server",
    title="Omerta.ai Graph MCP Server",
    description=(
        "Read-only relationship intelligence over the projected financial "
        "graph: neighbors, shared devices/IPs, transaction paths, and "
        "structural signals. Evidence only - never fraud verdicts."
    ),
    version="0.2.0",
)


@server.tool(
    name="get_account_neighbors",
    description="Get entities connected to an account: accounts, transactions, devices, IPs. Read-only.",
)
async def get_account_neighbors(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.get_account_neighbors(
        account_id, limit=limit, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="find_connected_accounts",
    description="Find connected accounts with the reason: direct txn, shared device, or shared IP. Read-only.",
)
async def find_connected_accounts(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.find_connected_accounts(
        account_id, limit=limit, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="find_shared_devices",
    description="Find devices used by this account and other accounts (shared-device signal). Read-only.",
)
async def find_shared_devices(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.find_shared_devices(
        account_id, limit=limit, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="find_shared_ips",
    description="Find IPs used by this account and other accounts (shared infrastructure). Read-only.",
)
async def find_shared_ips(
    account_id: str,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.find_shared_ips(
        account_id, limit=limit, specialist=specialist, auth_token=auth_token
    )


@server.tool(
    name="find_transaction_paths",
    description="Find bounded transaction paths between two accounts (max_depth 1-5). Read-only.",
)
async def find_transaction_paths(
    source_account_id: str,
    target_account_id: str,
    max_depth: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.find_transaction_paths(
        source_account_id,
        target_account_id,
        max_depth=max_depth,
        specialist=specialist,
        auth_token=auth_token,
    )


@server.tool(
    name="find_fraud_ring",
    description=(
        "Find structural signals around an account: shared devices, shared IPs, "
        "pass-through flows. Returns graph evidence, never a fraud verdict. Read-only."
    ),
)
async def find_fraud_ring(
    account_id: str,
    max_depth: int | None = None,
    limit: int | None = None,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.find_fraud_ring(
        account_id,
        max_depth=max_depth,
        limit=limit,
        specialist=specialist,
        auth_token=auth_token,
    )


def main() -> None:
    """Stdio entrypoint for local development."""
    server.run()


if __name__ == "__main__":
    main()
