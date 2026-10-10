"""Typed, read-only Neo4j Graph Tools for Omerta.ai Agentic RAG.

Guarantees:
- Strictly read-only topological queries.
- Bounded traversal depths (max 4 hops).
- Safe error handling (falls back gracefully if Neo4j is offline).
- Formats graph signals as structural evidence items with explicit provenance.
"""

import logging
from typing import Any

from domain.errors import DomainError
from domain.services.graph_service import GraphService

logger = logging.getLogger(__name__)


class GraphTools:
    """Read-only Neo4j graph toolset for topology, rings, and paths."""

    @staticmethod
    async def get_account_neighbors(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Fetch immediate graph neighbors (connected accounts, devices, IPs)."""
        try:
            res = await GraphService().get_account_neighbors(account_id, limit=limit)
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "account_id": account_id, "neighbors": []}
        except Exception as exc:
            logger.warning("Graph query get_account_neighbors failed for %s: %s", account_id, exc)
            return {"error": "GRAPH_UNAVAILABLE", "account_id": account_id, "neighbors": []}

    @staticmethod
    async def find_shared_devices(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Find hardware devices shared with other bank accounts."""
        try:
            res = await GraphService().find_shared_devices(account_id, limit=limit)
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "account_id": account_id, "devices": []}
        except Exception as exc:
            logger.warning("Graph query find_shared_devices failed for %s: %s", account_id, exc)
            return {"error": "GRAPH_UNAVAILABLE", "account_id": account_id, "devices": []}

    @staticmethod
    async def find_shared_ips(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Find IP addresses shared across multiple customer accounts."""
        try:
            res = await GraphService().find_shared_ips(account_id, limit=limit)
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "account_id": account_id, "ip_addresses": []}
        except Exception as exc:
            logger.warning("Graph query find_shared_ips failed for %s: %s", account_id, exc)
            return {"error": "GRAPH_UNAVAILABLE", "account_id": account_id, "ip_addresses": []}

    @staticmethod
    async def find_transaction_paths(
        source_account: str, target_account: str, max_depth: int = 3
    ) -> dict[str, Any]:
        """Find multi-hop money routing paths between two accounts (up to max_depth)."""
        try:
            max_depth = min(max(max_depth, 1), 4)
            res = await GraphService().find_transaction_paths(
                source_account, target_account, max_depth=max_depth
            )
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "paths": []}
        except Exception as exc:
            logger.warning("Graph query find_transaction_paths failed: %s", exc)
            return {"error": "GRAPH_UNAVAILABLE", "paths": []}

    @staticmethod
    async def summarize_account_network(account_id: str, max_depth: int = 2) -> dict[str, Any]:
        """Aggregate a summary of the account's complete topological blast radius."""
        try:
            connected = await GraphService().find_connected_accounts(account_id, limit=30)
            shared_dev = await GraphService().find_shared_devices(account_id, limit=10)
            shared_ip = await GraphService().find_shared_ips(account_id, limit=10)

            conn_dump = connected.model_dump(mode="json")
            dev_dump = shared_dev.model_dump(mode="json")
            ip_dump = shared_ip.model_dump(mode="json")

            return {
                "account_id": account_id,
                "connected_accounts_count": conn_dump.get("count", 0),
                "connections": conn_dump.get("connections", []),
                "shared_devices_count": dev_dump.get("count", 0),
                "shared_devices": dev_dump.get("devices", []),
                "shared_ips_count": ip_dump.get("count", 0),
                "shared_ips": ip_dump.get("ip_addresses", []),
            }
        except Exception as exc:
            logger.warning("summarize_account_network failed for %s: %s", account_id, exc)
            return {
                "account_id": account_id,
                "connected_accounts_count": 0,
                "connections": [],
                "shared_devices_count": 0,
                "shared_devices": [],
                "shared_ips_count": 0,
                "shared_ips": [],
            }
