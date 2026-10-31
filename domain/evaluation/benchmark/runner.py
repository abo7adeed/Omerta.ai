"""Benchmark evaluation runner for Omerta.ai.

Executes synthetic AML scenarios, computes per-dimension statistics, measures
deliberate error detection rates, tracks false passes / false flags, and stores
structured results.
"""

from datetime import UTC, datetime
import json
import logging
from pathlib import Path
import time
from typing import Any

from pydantic import BaseModel, Field

from domain.evaluation.benchmark.scenarios import BenchmarkScenario, get_benchmark_scenarios
from domain.evaluation.evaluator import InvestigationEvaluator
from domain.evaluation.schemas import EvaluationStatus, InvestigationEvaluationResult
from infrastructure.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class ScenarioEvaluationRecord(BaseModel):
    """Execution record for one benchmark scenario."""

    scenario_id: str
    scenario_name: str
    has_deliberate_error: bool
    error_type: str | None
    status: str
    scores: dict[str, int | None]
    deterministic_passed: bool
    human_review_required: bool
    discrepancies: list[str]
    unsupported_claims: list[str]
    detected_deliberate_error: bool
    is_false_pass: bool
    is_false_flag: bool
    latency_ms: float
    summary: str


class BenchmarkRunReport(BaseModel):
    """Aggregate benchmark report with dimension averages and error detection metrics."""

    benchmark_version: str = "1.0"
    executed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    judge_model: str
    judge_provider: str
    total_scenarios: int
    completed_scenarios: int
    failed_scenarios: int
    completion_rate_pct: float

    # Per-dimension averages
    average_scores: dict[str, float]

    # Deliberate error detection performance
    total_deliberate_error_scenarios: int
    deliberate_errors_detected: int
    error_detection_rate_pct: float

    # Confusion metrics against ground truth
    false_passes: int
    false_flags: int

    average_latency_ms: float
    total_latency_ms: float

    records: list[ScenarioEvaluationRecord] = Field(default_factory=list)

    disclaimer: str = (
        "BENCHMARK NOTICE: This benchmark uses small, synthetic, fictional financial crime "
        "scenarios to evaluate judge model alignment, deterministic grounding, and error detection. "
        "It does NOT establish or guarantee real-world regulatory AML effectiveness."
    )


