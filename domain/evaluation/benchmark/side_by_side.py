"""Reproducible Side-by-Side LLM Model Benchmark Runner for Omerta.ai.

Coordinates candidate generation (Model A vs Model B) on identical inputs,
deterministic validation, anonymized LLM-as-a-Judge evaluation, token/cost estimation,
Langfuse trace reporting, paired statistical differences, and PostgreSQL persistence.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
import logging
from statistics import median
import time
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.evaluation.benchmark.dataset import BenchmarkCase, get_benchmark_dataset
from domain.evaluation.benchmark.metrics import (
    compute_citation_metrics,
    compute_cost_projections,
    compute_ground_truth_metrics,
    compute_latency_distribution,
    get_gpu_vram_usage,
)
from domain.evaluation.benchmark.models import (
    BenchmarkModelConfig,
    build_candidate_llm_provider,
)
from domain.evaluation.benchmark.pricing import calculate_cost, estimate_tokens, get_model_pricing
from domain.evaluation.deterministic import DeterministicValidator
from domain.evaluation.evaluator import InvestigationEvaluator
from domain.evaluation.schemas import EvaluationStatus, InvestigationEvaluationResult
from domain.report import InvestigationReport
from infrastructure.config import get_settings
from infrastructure.database.models import BenchmarkCaseResult, BenchmarkRun
from infrastructure.database.session import get_engine, session_scope
from infrastructure.llm.base import LLMProvider
from infrastructure.observability import flush_langfuse, get_langfuse_client

logger = logging.getLogger(__name__)


def _anonymize_report(report_dict: dict[str, Any], candidate_label: str) -> dict[str, Any]:
    """Strip provider/model names to prevent LLM brand bias in judge evaluations."""
    sanitized = dict(report_dict)
    sanitized["provenance"] = {
        "candidate": candidate_label,
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
    return sanitized


class SideBySideBenchmarkRunner:
    """Orchestrates side-by-side benchmark evaluations comparing two LLM models."""

    def __init__(
        self,
        judge_provider: LLMProvider | None = None,
        evaluator: InvestigationEvaluator | None = None,
    ) -> None:
        self._judge_provider = judge_provider
        self._evaluator = evaluator or InvestigationEvaluator(judge_provider=judge_provider)
        self._validator = DeterministicValidator()

    async def _execute_candidate(
        self,
        case: BenchmarkCase,
        config: BenchmarkModelConfig,
        provider: LLMProvider,
        candidate_label: str,
        trace_id: str | None = None,
    ) -> dict[str, Any]:
        """Execute one candidate model on a case with isolated failure protection."""
        from apps.investigator.agent import (
            _extract_json,
            build_system_prompt,
            build_user_prompt,
            run_agent,
        )

        state_dict = case.to_agent_state()
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(state_dict)

        t_start = time.perf_counter()
        raw_output: dict[str, Any] | None = None
        raw_text: str = ""
        error_msg: str | None = None
        status = "COMPLETED"
        response_obj: Any = None

        try:
            if provider.name == "fake" or config.model_id.lower() == "fake":
                outcome = await run_agent(state_dict, provider=provider)
                raw_output = outcome.report.model_dump(mode="json")
                raw_text = json.dumps(raw_output)
            else:
                response = await provider.complete(
                    system_prompt,
                    user_prompt,
                    temperature=config.temperature,
                    max_tokens=config.max_tokens,
                )
                response_obj = response
                raw_text = response.content
                raw_output = _extract_json(raw_text)

        except Exception as exc:
            logger.warning("Candidate %s failed on case %s: %s", candidate_label, case.case_id, exc)
            status = "FAILED"
            error_msg = str(exc)
            raw_output = {
                "investigation_id": case.investigation_id,
                "transaction_id": case.transaction_id,
                "risk_level": "UNKNOWN",
                "summary": f"Generation failed: {error_msg}",
                "findings": [],
                "recommended_action": "HUMAN_REVIEW",
                "confidence": 0.0,
            }

        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        # 2. Token counts & Cost estimation (Provider reported vs Estimated)
        prompt_tokens: int = 0
        completion_tokens: int = 0
        is_usage_estimated = False

        if response_obj is not None and getattr(response_obj, "usage", None):
            usage_dict = response_obj.usage
            prompt_tokens = usage_dict.get("prompt_tokens") or 0
            completion_tokens = usage_dict.get("completion_tokens") or 0
            total_tokens = usage_dict.get("total_tokens") or (prompt_tokens + completion_tokens)
        else:
            prompt_tokens = estimate_tokens(system_prompt) + estimate_tokens(user_prompt)
            completion_tokens = estimate_tokens(raw_text) if raw_text else 0
            total_tokens = prompt_tokens + completion_tokens
            is_usage_estimated = True

        cost_info = calculate_cost(config.model_id, prompt_tokens, completion_tokens)

        token_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "is_estimated": is_usage_estimated,
        }

        # 3. Deterministic Validation
        det_result = self._validator.validate(raw_output or {}, case.evidence, case.context)
        validation_dict = det_result.model_dump(mode="json")

        # 4. LLM-as-a-Judge Evaluation (anonymized candidate identity)
        anonymized_report = _anonymize_report(raw_output or {}, candidate_label)
        try:
            eval_res = await self._evaluator.evaluate(
                investigation_id=f"eval-{case.case_id}-{candidate_label}",
                report=anonymized_report,
                evidence=case.evidence,
                context=case.context,
                task_description=case.task_description,
                trace_id=trace_id,
                force_run=True,
            )
            evaluation_dict = eval_res.model_dump(mode="json")
        except Exception as judge_exc:
            logger.error("Judge evaluation failed for %s on %s: %s", candidate_label, case.case_id, judge_exc)
            evaluation_dict = {
                "status": "FAILED",
                "scores": {
                    "evidence_grounding": 1,
                    "reasoning_quality": 1,
                    "investigation_completeness": 1,
                    "report_quality": 1,
                    "overall_quality": 1,
                },
                "summary": f"Judge failure: {judge_exc}",
                "human_review_required": True,
                "unsupported_claims": [],
                "evidence_gaps": ["Judge evaluation failed."],
            }

        # 5. Advanced Evaluation Metrics: Citation, Ground Truth, Hardware VRAM, Tokens/sec
        citation_metrics = compute_citation_metrics(raw_output or {}, case.evidence)
        ground_truth_metrics = compute_ground_truth_metrics(
            raw_output or {}, getattr(case, "ground_truth", None)
        )

        tokens_per_sec = (
            round(completion_tokens / (latency_ms / 1000.0), 2)
            if (latency_ms > 0 and completion_tokens > 0)
            else 0.0
        )

        if config.provider == "ollama" or getattr(provider, "name", "") == "ollama":
            gpu_metrics = get_gpu_vram_usage()
        else:
            gpu_metrics = {
                "measured": False,
                "vram_used_mb": None,
                "vram_total_mb": None,
                "vram_free_mb": None,
                "gpu_name": None,
                "utilization_pct": None,
                "reason": "Local GPU metrics not applicable for Cloud API",
            }

        candidate_metrics = {
            "citation_metrics": citation_metrics,
            "ground_truth_metrics": ground_truth_metrics,
            "gpu_metrics": gpu_metrics,
            "tokens_per_second": tokens_per_sec,
            "is_usage_estimated": is_usage_estimated,
            "token_usage": token_usage,
        }

        return {
            "status": status,
            "error": error_msg,
            "output": raw_output,
            "latency_ms": latency_ms,
            "tokens": token_usage,
            "cost_usd": cost_info["total_cost_usd"],
            "validation": validation_dict,
            "evaluation": evaluation_dict,
            "metrics": candidate_metrics,
        }

    async def run(
        self,
        model_a_config: BenchmarkModelConfig,
        model_b_config: BenchmarkModelConfig,
        cases: list[BenchmarkCase] | None = None,
        run_id: str | None = None,
        judge_config: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Execute a full side-by-side benchmark comparison across candidate models."""
        run_uuid = run_id or f"BRUN-{datetime.now(UTC).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        target_cases = cases if cases is not None else get_benchmark_dataset()
        started_at = datetime.now(UTC)

        settings = get_settings()
        default_judge_model = getattr(settings, "omerta_judge_model", "openai/gpt-oss-120b")
        effective_judge_config = judge_config or {
            "model_id": default_judge_model,
            "provider": getattr(settings, "omerta_judge_provider", "groq"),
        }

        # Initialize candidate providers
        provider_a = build_candidate_llm_provider(model_a_config)
        provider_b = build_candidate_llm_provider(model_b_config)

        # Initialize Langfuse client
        lf = get_langfuse_client()

        # Initial database record if persisting
        engine = get_engine()
        if persist:
            async with session_scope(engine) as session:
                db_run = BenchmarkRun(
                    run_id=run_uuid,
                    dataset_version="1.0",
                    model_a_config=model_a_config.model_dump(mode="json"),
                    model_b_config=model_b_config.model_dump(mode="json"),
                    judge_config=effective_judge_config,
                    status="RUNNING",
                    total_cases=len(target_cases),
                    completed_cases=0,
                    started_at=started_at,
                    pricing_metadata={
                        "model_a": get_model_pricing(model_a_config.model_id),
                        "model_b": get_model_pricing(model_b_config.model_id),
                    },
                )
                session.add(db_run)

        case_results: list[dict[str, Any]] = []

        for case in target_cases:
            case_trace_id = f"trace-{run_uuid}-{case.case_id}".lower()
            langfuse_host = (getattr(settings, "langfuse_host", "http://localhost:3000") or "http://localhost:3000").rstrip("/")
            trace_url = f"{langfuse_host}/trace/{case_trace_id}"

            # Create Langfuse trace if enabled
            lf_trace = None
            if lf:
                try:
                    lf_trace = lf.trace(
                        id=case_trace_id,
                        name=f"benchmark-{case.case_id}",
                        metadata={
                            "run_id": run_uuid,
                            "case_id": case.case_id,
                            "scenario_type": case.scenario_type,
                            "model_a": model_a_config.model_id,
                            "model_b": model_b_config.model_id,
                        },
                        tags=["benchmark", "side-by-side", f"run-{run_uuid}", case.scenario_type.lower()],
                    )
                except Exception as trace_exc:
                    logger.debug("Failed creating Langfuse trace: %s", trace_exc)

            # Execute Candidate A
            res_a = await self._execute_candidate(
                case=case,
                config=model_a_config,
                provider=provider_a,
                candidate_label="candidate_a",
                trace_id=case_trace_id,
            )

            # Execute Candidate B
            res_b = await self._execute_candidate(
                case=case,
                config=model_b_config,
                provider=provider_b,
                candidate_label="candidate_b",
                trace_id=case_trace_id,
            )

            # Record Langfuse generations & scores
            if lf and lf_trace:
                try:
                    # Model A generation
                    lf_trace.generation(
                        name=f"candidate_a_{model_a_config.model_id}",
                        model=model_a_config.model_id,
                        input={"case_id": case.case_id, "task": case.task_description},
                        output=res_a["output"],
                        usage=res_a["tokens"],
                    )
                    # Model B generation
                    lf_trace.generation(
                        name=f"candidate_b_{model_b_config.model_b if hasattr(model_b_config, 'model_b') else model_b_config.model_id}",
                        model=model_b_config.model_id,
                        input={"case_id": case.case_id, "task": case.task_description},
                        output=res_b["output"],
                        usage=res_b["tokens"],
                    )
                    # Model A scores
                    scores_a = (res_a["evaluation"] or {}).get("scores", {})
                    if scores_a.get("overall_quality") is not None:
                        lf.score(trace_id=case_trace_id, name="model_a_overall_quality", value=float(scores_a["overall_quality"]), data_type="NUMERIC")
                    if scores_a.get("evidence_grounding") is not None:
                        lf.score(trace_id=case_trace_id, name="model_a_evidence_grounding", value=float(scores_a["evidence_grounding"]), data_type="NUMERIC")
                    lf.score(trace_id=case_trace_id, name="model_a_deterministic_passed", value=1.0 if res_a["validation"].get("passed") else 0.0, data_type="NUMERIC")

                    # Model B scores
                    scores_b = (res_b["evaluation"] or {}).get("scores", {})
                    if scores_b.get("overall_quality") is not None:
                        lf.score(trace_id=case_trace_id, name="model_b_overall_quality", value=float(scores_b["overall_quality"]), data_type="NUMERIC")
                    if scores_b.get("evidence_grounding") is not None:
                        lf.score(trace_id=case_trace_id, name="model_b_evidence_grounding", value=float(scores_b["evidence_grounding"]), data_type="NUMERIC")
                    lf.score(trace_id=case_trace_id, name="model_b_deterministic_passed", value=1.0 if res_b["validation"].get("passed") else 0.0, data_type="NUMERIC")

                    flush_langfuse(lf)
                except Exception as lf_err:
                    logger.debug("Error logging to Langfuse: %s", lf_err)

            # Differences summary
            scores_a = (res_a["evaluation"] or {}).get("scores", {})
            scores_b = (res_b["evaluation"] or {}).get("scores", {})
            overall_a = scores_a.get("overall_quality")
            overall_b = scores_b.get("overall_quality")

            winner = "TIE"
            if res_a["status"] == "COMPLETED" and res_b["status"] == "FAILED":
                winner = "MODEL_A"
            elif res_b["status"] == "COMPLETED" and res_a["status"] == "FAILED":
                winner = "MODEL_B"
            elif overall_a is not None and overall_b is not None:
                if overall_a > overall_b:
                    winner = "MODEL_A"
                elif overall_b > overall_a:
                    winner = "MODEL_B"

            diff_summary = {
                "winner": winner,
                "score_deltas": {
                    "overall_quality": (overall_a - overall_b) if (overall_a is not None and overall_b is not None) else 0,
                    "evidence_grounding": (scores_a.get("evidence_grounding", 0) - scores_b.get("evidence_grounding", 0)),
                    "reasoning_quality": (scores_a.get("reasoning_quality", 0) - scores_b.get("reasoning_quality", 0)),
                    "investigation_completeness": (scores_a.get("investigation_completeness", 0) - scores_b.get("investigation_completeness", 0)),
                    "report_quality": (scores_a.get("report_quality", 0) - scores_b.get("report_quality", 0)),
                },
                "deterministic_agreement": res_a["validation"].get("passed") == res_b["validation"].get("passed"),
                "human_review_agreement": res_a["evaluation"].get("human_review_required") == res_b["evaluation"].get("human_review_required"),
                "latency_delta_ms": round(res_a["latency_ms"] - res_b["latency_ms"], 2),
                "cost_delta_usd": round(res_a["cost_usd"] - res_b["cost_usd"], 6),
                "model_a_summary": (res_a["output"] or {}).get("summary", ""),
                "model_b_summary": (res_b["output"] or {}).get("summary", ""),
            }

            case_record = {
                "run_id": run_uuid,
                "case_id": case.case_id,
                "scenario_type": case.scenario_type,
                "model_a_output": res_a["output"],
                "model_a_validation": res_a["validation"],
                "model_a_evaluation": res_a["evaluation"],
                "model_a_latency_ms": res_a["latency_ms"],
                "model_a_tokens": res_a["tokens"],
                "model_a_cost_usd": res_a["cost_usd"],
                "model_a_trace_id": case_trace_id,
                "model_a_trace_url": trace_url,
                "model_a_status": res_a["status"],
                "model_a_error": res_a["error"],
                "model_a_metrics": res_a.get("metrics"),
                "model_b_output": res_b["output"],
                "model_b_validation": res_b["validation"],
                "model_b_evaluation": res_b["evaluation"],
                "model_b_latency_ms": res_b["latency_ms"],
                "model_b_tokens": res_b["tokens"],
                "model_b_cost_usd": res_b["cost_usd"],
                "model_b_trace_id": case_trace_id,
                "model_b_trace_url": trace_url,
                "model_b_status": res_b["status"],
                "model_b_error": res_b["error"],
                "model_b_metrics": res_b.get("metrics"),
                "differences_summary": diff_summary,
            }
            case_results.append(case_record)

            if persist:
                async with session_scope(engine) as session:
                    db_case = BenchmarkCaseResult(**case_record)
                    session.add(db_case)

        # Compute aggregate metrics
        aggregate_metrics = self._compute_aggregates(
            model_a_config=model_a_config,
            model_b_config=model_b_config,
            case_results=case_results,
        )

        completed_at = datetime.now(UTC)

        # Update BenchmarkRun in DB
        if persist:
            async with session_scope(engine) as session:
                query = select(BenchmarkRun).where(BenchmarkRun.run_id == run_uuid)
                result = await session.execute(query)
                run_row = result.scalar_one_or_none()
                if run_row:
                    run_row.status = "COMPLETED"
                    run_row.completed_cases = len(case_results)
                    run_row.completed_at = completed_at
                    run_row.aggregate_metrics = aggregate_metrics

        return {
            "run_id": run_uuid,
            "status": "COMPLETED",
            "dataset_version": "1.0",
            "model_a_config": model_a_config.model_dump(mode="json"),
            "model_b_config": model_b_config.model_dump(mode="json"),
            "judge_config": effective_judge_config,
            "started_at": started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "total_cases": len(target_cases),
            "completed_cases": len(case_results),
            "aggregate_metrics": aggregate_metrics,
            "cases": case_results,
        }

    def _compute_aggregates(
        self,
        model_a_config: BenchmarkModelConfig,
        model_b_config: BenchmarkModelConfig,
        case_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compute aggregate metrics, mean/median scores, and head-to-head comparison stats."""
        total_cases = len(case_results)
        if total_cases == 0:
            return {}

        def _extract_metric_lists(model_prefix: str):
            scores_map: dict[str, list[float]] = {
                "overall_quality": [],
                "evidence_grounding": [],
                "reasoning_quality": [],
                "investigation_completeness": [],
                "report_quality": [],
            }
            latencies: list[float] = []
            prompt_toks: list[int] = []
            comp_toks: list[int] = []
            tot_toks: list[int] = []
            costs: list[float] = []
            citation_accuracies: list[float] = []
            evidence_coverages: list[float] = []
            gt_f1s: list[float] = []
            gt_precisions: list[float] = []
            gt_recalls: list[float] = []
            tokens_per_sec_list: list[float] = []
            vram_used_list: list[float] = []
            schema_passes = 0
            det_passes = 0
            human_reviews = 0

            for cr in case_results:
                eval_dict = cr.get(f"{model_prefix}_evaluation") or {}
                val_dict = cr.get(f"{model_prefix}_validation") or {}
                tok_dict = cr.get(f"{model_prefix}_tokens") or {}
                metrics_dict = cr.get(f"{model_prefix}_metrics") or {}
                scores = eval_dict.get("scores") or {}

                for dim in scores_map:
                    val = scores.get(dim)
                    if val is not None:
                        scores_map[dim].append(float(val))

                lat = cr.get(f"{model_prefix}_latency_ms")
                if lat is not None:
                    latencies.append(float(lat))

                prompt_toks.append(tok_dict.get("prompt_tokens", 0))
                comp_toks.append(tok_dict.get("completion_tokens", 0))
                tot_toks.append(tok_dict.get("total_tokens", 0))

                cost = cr.get(f"{model_prefix}_cost_usd")
                if cost is not None:
                    costs.append(float(cost))

                cit = metrics_dict.get("citation_metrics") or {}
                if "citation_accuracy_pct" in cit:
                    citation_accuracies.append(float(cit["citation_accuracy_pct"]))
                if "evidence_coverage_pct" in cit:
                    evidence_coverages.append(float(cit["evidence_coverage_pct"]))

                gt = metrics_dict.get("ground_truth_metrics") or {}
                if gt.get("has_ground_truth"):
                    if gt.get("f1_score") is not None:
                        gt_f1s.append(float(gt["f1_score"]))
                    if gt.get("precision") is not None:
                        gt_precisions.append(float(gt["precision"]))
                    if gt.get("recall") is not None:
                        gt_recalls.append(float(gt["recall"]))

                tps = metrics_dict.get("tokens_per_second")
                if tps is not None and tps > 0:
                    tokens_per_sec_list.append(float(tps))

                gpu = metrics_dict.get("gpu_metrics") or {}
                if gpu.get("measured") and gpu.get("vram_used_mb") is not None:
                    vram_used_list.append(float(gpu["vram_used_mb"]))

                if val_dict.get("schema_valid"):
                    schema_passes += 1
                if val_dict.get("passed"):
                    det_passes += 1
                if eval_dict.get("human_review_required"):
                    human_reviews += 1

            avg_scores = {
                dim: round(sum(vals) / max(1, len(vals)), 2) for dim, vals in scores_map.items()
            }
            med_scores = {
                dim: round(median(vals), 2) if vals else 0.0 for dim, vals in scores_map.items()
            }

            latency_dist = compute_latency_distribution(latencies)
            total_cost_usd = round(sum(costs), 6)
            cost_projections = compute_cost_projections(total_cost_usd, total_cases)

            mean_citation_acc = (
                round(sum(citation_accuracies) / max(1, len(citation_accuracies)), 1)
                if citation_accuracies
                else 0.0
            )
            mean_evidence_cov = (
                round(sum(evidence_coverages) / max(1, len(evidence_coverages)), 1)
                if evidence_coverages
                else 0.0
            )
            mean_tps = (
                round(sum(tokens_per_sec_list) / max(1, len(tokens_per_sec_list)), 1)
                if tokens_per_sec_list
                else 0.0
            )
            avg_vram = (
                round(sum(vram_used_list) / max(1, len(vram_used_list)), 1)
                if vram_used_list
                else None
            )
            peak_vram = (
                round(max(vram_used_list), 1)
                if vram_used_list
                else None
            )
            mean_gt_f1 = (
                round(sum(gt_f1s) / max(1, len(gt_f1s)), 3)
                if gt_f1s
                else None
            )

            return {
                "average_scores": avg_scores,
                "median_scores": med_scores,
                "schema_pass_rate_pct": round((schema_passes / total_cases) * 100.0, 1),
                "deterministic_pass_rate_pct": round((det_passes / total_cases) * 100.0, 1),
                "human_review_rate_pct": round((human_reviews / total_cases) * 100.0, 1),
                "mean_latency_ms": latency_dist["mean_latency_ms"],
                "median_latency_ms": latency_dist["median_latency_ms"],
                "p95_latency_ms": latency_dist["p95_latency_ms"],
                "min_latency_ms": latency_dist["min_latency_ms"],
                "max_latency_ms": latency_dist["max_latency_ms"],
                "total_latency_ms": round(sum(latencies), 2),
                "tokens_per_second": mean_tps,
                "citation_accuracy_pct": mean_citation_acc,
                "evidence_coverage_pct": mean_evidence_cov,
                "ground_truth_f1": mean_gt_f1,
                "gpu_vram_used_mb": avg_vram,
                "peak_gpu_vram_used_mb": peak_vram,
                "cost_per_case_usd": cost_projections["cost_per_case_usd"],
                "projected_cost_per_1000_cases_usd": cost_projections["projected_cost_per_1000_cases_usd"],
                "total_tokens": {
                    "prompt_tokens": sum(prompt_toks),
                    "completion_tokens": sum(comp_toks),
                    "total_tokens": sum(tot_toks),
                },
                "total_cost_usd": total_cost_usd,
            }

        agg_a = _extract_metric_lists("model_a")
        agg_b = _extract_metric_lists("model_b")

        wins_a = sum(1 for cr in case_results if (cr.get("differences_summary") or {}).get("winner") == "MODEL_A")
        wins_b = sum(1 for cr in case_results if (cr.get("differences_summary") or {}).get("winner") == "MODEL_B")
        ties = sum(1 for cr in case_results if (cr.get("differences_summary") or {}).get("winner") == "TIE")

        cost_diff = round(agg_a["total_cost_usd"] - agg_b["total_cost_usd"], 6)
        lat_diff = round(agg_a["total_latency_ms"] - agg_b["total_latency_ms"], 2)
        p95_diff = round(agg_a["p95_latency_ms"] - agg_b["p95_latency_ms"], 2)

        return {
            "total_cases": total_cases,
            "completed_cases": total_cases,
            "model_a": {
                "model_id": model_a_config.model_id,
                "display_name": model_a_config.get_display_name(),
                "provider": model_a_config.provider,
                **agg_a,
            },
            "model_b": {
                "model_b": model_b_config.model_id,
                "model_id": model_b_config.model_id,
                "display_name": model_b_config.get_display_name(),
                "provider": model_b_config.provider,
                **agg_b,
            },
            "comparison": {
                "model_a_wins": wins_a,
                "model_b_wins": wins_b,
                "ties": ties,
                "overall_score_delta_mean": round(
                    agg_a["average_scores"]["overall_quality"] - agg_b["average_scores"]["overall_quality"],
                    2,
                ),
                "cost_difference_usd": cost_diff,
                "cost_savings_pct": round(
                    ((agg_a["total_cost_usd"] - agg_b["total_cost_usd"]) / max(0.000001, agg_a["total_cost_usd"])) * 100.0,
                    1,
                ) if agg_a["total_cost_usd"] > 0 else 0.0,
                "latency_difference_ms": lat_diff,
                "p95_latency_difference_ms": p95_diff,
                "speedup_factor": round(agg_a["total_latency_ms"] / max(1.0, agg_b["total_latency_ms"]), 2)
                if agg_b["total_latency_ms"] > 0
                else 1.0,
            },
        }
