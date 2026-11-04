"""API endpoints for LLM Model Side-by-Side Benchmarking in Omerta.ai.

Provides REST interfaces for:
- Querying candidate model catalog and live credential status
- Fetching canonical benchmark test cases
- Launching side-by-side model evaluations
- Querying persisted runs, aggregate KPIs, and deep case diffs
"""

from __future__ import annotations

import csv
import io
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.evaluation.benchmark.dataset import BenchmarkCase, get_benchmark_dataset
from domain.evaluation.benchmark.models import (
    BenchmarkModelConfig,
    ModelAvailabilityInfo,
    get_available_model_catalog,
)
from domain.evaluation.benchmark.side_by_side import SideBySideBenchmarkRunner
from infrastructure.database.models import BenchmarkCaseResult, BenchmarkRun
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["Model Benchmarking"])


class CreateBenchmarkRunRequest(BaseModel):
    """Payload to initiate a reproducible side-by-side benchmark run."""

    model_a: BenchmarkModelConfig
    model_b: BenchmarkModelConfig
    case_ids: list[str] | None = Field(
        default=None,
        description="Optional list of case IDs to run. Defaults to all 7 canonical cases.",
    )
    dataset_version: str = Field(default="1.0", description="Version of the benchmark dataset.")


class BenchmarkRunSummaryResponse(BaseModel):
    """Concise representation of a benchmark run for list views."""

    run_id: str
    dataset_version: str
    status: str
    total_cases: int
    completed_cases: int
    started_at: str
    completed_at: str | None = None
    model_a_id: str
    model_b_id: str
    aggregate_metrics: dict[str, Any] | None = None


@router.get(
    "/models",
    response_model=list[ModelAvailabilityInfo],
    summary="Get Available Candidate Models Catalog",
    description="Returns list of candidate models with active credential availability and pricing rates.",
)
async def list_models_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[ModelAvailabilityInfo]:
    """Return model catalog with credential verification."""
    return get_available_model_catalog()


