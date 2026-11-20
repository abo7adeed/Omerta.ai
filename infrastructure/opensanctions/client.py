"""OpenSanctions API and Offline Dataset Client.

Provides resilient access to OpenSanctions watchlist data (FollowTheMoney schema):
- Online search via OpenSanctions REST API (https://api.opensanctions.org)
- API key authentication support
- In-memory TTL cache for repeat entity queries
- Automatic retry with exponential backoff on HTTP 429 (Rate Limit)
- Graceful offline fallback to bundled baseline watchlist dataset
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx

from infrastructure.config import get_settings

logger = logging.getLogger(__name__)

_DEFAULT_BASELINE_PATH = Path(__file__).resolve().parent / "data" / "baseline_sanctions.json"


class OpenSanctionsClient:
    """Async client for OpenSanctions screening with network resilience and fallback."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        cache_ttl_seconds: int = 3600,
        baseline_file: Path | str | None = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.opensanctions_base_url or "https://api.opensanctions.org").rstrip("/")
        self.api_key = api_key or settings.opensanctions_api_key or os.getenv("OPENSANCTIONS_API_KEY")
        self.timeout = timeout or settings.opensanctions_timeout_seconds
        self.cache_ttl = cache_ttl_seconds
        self.baseline_path = Path(baseline_file or _DEFAULT_BASELINE_PATH)

        # In-memory TTL cache: key -> (timestamp, data)
        self._cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}
        self._baseline_cache: list[dict[str, Any]] | None = None

    def _get_headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "Omerta-Sanctions-Agent/1.0"}
        if self.api_key:
            headers["Authorization"] = f"ApiKey {self.api_key}"
        return headers

    def _load_baseline_dataset(self) -> list[dict[str, Any]]:
        """Load bundled offline watchlist dataset."""
        if self._baseline_cache is not None:
            return self._baseline_cache

        if not self.baseline_path.exists():
            logger.warning("Baseline sanctions dataset not found at %s", self.baseline_path)
            self._baseline_cache = []
            return []

        try:
            with open(self.baseline_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._baseline_cache = data
                    logger.info("Loaded %d baseline sanctions entities", len(data))
                    return self._baseline_cache
        except Exception as exc:
            logger.exception("Failed loading baseline sanctions dataset: %s", exc)

        self._baseline_cache = []
        return []

    def _search_baseline(
        self,
        query: str,
        schema: str | None = None,
        countries: list[str] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Filter local baseline dataset by name tokens and optional criteria."""
        baseline = self._load_baseline_dataset()
        if not baseline:
            return []

        from domain.services.entity_resolution_service import normalize_name

        q_norm = normalize_name(query).lower().strip()
        q_lower = query.lower().strip()
        q_tokens = set(q_norm.split()).union(set(q_lower.split()))
        matched: list[tuple[float, dict[str, Any]]] = []

        for entity in baseline:
            # Check schema filter (Person, Company, Organization, etc.)
            ent_schema = entity.get("schema", "")
            if schema and schema.lower() != "any":
                if ent_schema.lower() != schema.lower():
                    # Allow Company / Organization interchangeability
                    if not (schema.lower() in ("company", "organization") and ent_schema.lower() in ("company", "organization")):
                        continue

            props = entity.get("properties", {})
            names = props.get("name", []) + props.get("alias", [])
            caption = entity.get("caption", "")
            all_name_strings = [caption] + names

            # Simple token overlap score for baseline filtering
            best_overlap = 0.0
            for name_str in all_name_strings:
                if not name_str:
                    continue
                n_norm = normalize_name(name_str).lower().strip()
                n_str_lower = name_str.lower().strip()

                if q_norm and (q_norm in n_norm or n_norm in q_norm):
                    best_overlap = max(best_overlap, 1.0)
                elif q_lower in n_str_lower or n_str_lower in q_lower:
                    best_overlap = max(best_overlap, 1.0)
                else:
                    n_tokens = set(n_norm.split()).union(set(n_str_lower.split()))
                    if q_tokens and n_tokens:
                        intersection = q_tokens.intersection(n_tokens)
                        if intersection:
                            best_overlap = max(best_overlap, len(intersection) / max(len(q_tokens), len(n_tokens)))

            # Country filter if specified
            if countries:
                ent_countries = [
                    c.lower()
                    for c in (
                        props.get("country", [])
                        + props.get("nationality", [])
                        + props.get("citizenship", [])
                        + props.get("jurisdiction", [])
                    )
                    if c
                ]
                if ent_countries:
                    overlap_country = any(c.lower() in ent_countries for c in countries)
                    if overlap_country:
                        best_overlap += 0.1

            if best_overlap > 0.15:
                matched.append((best_overlap, entity))

        matched.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched[:limit]]

    async def search(
        self,
        query: str,
        schema: str | None = None,
        countries: list[str] | None = None,
        limit: int = 10,
    ) -> tuple[list[dict[str, Any]], str]:
        """Search entities by name/query with network retry and offline fallback.

        Returns:
            tuple[list[dict[str, Any]], str]: (entities_list, source_used: 'ONLINE_API' | 'LOCAL_BASELINE')
        """
        clean_q = query.strip()
        if not clean_q:
            return [], "NO_QUERY"

        # Check in-memory cache
        cache_key = f"{clean_q}::{schema}::{sorted(countries or [])}::{limit}"
        now = time.time()
        if cache_key in self._cache:
            ts, cached_results = self._cache[cache_key]
            if now - ts < self.cache_ttl:
                return cached_results, "CACHE"

        # Always search local baseline dataset for high-priority sanctions list coverage
        baseline_results = self._search_baseline(clean_q, schema=schema, countries=countries, limit=limit)

        url = f"{self.base_url}/search/default"
        params: dict[str, Any] = {"q": clean_q, "limit": limit}
        if schema and schema.lower() != "any":
            params["schema"] = schema

        headers = self._get_headers()

        # Attempt online search with retries for transient issues
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.get(url, params=params, headers=headers)

                    if resp.status_code == 200:
                        data = resp.json()
                        online_results = data.get("results", [])

                        # Merge baseline candidates with online results (preserving high-priority baseline records)
                        seen_ids = set()
                        merged = []
                        for b in baseline_results:
                            bid = b.get("id")
                            if bid:
                                seen_ids.add(bid)
                            merged.append(b)

                        for o in online_results:
                            oid = o.get("id")
                            if oid and oid in seen_ids:
                                continue
                            merged.append(o)
                            if oid:
                                seen_ids.add(oid)

                        self._cache[cache_key] = (now, merged)
                        source = "ONLINE_API" if online_results else "LOCAL_BASELINE"
                        return merged, source

                    if resp.status_code == 429:
                        logger.warning(
                            "OpenSanctions rate limited (429) on attempt %d/%d; backoff...",
                            attempt + 1,
                            max_attempts,
                        )
                        if attempt < max_attempts - 1:
                            await httpx.AsyncClient().sleep(1.0)
                            continue

                    logger.warning(
                        "OpenSanctions API responded with status %d: %s",
                        resp.status_code,
                        resp.text[:200],
                    )
                    break
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RequestError) as exc:
                logger.warning(
                    "OpenSanctions network error on attempt %d/%d: %s",
                    attempt + 1,
                    max_attempts,
                    str(exc),
                )
                if attempt < max_attempts - 1:
                    continue

        # Fallback to local baseline dataset
        logger.info("Serving query '%s' from local baseline sanctions dataset", clean_q)
        baseline_results = self._search_baseline(clean_q, schema=schema, countries=countries, limit=limit)
        self._cache[cache_key] = (now, baseline_results)
        return baseline_results, "LOCAL_BASELINE"
