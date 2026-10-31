"""API endpoints for LLM-as-a-Judge Evaluation in Omerta.ai."""

from datetime import UTC, datetime
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.evaluation.benchmark import BenchmarkRunReport, BenchmarkRunner, get_benchmark_scenarios
from domain.evaluation.evaluator import InvestigationEvaluator
from domain.evaluation.schemas import InvestigationEvaluationResult
from infrastructure.database.models import InvestigationCase, Transaction
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["LLM-as-a-Judge Evaluation"])


class EvaluateReportRequest(BaseModel):
    """Payload for on-demand evaluation of an investigation report."""

    investigation_id: str
    report: dict[str, Any]
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    task_description: str | None = None
    trace_id: str | None = None
    expected_labels: dict[str, Any] | None = None
    force_run: bool = Field(
        default=True,
        description="Whether to execute evaluation even if OMERTA_EVALUATION_ENABLED is false in config.",
    )


@router.post(
    "/evaluate",
    response_model=InvestigationEvaluationResult,
    summary="Evaluate an Investigation Report (LLM-as-a-Judge)",
    description="Executes deterministic validation and LLM-as-a-Judge evaluation, optionally recording scores to Langfuse trace.",
)
async def evaluate_investigation_endpoint(
    body: EvaluateReportRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InvestigationEvaluationResult:
    """Execute evaluation against supplied report and evidence."""
    evaluator = InvestigationEvaluator()
    result = await evaluator.evaluate(
        investigation_id=body.investigation_id,
        report=body.report,
        evidence=body.evidence,
        context=body.context,
        task_description=body.task_description,
        trace_id=body.trace_id,
        expected_labels=body.expected_labels,
        force_run=body.force_run,
    )
    return result


@router.get(
    "/case/{case_id_or_external_id}",
    response_model=InvestigationEvaluationResult,
    summary="Evaluate Persisted Investigation Case from Database",
    description="Loads a persisted case and its evidence from the database and runs evaluation.",
)
async def evaluate_persisted_case_endpoint(
    case_id_or_external_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InvestigationEvaluationResult:
    """Evaluate a persisted investigation case by ID or external identifier."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        stmt = (
            select(InvestigationCase)
            .where(
                or_(
                    InvestigationCase.external_id == case_id_or_external_id,
                    InvestigationCase.id == int(case_id_or_external_id)
                    if case_id_or_external_id.isdigit()
                    else False,
                )
            )
            .order_by(desc(InvestigationCase.id))
        )
        case = await session.scalar(stmt)
        if not case or not case.report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Investigation case '{case_id_or_external_id}' with report not found.",
            )

        report = case.report
        evidence_items: list[dict[str, Any]] = []
        if case.evidence:
            for ev in case.evidence:
                evidence_items.append(
                    {
                        "evidence_id": ev.evidence_id,
                        "category": ev.evidence_type,
                        "source": ev.source,
                        "reference": ev.source_reference,
                        "description": ev.description,
                        "data": ev.data or {},
                    }
                )

        evaluator = InvestigationEvaluator()
        result = await evaluator.evaluate(
            investigation_id=case.external_id,
            report=report,
            evidence=evidence_items,
            context={"case_id": case.id, "title": case.title},
            force_run=True,
        )
        return result


@router.get(
    "/benchmark/scenarios",
    summary="List Synthetic AML Benchmark Scenarios",
    description="Returns metadata for the 8 canonical benchmark evaluation scenarios.",
)
async def list_benchmark_scenarios_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List benchmark scenarios."""
    scenarios = get_benchmark_scenarios()
    return [
        {
            "scenario_id": s.scenario_id,
            "name": s.name,
            "description": s.description,
            "has_deliberate_error": s.ground_truth.get("has_deliberate_error", False),
            "error_type": s.ground_truth.get("error_type"),
        }
        for s in scenarios
    ]


@router.post(
    "/benchmark/run",
    response_model=BenchmarkRunReport,
    summary="Execute AML Benchmark Suite",
    description="Executes the 8 canonical benchmark scenarios and returns aggregate metrics and error detection accuracy.",
)
async def run_benchmark_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> BenchmarkRunReport:
    """Run full benchmark suite."""
    runner = BenchmarkRunner()
    return await runner.run()

