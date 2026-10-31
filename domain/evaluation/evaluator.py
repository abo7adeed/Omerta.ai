"""Production-grade LLM-as-a-Judge and Deterministic Evaluator for Omerta.ai."""

import json
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, ValidationError

from domain.evaluation.deterministic import DeterministicValidator
from domain.evaluation.judge_provider import get_judge_llm_provider
from domain.evaluation.langfuse_reporter import record_evaluation_to_langfuse
from domain.evaluation.prompts import build_judge_system_prompt, build_judge_user_prompt
from domain.evaluation.schemas import (
    EvaluationScores,
    EvaluationStatus,
    InvestigationEvaluationResult,
    JudgeRawOutput,
)
from infrastructure.config import get_settings
from infrastructure.llm.base import LLMProvider

logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Any:
    """Recursively convert Pydantic models or dataclasses into plain JSON-serializable dicts."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


def _clean_json_markdown(text: str) -> str:
    """Extract raw JSON from possible markdown code block fences."""
    cleaned = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()
    return cleaned


class InvestigationEvaluator:
    """Evaluates the quality, factual grounding, and completeness of an investigation."""

    def __init__(self, judge_provider: LLMProvider | None = None) -> None:
        self._judge_provider = judge_provider
        self._validator = DeterministicValidator()

    async def evaluate(
        self,
        investigation_id: str,
        report: dict[str, Any] | BaseModel,
        evidence: list[dict[str, Any]] | list[Any],
        context: dict[str, Any] | None = None,
        task_description: str | None = None,
        trace_id: str | None = None,
        expected_labels: dict[str, Any] | None = None,
        force_run: bool = False,
    ) -> InvestigationEvaluationResult:
        """Execute deterministic verification and LLM-as-a-Judge evaluation."""
        settings = get_settings()
        report_dict = _to_dict(report)
        evidence_list = _to_dict(evidence)
        context_dict = _to_dict(context or {})

        # Step 1: Run Deterministic Validation
        det_result = self._validator.validate(report_dict, evidence_list, context_dict)

        # Step 2: Check if LLM evaluation is enabled
        is_enabled = settings.omerta_evaluation_enabled or force_run
        if not is_enabled:
            logger.info("Evaluation disabled (OMERTA_EVALUATION_ENABLED=false); returning skipped status.")
            return InvestigationEvaluationResult(
                evaluation_version=settings.omerta_evaluation_version,
                investigation_id=investigation_id,
                trace_id=trace_id,
                status=EvaluationStatus.SKIPPED,
                scores=EvaluationScores(),
                deterministic_validation=det_result,
                summary="Evaluation skipped: OMERTA_EVALUATION_ENABLED is false.",
            )

        # Step 3: Prepare LLM Judge Provider
        provider = self._judge_provider or get_judge_llm_provider()

        # Build prompt
        det_summary = None
        if not det_result.passed:
            det_summary = f"Pre-check detected discrepancies: {'; '.join(det_result.discrepancies)}"

        system_prompt = build_judge_system_prompt()
        user_prompt = build_judge_user_prompt(
            investigation_id=investigation_id,
            task_description=task_description,
            report_dict=report_dict,
            evidence_items=evidence_list,
            context=context_dict,
            deterministic_summary=det_summary,
            expected_labels=expected_labels,
        )

        max_retries = max(0, settings.omerta_evaluation_max_retries)
        last_error: str | None = None
        raw_output: JudgeRawOutput | None = None
        t0 = time.perf_counter()
        attempt_prompt = user_prompt

        # Step 4: Call LLM Judge with Bounded Retries
        for attempt in range(max_retries + 1):
            try:
                response = await provider.complete(system=system_prompt, user=attempt_prompt)
                cleaned_json = _clean_json_markdown(response.content)
                parsed_dict = json.loads(cleaned_json)
                raw_output = JudgeRawOutput.model_validate(parsed_dict)
                break
            except (json.JSONDecodeError, ValidationError) as parse_err:
                last_error = f"Malformed judge JSON response: {parse_err}"
                logger.warning("Judge parsing failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, parse_err)
                attempt_prompt = (
                    f"{user_prompt}\n\n[RETRY NOTICE]: Your previous response was invalid JSON or violated schema. "
                    f"Error: {parse_err}. Please output valid JSON only matching the schema exactly."
                )
            except Exception as exc:
                last_error = f"Judge provider completion error: {exc}"
                logger.warning("Judge call failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)

        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        # Step 5: Handle Evaluation Failure
        if raw_output is None:
            failed_result = InvestigationEvaluationResult(
                evaluation_version=settings.omerta_evaluation_version,
                investigation_id=investigation_id,
                trace_id=trace_id,
                status=EvaluationStatus.FAILED,
                scores=EvaluationScores(),
                deterministic_validation=det_result,
                error_message=last_error,
                summary=f"Evaluation failed after {max_retries + 1} attempt(s): {last_error}",
                judge_metadata={
                    "provider": getattr(provider, "name", "unknown"),
                    "model": getattr(provider, "model", "unknown"),
                    "latency_ms": latency_ms,
                },
            )
            # Record failed evaluation to Langfuse
            record_evaluation_to_langfuse(failed_result, trace_id=trace_id)
            return failed_result

        # Step 6: Assemble Successful Evaluation
        eval_result = InvestigationEvaluationResult(
            evaluation_version=settings.omerta_evaluation_version,
            investigation_id=investigation_id,
            trace_id=trace_id,
            status=EvaluationStatus.COMPLETED,
            scores=raw_output.scores,
            dimension_explanations=raw_output.dimension_explanations,
            unsupported_claims=raw_output.unsupported_claims,
            evidence_gaps=raw_output.evidence_gaps,
            strengths=raw_output.strengths,
            weaknesses=raw_output.weaknesses,
            human_review_required=raw_output.human_review_required,
            review_reasons=raw_output.review_reasons,
            summary=raw_output.summary,
            deterministic_validation=det_result,
            judge_metadata={
                "provider": getattr(provider, "name", "unknown"),
                "model": getattr(provider, "model", "unknown"),
                "latency_ms": latency_ms,
            },
        )

        # Step 7: Record Evaluation to Langfuse
        record_evaluation_to_langfuse(eval_result, trace_id=trace_id)

        return eval_result

