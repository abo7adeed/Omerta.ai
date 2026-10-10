"""Deterministic Financial Analytics Service for Omerta.ai Agentic RAG.

Enforces:
- Deterministic arithmetic (no arbitrary model-generated Python).
- Safe percentage-change calculation with explicit zero-denominator handling.
- Statistical aggregations: mean, median, standard deviation, quantiles, min/max.
- Time-series grouping and period-over-period comparisons.
"""

import math
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from domain.agentic_rag.schemas import (
    ComparisonResult,
    StatisticalSummary,
)


class DeterministicAnalyticsService:
    """Core mathematical and statistical calculation service."""

    @staticmethod
    def calculate_percentage_change(current: float, previous: float) -> tuple[float | None, str]:
        """Compute percentage change using: ((Current - Previous) / Previous) * 100.
        
        Guarantees that division by zero produces an explicit not-applicable indicator.
        """
        if previous == 0.0:
            if current == 0.0:
                return 0.0, "0.0%"
            return None, "N/A (previous period was 0)"
        
        pct = ((current - previous) / previous) * 100.0
        sign = "+" if pct > 0 else ""
        return round(pct, 2), f"{sign}{pct:.2f}%"

    @staticmethod
    def compare_periods(
        current_label: str,
        current_value: float,
        previous_label: str,
        previous_value: float,
        citations: list[str] | None = None,
    ) -> ComparisonResult:
        """Construct a validated period-over-period comparison."""
        diff = current_value - previous_value
        pct_val, pct_str = DeterministicAnalyticsService.calculate_percentage_change(
            current_value, previous_value
        )
        return ComparisonResult(
            current_label=current_label,
            current_value=round(current_value, 2),
            previous_label=previous_label,
            previous_value=round(previous_value, 2),
            absolute_difference=round(diff, 2),
            percentage_change=pct_val,
            percentage_change_display=pct_str,
            is_defined=pct_val is not None,
            citations=citations or [],
        )

    @staticmethod
    def compute_statistics(values: list[float], unit: str = "EGP", citations: list[str] | None = None) -> StatisticalSummary:
        """Compute descriptive statistics over a numeric sample."""
        if not values:
            return StatisticalSummary(
                count=0,
                mean=0.0,
                std_dev=0.0,
                min_val=0.0,
                max_val=0.0,
                median=0.0,
                q25=0.0,
                q75=0.0,
                unit=unit,
                citations=citations or [],
            )

        n = len(values)
        sorted_vals = sorted(values)
        total = sum(sorted_vals)
        mean_val = total / n

        # Sample variance / std-dev
        if n > 1:
            variance = sum((x - mean_val) ** 2 for x in sorted_vals) / (n - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        min_val = sorted_vals[0]
        max_val = sorted_vals[-1]

        def quantile(p: float) -> float:
            idx = (n - 1) * p
            low = int(math.floor(idx))
            high = int(math.ceil(idx))
            if low == high:
                return sorted_vals[low]
            weight = idx - low
            return sorted_vals[low] * (1 - weight) + sorted_vals[high] * weight

        median_val = quantile(0.5)
        q25_val = quantile(0.25)
        q75_val = quantile(0.75)

        return StatisticalSummary(
            count=n,
            mean=round(mean_val, 2),
            std_dev=round(std_dev, 2),
            min_val=round(min_val, 2),
            max_val=round(max_val, 2),
            median=round(median_val, 2),
            q25=round(q25_val, 2),
            q75=round(q75_val, 2),
            unit=unit,
            citations=citations or [],
        )

    @staticmethod
    def group_by_time_bucket(
        records: list[dict[str, Any]],
        timestamp_key: str = "timestamp",
        amount_key: str = "amount",
        bucket: str = "month",  # "day", "week", "month"
    ) -> dict[str, dict[str, float]]:
        """Group records into chronological buckets and aggregate count & sum."""
        buckets: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "total": 0.0})

        for rec in records:
            ts = rec.get(timestamp_key)
            if not ts:
                continue
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    continue

            if bucket == "day":
                key = ts.strftime("%Y-%m-%d")
            elif bucket == "week":
                key = f"{ts.year}-W{ts.isocalendar()[1]:02d}"
            else:  # month
                key = ts.strftime("%Y-%m")

            amt = float(rec.get(amount_key) or 0.0)
            buckets[key]["count"] += 1
            buckets[key]["total"] += amt

        # Sort chronologically
        return {k: {"count": buckets[k]["count"], "total": round(buckets[k]["total"], 2)} for k in sorted(buckets.keys())}
