"""Langfuse score association and trace reporting for Omerta.ai evaluations.

Compatible with Langfuse Python SDK v2.60+. Emits numerical quality scores,
categorical deterministic verification flags, and evaluation audit metadata
associated with the investigation trace.
"""

import logging
from typing import Any

from domain.evaluation.schemas import EvaluationStatus, InvestigationEvaluationResult
from infrastructure.config import get_settings
from infrastructure.observability import flush_langfuse, get_langfuse_client

logger = logging.getLogger(__name__)


def record_evaluation_to_langfuse(
    result: InvestigationEvaluationResult,
    trace_id: str | None = None,
    client: Any | None = None,
) -> bool:
    """Record structured evaluation scores and metadata to Langfuse trace.

    Returns True if successfully sent to Langfuse, False if skipped or failed.
    Never raises an exception: protects workflow execution.
    """
    lf = client or get_langfuse_client()
    if not lf:
        logger.debug("Langfuse client unavailable or disabled; evaluation not published.")
        return False

    settings = get_settings()
    target_trace_id = trace_id or result.trace_id

    # If no existing trace_id provided, create a dedicated trace for this evaluation run
    if not target_trace_id:
        try:
            trace = lf.trace(
                name=f"investigation-eval-{result.investigation_id}",
                metadata={
                    "investigation_id": result.investigation_id,
                    "evaluation_version": result.evaluation_version,
                    "status": result.status.value,
                },
                tags=["evaluation", "omerta-judge"],
            )
            target_trace_id = trace.id
            result.trace_id = target_trace_id
            if hasattr(trace, "get_trace_url"):
                result.trace_url = trace.get_trace_url()
        except Exception as exc:
            logger.debug("Could not create dedicated Langfuse trace for evaluation: %s", exc)

    if not target_trace_id:
        logger.debug("No trace_id available or creatable; skipping Langfuse score association.")
        return False

    result.trace_id = target_trace_id
    if not result.trace_url:
        host = (settings.langfuse_host or "http://localhost:3000").rstrip("/")
        result.trace_url = f"{host}/trace/{target_trace_id}"

    try:
        # 1. If evaluation failed, record failure score
        if result.status == EvaluationStatus.FAILED:
            lf.score(
                trace_id=target_trace_id,
                name="evaluation_status",
                value="FAILED",
                comment=f"Evaluation failed: {result.error_message or 'Unknown error'}",
                data_type="CATEGORICAL",
            )
            flush_langfuse(lf)
            return True

        scores = result.scores
        explanations = result.dimension_explanations

        # 2. Emit individual numerical dimension scores (1-5)
        dimension_map = [
            ("evidence_grounding", scores.evidence_grounding),
            ("reasoning_quality", scores.reasoning_quality),
            ("investigation_completeness", scores.investigation_completeness),
            ("report_quality", scores.report_quality),
            ("overall_quality", scores.overall_quality),
        ]

        for dim_name, score_val in dimension_map:
            if score_val is not None:
                comment = explanations.get(dim_name, "")
                lf.score(
                    trace_id=target_trace_id,
                    name=dim_name,
                    value=float(score_val),
                    comment=comment[:500] if comment else None,
                    data_type="NUMERIC",
                )

        # 3. Emit categorical deterministic validation score
        if result.deterministic_validation:
            det_val = "PASSED" if result.deterministic_validation.passed else "FAILED"
            det_comment = "; ".join(result.deterministic_validation.discrepancies) or "All deterministic checks passed."
            lf.score(
                trace_id=target_trace_id,
                name="deterministic_validation",
                value=det_val,
                comment=det_comment[:500],
                data_type="CATEGORICAL",
            )

        # 4. Emit human review flag
        review_val = "REQUIRED" if result.human_review_required else "NOT_REQUIRED"
        review_comment = "; ".join(result.review_reasons) or "No human review triggers."
        lf.score(
            trace_id=target_trace_id,
            name="human_review_required",
            value=review_val,
            comment=review_comment[:500],
            data_type="CATEGORICAL",
        )

        # 5. Emit overall completion status
        lf.score(
            trace_id=target_trace_id,
            name="evaluation_status",
            value="COMPLETED",
            comment=result.summary[:500] if result.summary else "Evaluation completed successfully",
            data_type="CATEGORICAL",
        )

        # 6. Flush client to ensure immediate delivery
        flush_langfuse(lf)
        logger.info(
            "Recorded evaluation scores to Langfuse trace '%s' (Overall: %s, URL: %s)",
            target_trace_id,
            scores.overall_quality,
            result.trace_url,
        )
        return True

    except Exception as exc:
        logger.warning("Failed to record evaluation scores to Langfuse: %s", exc)
        return False

