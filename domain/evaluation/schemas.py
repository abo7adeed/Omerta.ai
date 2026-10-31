"""Evaluation schemas for Omerta.ai LLM-as-a-Judge and Deterministic Validation.

Enforces valid score ranges (1-5 or null), deterministic verification results,
and compliance analyst-oriented audit structures.
"""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class EvaluationStatus(StrEnum):
    """Lifecycle status of an evaluation run."""

    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EvaluationScores(BaseModel):
    """Structured 1-5 quality scores across the five core evaluation dimensions.

    Each dimension accepts integer 1 to 5, or None (null) if the dimension
    cannot be meaningfully evaluated (e.g. evidence unavailable or irrelevant).
    """

    evidence_grounding: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Factual consistency of claims against verified evidence (1=completely hallucinated, 5=perfectly grounded).",
    )
    reasoning_quality: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Logical soundness and distinction between facts vs hypotheses (1=irrational/contradictory, 5=airtight logic).",
    )
    investigation_completeness: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Coverage of relevant available evidence sources and disclosure of gaps (1=grossly incomplete, 5=thorough with gaps acknowledged).",
    )
    report_quality: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Structure, clarity, and usefulness for a compliance analyst (1=incomprehensible, 5=exemplary compliance report).",
    )
    overall_quality: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Holistic evaluation synthesis (1=unusable, 5=production grade investigation).",
    )


class DeterministicCheckItem(BaseModel):
    """Result of an individual deterministic factual check."""

    check_name: str
    passed: bool
    details: str
    discrepancies: list[str] = Field(default_factory=list)
    unverified_items: list[str] = Field(default_factory=list)


class DeterministicValidationResult(BaseModel):
    """Deterministic validation findings executed independently of LLM judgments.

    Compares report claims against source records, graph topology, and evidence IDs.
    """

    passed: bool = True
    account_ids_valid: bool = True
    transaction_ids_valid: bool = True
    amounts_valid: bool = True
    dates_valid: bool = True
    relationships_valid: bool = True
    evidence_references_valid: bool = True
    schema_valid: bool = True

    discrepancies: list[str] = Field(
        default_factory=list,
        description="Deterministic factual contradictions found in the report.",
    )
    unverified_claims: list[str] = Field(
        default_factory=list,
        description="Entities or assertions that could not be verified against available records.",
    )
    checks: list[DeterministicCheckItem] = Field(
        default_factory=list,
        description="Granular check breakdown.",
    )


class JudgeRawOutput(BaseModel):
    """Untrusted raw JSON response schema parsed from the LLM-as-a-Judge completion."""

    scores: EvaluationScores
    dimension_explanations: dict[str, str] = Field(
        default_factory=dict,
        description="Per-dimension rationale, required especially when a score is null or <= 2.",
    )
    unsupported_claims: list[str] = Field(
        default_factory=list,
        description="Claims made in the report that have no backing in the provided evidence.",
    )
    evidence_gaps: list[str] = Field(
        default_factory=list,
        description="Important unanswered investigative questions or uncollected signals.",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Notable investigative rigor, valid citations, or clear explanations.",
    )
    weaknesses: list[str] = Field(
        default_factory=list,
        description="Identified flaws, premature assumptions, or omitted sources.",
    )
    human_review_required: bool = Field(
        default=False,
        description="Whether a human compliance officer must review the investigation before proceeding.",
    )
    review_reasons: list[str] = Field(
        default_factory=list,
        description="Specific reasons requiring human intervention.",
    )
    summary: str = Field(
        min_length=1,
        description="Concise synthesis explaining the evaluation scores and key findings.",
    )


class InvestigationEvaluationResult(BaseModel):
    """Validated, production-grade evaluation result combining LLM judge & deterministic checks."""

    evaluation_version: str = "1.0"
    investigation_id: str
    trace_id: str | None = None
    trace_url: str | None = Field(
        default=None,
        description="Direct URL link to view trace and evaluation scores in Langfuse dashboard.",
    )
    status: EvaluationStatus = EvaluationStatus.COMPLETED

    scores: EvaluationScores
    dimension_explanations: dict[str, str] = Field(default_factory=dict)
    unsupported_claims: list[str] = Field(default_factory=list)
    evidence_gaps: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    summary: str = ""

    deterministic_validation: DeterministicValidationResult | None = None
    judge_metadata: dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None

    disclaimer: str = (
        "ADVISORY NOTICE: Evaluation scores are generated by an automated LLM-as-a-Judge "
        "and deterministic validation layer. They evaluate investigation quality and rigor, "
        "not criminal guilt or liability, and do not replace human compliance authority."
    )

    @model_validator(mode="after")
    def _enforce_human_review_policy(self) -> "InvestigationEvaluationResult":
        """Deterministic policy guardrail: ensure human review is triggered on critical flaws."""
        reasons = list(self.review_reasons)
        needs_review = self.human_review_required

        # Rule 1: If deterministic validation failed (e.g. fabricated IDs or amounts)
        if self.deterministic_validation and not self.deterministic_validation.passed:
            needs_review = True
            for d in self.deterministic_validation.discrepancies:
                if d not in reasons:
                    reasons.append(f"Deterministic discrepancy: {d}")

        # Rule 2: If overall quality or evidence grounding is critically low (<= 2)
        if self.scores.overall_quality is not None and self.scores.overall_quality <= 2:
            needs_review = True
            if "Critically low overall investigation quality (<= 2)" not in reasons:
                reasons.append("Critically low overall investigation quality (<= 2)")

        if self.scores.evidence_grounding is not None and self.scores.evidence_grounding <= 2:
            needs_review = True
            if "Severe evidence grounding failure (<= 2)" not in reasons:
                reasons.append("Severe evidence grounding failure (<= 2)")

        # Rule 3: If unsupported claims exist
        if self.unsupported_claims and not any("Unsupported claim" in r for r in reasons):
            needs_review = True
            reasons.append(f"{len(self.unsupported_claims)} unsupported claim(s) detected in report")

        self.human_review_required = needs_review
        self.review_reasons = reasons
        return self

