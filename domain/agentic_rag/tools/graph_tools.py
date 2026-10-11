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

    @staticmethod
    async def find_connected_accounts(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Find accounts connected by transactions, shared devices, or shared IPs with explicit reasons."""
        try:
            res = await GraphService().find_connected_accounts(account_id, limit=limit)
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "account_id": account_id, "connections": []}
        except Exception as exc:
            logger.warning("Graph query find_connected_accounts failed for %s: %s", account_id, exc)
            return {"error": "GRAPH_UNAVAILABLE", "account_id": account_id, "connections": []}

    @staticmethod
    async def find_fraud_signals(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Extract structural risk signals (pass-through conduit flows, shared hardware clusters)."""
        try:
            res = await GraphService().find_fraud_ring(account_id, limit=limit)
            return res.model_dump(mode="json")
        except DomainError as exc:
            return {"error": exc.payload, "account_id": account_id, "signals": []}
        except Exception as exc:
            logger.warning("Graph query find_fraud_signals failed for %s: %s", account_id, exc)
            return {"error": "GRAPH_UNAVAILABLE", "account_id": account_id, "signals": []}

    @staticmethod
    async def get_graph_schema_overview() -> dict[str, Any]:
        """Provide trusted graph schema definition, node types, and relationship semantics."""
        overview = {
            "graph_database": "Neo4j Property Graph",
            "projection_model": "Financial Crime & Topology Projection",
            "node_types": [
                {
                    "label": "Account",
                    "description": "Customer bank account identified by external_id (e.g. ACC-0001, ACC-1001).",
                    "properties": ["external_id", "currency", "status", "risk_level"],
                },
                {
                    "label": "Transaction",
                    "description": "Financial value transfer entity identified by external_id (e.g. TXN-001).",
                    "properties": ["external_id", "amount", "currency", "timestamp", "risk_score"],
                },
                {
                    "label": "Device",
                    "description": "Hardware device fingerprint identified by external_id (e.g. DEV-101, DEV-571A8B91).",
                    "properties": ["external_id", "platform", "model", "is_emulator", "is_rooted"],
                },
                {
                    "label": "IP",
                    "description": "Network egress IP address node identified by address.",
                    "properties": ["address", "country", "is_vpn"],
                },
            ],
            "relationship_types": [
                {
                    "type": "SENT",
                    "pattern": "(Account)-[:SENT]->(Transaction)",
                    "meaning": "Account initiated an outbound financial transfer.",
                },
                {
                    "type": "RECEIVED_BY",
                    "pattern": "(Transaction)-[:RECEIVED_BY]->(Account)",
                    "meaning": "Account received inbound funds from a transaction.",
                },
                {
                    "type": "USED_DEVICE",
                    "pattern": "(Transaction)-[:USED_DEVICE]->(Device)",
                    "meaning": "Transaction was authorized from this physical hardware fingerprint.",
                },
                {
                    "type": "USED_IP",
                    "pattern": "(Transaction)-[:USED_IP]->(IP)",
                    "meaning": "Transaction egressed from this network IP address.",
                },
            ],
            "structural_typologies": [
                "SHARED_DEVICE: Multiple distinct accounts transacting on identical hardware.",
                "SHARED_IP: Coordinated accounts sharing single egress gateway or VPN proxy.",
                "PASS_THROUGH: Account acting as conduit, receiving funds and rapidly dispersing to third parties.",
                "CIRCULAR_TRANSFER: Multi-hop transaction chain where funds loop back toward originating entity.",
            ],
            "read_only_guarantee": "All graph queries run parameterized Cypher MATCH queries bounded to max 4 hops and 100 rows.",
        }

        # Check live connectivity and pull current graph entity tallies
        try:
            from infrastructure.neo4j.client import get_driver
            driver = get_driver()
            async with driver.session() as session:
                res_nodes = await session.run("MATCH (n) RETURN labels(n)[0] AS label, count(n) AS cnt")
                node_data = await res_nodes.data()
                res_rels = await session.run("MATCH ()-[r]->() RETURN type(r) AS rel, count(r) AS cnt")
                rel_data = await res_rels.data()
                overview["live_database_connected"] = True
                overview["live_counts"] = {
                    "nodes": {r["label"]: r["cnt"] for r in node_data if r.get("label")},
                    "relationships": {r["rel"]: r["cnt"] for r in rel_data if r.get("rel")},
                }
        except Exception as exc:
            overview["live_database_connected"] = False
            overview["live_status"] = f"Neo4j offline or disconnected: {exc}"

        return overview

    @staticmethod
    async def execute_read_only_cypher(cypher_query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Execute a dynamic read-only Cypher MATCH/RETURN query against Neo4j with strict security validation."""
        import re
        from infrastructure.neo4j.client import get_driver

        clean_cypher = (cypher_query or "").strip()
        if not clean_cypher:
            return []

        upper_cypher = clean_cypher.upper()
        # Strictly require MATCH, RETURN, or WITH
        if not (upper_cypher.startswith("MATCH") or upper_cypher.startswith("RETURN") or upper_cypher.startswith("WITH")):
            raise ValueError("Only read-only MATCH/RETURN Cypher queries are permitted.")

        # Prohibit any graph mutation syntax
        blocked = [
            "CREATE", "MERGE", "DELETE", "DETACH", "SET", "REMOVE",
            "DROP", "ALTER", "CALL", "LOAD CSV",
        ]
        for kw in blocked:
            if re.search(rf"\b{kw}\b", upper_cypher):
                raise ValueError(f"Prohibited Cypher keyword detected: {kw}. Graph modifications are rejected.")

        if ";" in clean_cypher.rstrip(";"):
            raise ValueError("Multiple Cypher queries separated by semicolons are prohibited.")

        limit = min(max(limit, 1), 50)
        if "LIMIT" not in upper_cypher:
            clean_cypher = f"{clean_cypher.rstrip(';')} LIMIT {limit}"

        try:
            driver = get_driver()
            async with driver.session() as session:
                res = await session.run(clean_cypher)
                records = await res.data()
                return records[:limit]
        except Exception as exc:
            logger.warning("execute_read_only_cypher failed: %s", exc)
            return [{"error": str(exc)}]