class BenchmarkRunner:
    """Orchestrates running benchmark scenarios and computing performance metrics."""

    def __init__(self, judge_provider: LLMProvider | None = None) -> None:
        self._judge_provider = judge_provider
        self._evaluator = InvestigationEvaluator(judge_provider=judge_provider)

    async def run(
        self,
        scenarios: list[BenchmarkScenario] | None = None,
        output_path: str | Path | None = None,
    ) -> BenchmarkRunReport:
        """Run all benchmark scenarios and generate aggregate analysis."""
        target_scenarios = scenarios or get_benchmark_scenarios()
        records: list[ScenarioEvaluationRecord] = []
        t_start = time.perf_counter()

        judge_name = "default"
        judge_model = "default"

        for sc in target_scenarios:
            t0 = time.perf_counter()
            eval_res = await self._evaluator.evaluate(
                investigation_id=sc.investigation_id,
                report=sc.report,
                evidence=sc.evidence,
                context=sc.context,
                task_description=sc.task_description,
                expected_labels=sc.ground_truth,
                force_run=True,
            )
            sc_latency = round((time.perf_counter() - t0) * 1000, 2)

            judge_name = eval_res.judge_metadata.get("provider", judge_name)
            judge_model = eval_res.judge_metadata.get("model", judge_model)

            # Analyze error detection and false passes / flags
            has_error = sc.ground_truth.get("has_deliberate_error", False)
            error_type = sc.ground_truth.get("error_type")
            overall = eval_res.scores.overall_quality or 0
            grounding = eval_res.scores.evidence_grounding or 0
            reasoning = eval_res.scores.reasoning_quality or 0
            completeness = eval_res.scores.investigation_completeness or 0

            detected = False
            if has_error:
                # Error detected if deterministic checks flagged discrepancies,
                # or if relevant dimension score was appropriately downgraded (<= 3),
                # or unsupported claims / gaps were captured
                if eval_res.deterministic_validation and not eval_res.deterministic_validation.passed:
                    detected = True
                elif error_type in {"FABRICATED_TRANSACTION_ID", "INCORRECT_AMOUNT"} and grounding <= 3:
                    detected = True
                elif error_type == "WEAK_REASONING_LEAP" and reasoning <= 3:
                    detected = True
                elif error_type == "INCOMPLETE_EVIDENCE" and completeness <= 3:
                    detected = True
                elif error_type == "INCORRECT_RELATIONSHIP" and grounding <= 3:
                    detected = True
                elif overall <= 3:
                    detected = True

            # False pass: Scenario had deliberate critical error, but judge gave passing overall score >= 4
            is_false_pass = has_error and not detected and overall >= 4

            # False flag: Clean scenario without deliberate error, but judge failed it (<= 2)
            is_false_flag = (not has_error) and (overall <= 2)

            det_passed = eval_res.deterministic_validation.passed if eval_res.deterministic_validation else True
            discrepancies = eval_res.deterministic_validation.discrepancies if eval_res.deterministic_validation else []

            record = ScenarioEvaluationRecord(
                scenario_id=sc.scenario_id,
                scenario_name=sc.name,
                has_deliberate_error=has_error,
                error_type=error_type,
                status=eval_res.status.value,
                scores={
                    "evidence_grounding": eval_res.scores.evidence_grounding,
                    "reasoning_quality": eval_res.scores.reasoning_quality,
                    "investigation_completeness": eval_res.scores.investigation_completeness,
                    "report_quality": eval_res.scores.report_quality,
                    "overall_quality": eval_res.scores.overall_quality,
                },
                deterministic_passed=det_passed,
                human_review_required=eval_res.human_review_required,
                discrepancies=discrepancies,
                unsupported_claims=eval_res.unsupported_claims,
                detected_deliberate_error=detected,
                is_false_pass=is_false_pass,
                is_false_flag=is_false_flag,
                latency_ms=sc_latency,
                summary=eval_res.summary,
            )
            records.append(record)

        total_time = round((time.perf_counter() - t_start) * 1000, 2)
        total_count = len(records)
        completed = sum(1 for r in records if r.status == EvaluationStatus.COMPLETED.value)
        failed = sum(1 for r in records if r.status == EvaluationStatus.FAILED.value)

        # Calculate dimension averages over non-null completed scores
        avg_scores: dict[str, float] = {}
        for dim in [
            "evidence_grounding",
            "reasoning_quality",
            "investigation_completeness",
            "report_quality",
            "overall_quality",
        ]:
            valid_vals = [r.scores[dim] for r in records if r.scores.get(dim) is not None]
            avg_scores[dim] = round(sum(valid_vals) / len(valid_vals), 2) if valid_vals else 0.0

        error_records = [r for r in records if r.has_deliberate_error]
        errors_detected = sum(1 for r in error_records if r.detected_deliberate_error)
        detection_pct = (
            round((errors_detected / len(error_records)) * 100, 1) if error_records else 100.0
        )

        false_passes = sum(1 for r in records if r.is_false_pass)
        false_flags = sum(1 for r in records if r.is_false_flag)
        avg_latency = round(total_time / total_count, 2) if total_count else 0.0

        report = BenchmarkRunReport(
            judge_model=judge_model,
            judge_provider=judge_name,
            total_scenarios=total_count,
            completed_scenarios=completed,
            failed_scenarios=failed,
            completion_rate_pct=round((completed / total_count) * 100, 1) if total_count else 0.0,
            average_scores=avg_scores,
            total_deliberate_error_scenarios=len(error_records),
            deliberate_errors_detected=errors_detected,
            error_detection_rate_pct=detection_pct,
            false_passes=false_passes,
            false_flags=false_flags,
            average_latency_ms=avg_latency,
            total_latency_ms=total_time,
            records=records,
        )

        if output_path:
            out_p = Path(output_path)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            logger.info("Saved benchmark evaluation report to %s", out_p)

        return report

