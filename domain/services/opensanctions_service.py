"""Domain service for OpenSanctions watchlist operations.

Encapsulates query preparation, external search execution, resilience fallbacks,
and standard entity normalization for downstream matching.
"""

from __future__ import annotations

import logging
from typing import Any

from infrastructure.opensanctions.client import OpenSanctionsClient

logger = logging.getLogger(__name__)


class OpenSanctionsService:
    """Domain service managing watchlist searches, source fallback, and health metrics."""

    def __init__(self, client: OpenSanctionsClient | None = None) -> None:
        self.client = client or OpenSanctionsClient()

    async def search_watchlists(
        self,
        name: str,
        entity_type: str | None = None,
        countries: list[str] | None = None,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], str]:
        """Search watchlists for an entity by name, type, and country.

        Returns:
            tuple[list[dict[str, Any]], str]: List of candidate entities and the source used
            ('ONLINE_API' or 'LOCAL_BASELINE').
        """
        # Map generic entity type to FollowTheMoney schema if needed
        schema_map = {
            "individual": "Person",
            "person": "Person",
            "company": "Company",
            "organization": "Organization",
            "vessel": "Vessel",
            "aircraft": "Airplane",
        }
        schema = schema_map.get((entity_type or "").lower(), entity_type)

        return await self.client.search(
            query=name,
            schema=schema,
            countries=countries,
            limit=limit,
        )

    async def get_health(self) -> dict[str, Any]:
        """Check status of OpenSanctions upstream and local baseline fallback."""
        baseline_entities = self.client._load_baseline_dataset()
        status_info = {
            "upstream_url": self.client.base_url,
            "has_api_key": bool(self.client.api_key),
            "baseline_dataset_loaded": len(baseline_entities) > 0,
            "baseline_entity_count": len(baseline_entities),
            "cache_entries": len(self.client._cache),
            "status": "healthy" if len(baseline_entities) > 0 else "degraded",
        }
        return status_info