@router.get(
    "/scenarios",
    response_model=list[BenchmarkCase],
    summary="Get Benchmark Dataset Cases",
    description="Returns the canonical versioned benchmark cases with evidence and ground-truth specs.",
)
async def list_scenarios_endpoint(
    version: str = Query(default="1.0", description="Dataset version"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[BenchmarkCase]:
    """Return canonical benchmark dataset cases."""
    return get_benchmark_dataset(version=version)


@router.post(
    "/runs",
    summary="Execute Side-by-Side Benchmark Run",
    description="Runs Candidate Model A vs Candidate Model B across benchmark cases, runs judge and deterministic validation, logs to Langfuse, and persists to PostgreSQL.",
)
async def execute_benchmark_run_endpoint(
    body: CreateBenchmarkRunRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute side-by-side benchmark evaluation."""
    all_cases = get_benchmark_dataset(version=body.dataset_version)
    if body.case_ids:
        selected_ids = set(body.case_ids)
        target_cases = [c for c in all_cases if c.case_id in selected_ids]
        if not target_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"None of the requested case IDs {body.case_ids} exist in dataset v{body.dataset_version}.",
            )
    else:
        target_cases = all_cases

    runner = SideBySideBenchmarkRunner()
    try:
        run_result = await runner.run(
            model_a_config=body.model_a,
            model_b_config=body.model_b,
            cases=target_cases,
            persist=True,
        )
        return run_result
    except Exception as exc:
        logger.error("Side-by-side benchmark execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark run failed: {str(exc)}",
        )


@router.get(
    "/runs",
    response_model=list[BenchmarkRunSummaryResponse],
    summary="List Benchmark Runs History",
    description="Returns persisted benchmark runs ordered by started_at descending.",
)
async def list_benchmark_runs_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[BenchmarkRunSummaryResponse]:
    """List historical benchmark runs."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        query = (
            select(BenchmarkRun)
            .order_by(desc(BenchmarkRun.started_at))
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(query)
        runs = result.scalars().all()

        summaries = []
        for r in runs:
            m_a = r.model_a_config or {}
            m_b = r.model_b_config or {}
            summaries.append(
                BenchmarkRunSummaryResponse(
                    run_id=r.run_id,
                    dataset_version=r.dataset_version,
                    status=r.status,
                    total_cases=r.total_cases,
                    completed_cases=r.completed_cases,
                    started_at=r.started_at.isoformat() if r.started_at else "",
                    completed_at=r.completed_at.isoformat() if r.completed_at else None,
                    model_a_id=m_a.get("model_id", "Unknown"),
                    model_b_id=m_b.get("model_id", "Unknown"),
                    aggregate_metrics=r.aggregate_metrics,
                )
            )
        return summaries


@router.get(
    "/runs/{run_id}",
    summary="Get Benchmark Run Details",
    description="Returns aggregate metrics, model configs, pricing, and all case results for a run.",
)
async def get_benchmark_run_endpoint(
    run_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve full benchmark run record with associated case results."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        query = (
            select(BenchmarkRun)
            .options(selectinload(BenchmarkRun.cases))
            .where(BenchmarkRun.run_id == run_id)
        )
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Benchmark run '{run_id}' not found.",
            )

        cases_data = []
        for c in run.cases:
            cases_data.append({
                "id": c.id,
                "case_id": c.case_id,
                "scenario_type": c.scenario_type,
                "model_a_output": c.model_a_output,
                "model_a_validation": c.model_a_validation,
                "model_a_evaluation": c.model_a_evaluation,
                "model_a_latency_ms": float(c.model_a_latency_ms) if c.model_a_latency_ms is not None else None,
                "model_a_tokens": c.model_a_tokens,
                "model_a_cost_usd": float(c.model_a_cost_usd) if c.model_a_cost_usd is not None else None,
                "model_a_trace_id": c.model_a_trace_id,
                "model_a_trace_url": c.model_a_trace_url,
                "model_a_status": c.model_a_status,
                "model_a_error": c.model_a_error,
                "model_a_metrics": c.model_a_metrics,
                "model_b_output": c.model_b_output,
                "model_b_validation": c.model_b_validation,
                "model_b_evaluation": c.model_b_evaluation,
                "model_b_latency_ms": float(c.model_b_latency_ms) if c.model_b_latency_ms is not None else None,
                "model_b_tokens": c.model_b_tokens,
                "model_b_cost_usd": float(c.model_b_cost_usd) if c.model_b_cost_usd is not None else None,
                "model_b_trace_id": c.model_b_trace_id,
                "model_b_trace_url": c.model_b_trace_url,
                "model_b_status": c.model_b_status,
                "model_b_error": c.model_b_error,
                "model_b_metrics": c.model_b_metrics,
                "differences_summary": c.differences_summary,
            })

        return {
            "run_id": run.run_id,
            "dataset_version": run.dataset_version,
            "status": run.status,
            "model_a_config": run.model_a_config,
            "model_b_config": run.model_b_config,
            "judge_config": run.judge_config,
            "total_cases": run.total_cases,
            "completed_cases": run.completed_cases,
            "started_at": run.started_at.isoformat() if run.started_at else "",
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "aggregate_metrics": run.aggregate_metrics,
            "pricing_metadata": run.pricing_metadata,
            "error_message": run.error_message,
            "cases": cases_data,
        }


@router.get(
    "/runs/{run_id}/cases/{case_id}",
    summary="Get Specific Case Comparison Details",
    description="Returns detailed side-by-side comparison for a single case in a benchmark run.",
)
async def get_case_comparison_endpoint(
    run_id: str,
    case_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve deep side-by-side comparison for one case."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        query = (
            select(BenchmarkCaseResult)
            .where(
                BenchmarkCaseResult.run_id == run_id,
                BenchmarkCaseResult.case_id == case_id,
            )
        )
        result = await session.execute(query)
        case_row = result.scalar_one_or_none()

        if not case_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Case result for run '{run_id}' and case '{case_id}' not found.",
            )

        return {
            "id": case_row.id,
            "run_id": case_row.run_id,
            "case_id": case_row.case_id,
            "scenario_type": case_row.scenario_type,
            "model_a_output": case_row.model_a_output,
            "model_a_validation": case_row.model_a_validation,
            "model_a_evaluation": case_row.model_a_evaluation,
            "model_a_latency_ms": float(case_row.model_a_latency_ms) if case_row.model_a_latency_ms is not None else None,
            "model_a_tokens": case_row.model_a_tokens,
            "model_a_cost_usd": float(case_row.model_a_cost_usd) if case_row.model_a_cost_usd is not None else None,
            "model_a_trace_id": case_row.model_a_trace_id,
            "model_a_trace_url": case_row.model_a_trace_url,
            "model_a_status": case_row.model_a_status,
            "model_a_error": case_row.model_a_error,
            "model_a_metrics": case_row.model_a_metrics,
            "model_b_output": case_row.model_b_output,
            "model_b_validation": case_row.model_b_validation,
            "model_b_evaluation": case_row.model_b_evaluation,
            "model_b_latency_ms": float(case_row.model_b_latency_ms) if case_row.model_b_latency_ms is not None else None,
            "model_b_tokens": case_row.model_b_tokens,
            "model_b_cost_usd": float(case_row.model_b_cost_usd) if case_row.model_b_cost_usd is not None else None,
            "model_b_trace_id": case_row.model_b_trace_id,
            "model_b_trace_url": case_row.model_b_trace_url,
            "model_b_status": case_row.model_b_status,
            "model_b_error": case_row.model_b_error,
            "model_b_metrics": case_row.model_b_metrics,
            "differences_summary": case_row.differences_summary,
        }


@router.get(
    "/runs/{run_id}/export",
    summary="Export Benchmark Run Data",
    description="Export full benchmark run results in JSON or CSV format for offline reporting and auditing.",
)
async def export_benchmark_run_endpoint(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Export benchmark run results to JSON or CSV."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        query = (
            select(BenchmarkRun)
            .options(selectinload(BenchmarkRun.cases))
            .where(BenchmarkRun.run_id == run_id)
        )
        result = await session.execute(query)
        run = result.scalar_one_or_none()

        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Benchmark run '{run_id}' not found.",
            )

        run_dict = {
            "run_id": run.run_id,
            "dataset_version": run.dataset_version,
            "status": run.status,
            "model_a_config": run.model_a_config,
            "model_b_config": run.model_b_config,
            "judge_config": run.judge_config,
            "total_cases": run.total_cases,
            "completed_cases": run.completed_cases,
            "started_at": run.started_at.isoformat() if run.started_at else "",
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "aggregate_metrics": run.aggregate_metrics,
            "pricing_metadata": run.pricing_metadata,
            "cases": [
                {
                    "case_id": c.case_id,
                    "scenario_type": c.scenario_type,
                    "model_a_status": c.model_a_status,
                    "model_a_latency_ms": float(c.model_a_latency_ms) if c.model_a_latency_ms is not None else None,
                    "model_a_tokens": c.model_a_tokens,
                    "model_a_cost_usd": float(c.model_a_cost_usd) if c.model_a_cost_usd is not None else None,
                    "model_a_validation": c.model_a_validation,
                    "model_a_evaluation": c.model_a_evaluation,
                    "model_a_metrics": c.model_a_metrics,
                    "model_b_status": c.model_b_status,
                    "model_b_latency_ms": float(c.model_b_latency_ms) if c.model_b_latency_ms is not None else None,
                    "model_b_tokens": c.model_b_tokens,
                    "model_b_cost_usd": float(c.model_b_cost_usd) if c.model_b_cost_usd is not None else None,
                    "model_b_validation": c.model_b_validation,
                    "model_b_evaluation": c.model_b_evaluation,
                    "model_b_metrics": c.model_b_metrics,
                    "differences_summary": c.differences_summary,
                }
                for c in run.cases
            ],
        }

        if format == "json":
            json_str = json.dumps(run_dict, indent=2, default=str)
            return Response(
                content=json_str,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="benchmark-{run_id}.json"',
                },
            )

        # CSV format
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "case_id",
            "scenario_type",
            "winner",
            "model_a_id",
            "model_a_status",
            "model_a_overall_quality",
            "model_a_evidence_grounding",
            "model_a_deterministic_passed",
            "model_a_citation_accuracy_pct",
            "model_a_evidence_coverage_pct",
            "model_a_latency_ms",
            "model_a_total_tokens",
            "model_a_cost_usd",
            "model_b_id",
            "model_b_status",
            "model_b_overall_quality",
            "model_b_evidence_grounding",
            "model_b_deterministic_passed",
            "model_b_citation_accuracy_pct",
            "model_b_evidence_coverage_pct",
            "model_b_latency_ms",
            "model_b_total_tokens",
            "model_b_cost_usd",
        ])

        m_a_id = (run.model_a_config or {}).get("model_id", "Model A")
        m_b_id = (run.model_b_config or {}).get("model_id", "Model B")

        for c in run.cases:
            diff = c.differences_summary or {}
            val_a = c.model_a_validation or {}
            eval_a = (c.model_a_evaluation or {}).get("scores", {})
            met_a = c.model_a_metrics or {}
            cit_a = met_a.get("citation_metrics", {})
            tok_a = c.model_a_tokens or {}

            val_b = c.model_b_validation or {}
            eval_b = (c.model_b_evaluation or {}).get("scores", {})
            met_b = c.model_b_metrics or {}
            cit_b = met_b.get("citation_metrics", {})
            tok_b = c.model_b_tokens or {}

            writer.writerow([
                c.case_id,
                c.scenario_type,
                diff.get("winner", "TIE"),
                m_a_id,
                c.model_a_status,
                eval_a.get("overall_quality", ""),
                eval_a.get("evidence_grounding", ""),
                "PASS" if val_a.get("passed") else "FAIL",
                cit_a.get("citation_accuracy_pct", ""),
                cit_a.get("evidence_coverage_pct", ""),
                float(c.model_a_latency_ms) if c.model_a_latency_ms is not None else "",
                tok_a.get("total_tokens", ""),
                float(c.model_a_cost_usd) if c.model_a_cost_usd is not None else "",
                m_b_id,
                c.model_b_status,
                eval_b.get("overall_quality", ""),
                eval_b.get("evidence_grounding", ""),
                "PASS" if val_b.get("passed") else "FAIL",
                cit_b.get("citation_accuracy_pct", ""),
                cit_b.get("evidence_coverage_pct", ""),
                float(c.model_b_latency_ms) if c.model_b_latency_ms is not None else "",
                tok_b.get("total_tokens", ""),
                float(c.model_b_cost_usd) if c.model_b_cost_usd is not None else "",
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="benchmark-{run_id}.csv"',
            },
        )

