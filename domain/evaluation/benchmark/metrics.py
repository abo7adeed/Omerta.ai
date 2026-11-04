"""Benchmark metrics computation for Omerta.ai.

Calculates and documents mathematical formulas for:
- Quality metrics: citation accuracy, evidence coverage, ground truth precision/recall/F1
- Performance metrics: latency distribution (mean, median, P95, min, max), tokens per second
- Hardware metrics: GPU VRAM usage and memory profiling via nvidia-smi
- Cost projections: cost per case and projected cost per 1,000 financial investigations
"""

from __future__ import annotations

import logging
import math
import shutil
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


def get_gpu_vram_usage() -> dict[str, Any]:
    """Profile local NVIDIA GPU VRAM usage using nvidia-smi if available.

    Returns normalized dictionary with measured memory in MB, or explanation if unavailable.
    Formula: Memory Used / Total VRAM * 100
    """
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return {
            "measured": False,
            "vram_used_mb": None,
            "vram_total_mb": None,
            "vram_free_mb": None,
            "gpu_name": None,
            "utilization_pct": None,
            "reason": "nvidia-smi executable not found in PATH",
        }

    try:
        cmd = [
            nvidia_smi,
            "--query-gpu=memory.total,memory.used,memory.free,name",
            "--format=csv,noheader,nounits",
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0, check=True)
        lines = [line.strip() for line in proc.stdout.strip().splitlines() if line.strip()]
        if not lines:
            return {"measured": False, "reason": "No GPU output returned by nvidia-smi"}

        parts = [p.strip() for p in lines[0].split(",")]
        total_mb = float(parts[0])
        used_mb = float(parts[1])
        free_mb = float(parts[2])
        name = parts[3] if len(parts) > 3 else "NVIDIA GPU"
        utilization_pct = round((used_mb / total_mb) * 100.0, 1) if total_mb > 0 else 0.0

        return {
            "measured": True,
            "vram_used_mb": used_mb,
            "vram_total_mb": total_mb,
            "vram_free_mb": free_mb,
            "gpu_name": name,
            "utilization_pct": utilization_pct,
            "reason": None,
        }
    except Exception as exc:
        return {
            "measured": False,
            "vram_used_mb": None,
            "vram_total_mb": None,
            "vram_free_mb": None,
            "gpu_name": None,
            "utilization_pct": None,
            "reason": f"Failed querying nvidia-smi: {str(exc)}",
        }


