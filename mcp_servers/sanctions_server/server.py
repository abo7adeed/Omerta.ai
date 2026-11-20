"""Sanctions & Watchlist Screening MCP Server: read-only screening over OpenSanctions.

Exposes the `screen_entity_against_watchlists` tool via the Model Context Protocol.
All operations are strictly READ-ONLY.

Run locally over stdio:
    python -m mcp_servers.sanctions_server.server
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.server.mcpserver import MCPServer

from mcp_servers.sanctions_server import tools

logger = logging.getLogger(__name__)

server: MCPServer = MCPServer(
    name="omerta-sanctions-server",
    title="Omerta.ai Sanctions & Watchlist Screening MCP Server",
    description=(
        "Read-only sanctions and watchlist screening over OpenSanctions "
        "and international AML regulatory lists with explainable matching."
    ),
    version="0.2.0",
)


@server.tool(
    name="screen_entity_against_watchlists",
    description=(
        "Screen an individual or organization against international sanctions, "
        "PEP, and regulatory watchlists (OFAC, UN, EU, UK, INTERPOL). "
        "Performs Arabic/English entity resolution and returns explainable multi-signal match confidence. "
        "Strictly read-only; rejects SQL/Cypher/shell injection vectors."
    ),
)
async def screen_entity_against_watchlists(
    name: str,
    entity_type: str | None = "individual",
    countries: list[str] | None = None,
    birth_date: str | None = None,
    identification_number: str | None = None,
    threshold: float | None = 0.70,
    limit: int | None = 5,
    specialist: str | None = None,
    auth_token: str | None = None,
) -> dict[str, Any]:
    return await tools.screen_entity_against_watchlists(
        name=name,
        entity_type=entity_type,
        countries=countries,
        birth_date=birth_date,
        identification_number=identification_number,
        threshold=threshold,
        limit=limit,
        specialist=specialist,
        auth_token=auth_token,
    )


if __name__ == "__main__":
    import asyncio
    from mcp.server.stdio import stdio_server

    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(main())