def compute_citation_metrics(
    report_dict: dict[str, Any],
    evidence_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute citation accuracy and evidence coverage.

    Formulas:
    - Citation Accuracy: (Findings referencing at least 1 valid evidence_id / Total findings) * 100
    - Evidence Coverage: (Unique valid evidence IDs cited in report / Total evidence items available) * 100
    """
    valid_ids = {item["evidence_id"] for item in evidence_items if "evidence_id" in item}
    findings = report_dict.get("findings", [])

    if not isinstance(findings, list) or len(findings) == 0:
        return {
            "citation_accuracy_pct": 0.0,
            "evidence_coverage_pct": 0.0,
            "total_findings": 0,
            "valid_cited_findings": 0,
            "invalid_evidence_ids": [],
            "unique_cited_evidence_count": 0,
            "total_available_evidence_count": len(valid_ids),
        }

    valid_cited_findings = 0
    all_cited_ids: set[str] = set()
    invalid_cited_ids: list[str] = []

    for f in findings:
        if not isinstance(f, dict):
            continue
        cited = f.get("evidence_ids", [])
        if isinstance(cited, list):
            has_valid = False
            for cid in cited:
                all_cited_ids.add(cid)
                if cid in valid_ids:
                    has_valid = True
                else:
                    invalid_cited_ids.append(cid)
            if has_valid:
                valid_cited_findings += 1

    total_findings = len(findings)
    citation_accuracy = round((valid_cited_findings / total_findings) * 100.0, 1)

    intersected_ids = all_cited_ids.intersection(valid_ids)
    evidence_coverage = (
        round((len(intersected_ids) / len(valid_ids)) * 100.0, 1) if len(valid_ids) > 0 else 100.0
    )

    return {
        "citation_accuracy_pct": citation_accuracy,
        "evidence_coverage_pct": evidence_coverage,
        "total_findings": total_findings,
        "valid_cited_findings": valid_cited_findings,
        "invalid_evidence_ids": sorted(list(set(invalid_cited_ids))),
        "unique_cited_evidence_count": len(intersected_ids),
        "total_available_evidence_count": len(valid_ids),
    }


def compute_ground_truth_metrics(
    report_dict: dict[str, Any],
    ground_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    """Calculate precision, recall, and F1 score against case ground truth.

    Formulas:
    - Precision: TP / (TP + FP)
    - Recall: TP / (TP + FN)
    - F1: 2 * Precision * Recall / (Precision + Recall)
    """
    if not ground_truth:
        return {
            "has_ground_truth": False,
            "precision": None,
            "recall": None,
            "f1_score": None,
            "risk_level_matched": None,
            "action_matched": None,
        }

    expected_typologies = set(ground_truth.get("typologies", []))
    raw_pred = report_dict.get("typologies", [])
    predicted_typologies = set(raw_pred) if isinstance(raw_pred, list) else set()

    # Compare typology sets
    tp = len(expected_typologies.intersection(predicted_typologies))
    fp = len(predicted_typologies - expected_typologies)
    fn = len(expected_typologies - predicted_typologies)

    if not expected_typologies and not predicted_typologies:
        precision, recall, f1 = 1.0, 1.0, 1.0
    else:
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    exp_risk = ground_truth.get("expected_risk_level")
    pred_risk = report_dict.get("risk_level")
    risk_matched = (pred_risk == exp_risk) if (exp_risk and pred_risk) else None

    exp_action = ground_truth.get("expected_action")
    pred_action = report_dict.get("recommended_action")
    action_matched = (pred_action == exp_action) if (exp_action and pred_action) else None

    return {
        "has_ground_truth": True,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "risk_level_matched": risk_matched,
        "action_matched": action_matched,
        "expected_typologies": sorted(list(expected_typologies)),
        "predicted_typologies": sorted(list(predicted_typologies)),
    }


def compute_latency_distribution(latencies_ms: list[float]) -> dict[str, float]:
    """Calculate mean, median, P95, min, and max latency.

    Formula for P95: 95th percentile using linear rank interpolation.
    """
    if not latencies_ms:
        return {
            "mean_latency_ms": 0.0,
            "median_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "min_latency_ms": 0.0,
            "max_latency_ms": 0.0,
        }

    sorted_lats = sorted(latencies_ms)
    n = len(sorted_lats)
    mean_val = sum(sorted_lats) / n

    # Median
    if n % 2 == 1:
        med_val = sorted_lats[n // 2]
    else:
        med_val = (sorted_lats[n // 2 - 1] + sorted_lats[n // 2]) / 2.0

    # P95 percentile
    idx = int(math.ceil(0.95 * n)) - 1
    p95_val = sorted_lats[max(0, min(idx, n - 1))]

    return {
        "mean_latency_ms": round(mean_val, 2),
        "median_latency_ms": round(med_val, 2),
        "p95_latency_ms": round(p95_val, 2),
        "min_latency_ms": round(sorted_lats[0], 2),
        "max_latency_ms": round(sorted_lats[-1], 2),
    }


def compute_cost_projections(total_cost_usd: float, total_cases: int) -> dict[str, Any]:
    """Calculate cost per case and projected cost per 1,000 investigations.

    Formula:
    - Cost per case = Total Cost / Max(1, Cases)
    - Projected 1,000 cases cost = Cost per case * 1,000
    Data source: published provider reference rates (Groq / OpenAI) or $0.00 for local Ollama.
    """
    cases_cnt = max(1, total_cases)
    cost_per_case = round(total_cost_usd / cases_cnt, 6)
    projected_1k = round(cost_per_case * 1000.0, 4)

    return {
        "cost_per_case_usd": cost_per_case,
        "projected_cost_per_1000_cases_usd": projected_1k,
        "formula": "Total Cost / Cases * 1,000",
        "currency": "USD",
    }

