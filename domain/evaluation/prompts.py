"""System and user prompts for the Omerta.ai LLM-as-a-Judge evaluation layer."""

from typing import Any
import json

from domain.evaluation.rubrics import (
    RUBRIC_EVIDENCE_GROUNDING,
    RUBRIC_INVESTIGATION_COMPLETENESS,
    RUBRIC_OVERALL_QUALITY,
    RUBRIC_REASONING_QUALITY,
    RUBRIC_REPORT_QUALITY,
)
from infrastructure.observability import get_managed_prompt


def build_judge_system_prompt() -> str:
    """Return the system prompt for the evaluation judge with rubrics and JSON constraints."""
    fallback = f"""You are a Senior AML Compliance Evaluation Auditor and AI Quality Judge.
Your objective is to impartially assess the quality, factual grounding, and logical rigor of an AI-generated financial crime investigation report.

CRITICAL ETHICAL & LEGAL DIRECTIVES:
1. You evaluate the INVESTIGATION REPORT, not the customer.
2. You must NEVER determine criminal guilt, authorize account freezing, or replace human compliance decisions.
3. Scores are advisory for quality control and model alignment.
4. Do NOT penalize an investigation for missing information that was unavailable or irrelevant.
5. Do NOT treat missing evidence as proof of wrongdoing.

EVALUATION RUBRICS:
{RUBRIC_EVIDENCE_GROUNDING}
{RUBRIC_REASONING_QUALITY}
{RUBRIC_INVESTIGATION_COMPLETENESS}
{RUBRIC_REPORT_QUALITY}
{RUBRIC_OVERALL_QUALITY}

INSTRUCTIONS:
1. Validate all claims, amounts, transaction IDs, account IDs, and device signals against the provided evidence.
2. If the report contains fabricated entities or contradict verified facts, severely penalize Evidence Grounding (score 1 or 2) and flag in unsupported_claims.
3. If the report confuses correlation with causation (e.g. asserting that using a VPN or having a shared device proves money laundering), penalize Reasoning Quality.
4. If a dimension cannot be evaluated meaningfully, return null for its score with an explanation.
5. Output MUST be a SINGLE raw JSON object matching this schema exactly (no markdown formatting, no code fences):
{{
  "scores": {{
    "evidence_grounding": 1-5 or null,
    "reasoning_quality": 1-5 or null,
    "investigation_completeness": 1-5 or null,
    "report_quality": 1-5 or null,
    "overall_quality": 1-5 or null
  }},
  "dimension_explanations": {{
    "evidence_grounding": "string",
    "reasoning_quality": "string",
    "investigation_completeness": "string",
    "report_quality": "string",
    "overall_quality": "string"
  }},
  "unsupported_claims": ["claim 1", ...],
  "evidence_gaps": ["gap 1", ...],
  "strengths": ["strength 1", ...],
  "weaknesses": ["weakness 1", ...],
  "human_review_required": true|false,
  "review_reasons": ["reason 1", ...],
  "summary": "Concise 2-4 sentence executive evaluation summary."
}}
"""
    return get_managed_prompt("omerta-judge-system", fallback=fallback)


def build_judge_user_prompt(
    investigation_id: str,
    task_description: str | None,
    report_dict: dict[str, Any],
    evidence_items: list[dict[str, Any]],
    context: dict[str, Any] | None = None,
    deterministic_summary: str | None = None,
    expected_labels: dict[str, Any] | None = None,
) -> str:
    """Construct structured user prompt containing evidence and report to evaluate."""
    context = context or {}

    payload = {
        "investigation_id": investigation_id,
        "investigation_task": task_description or "Assess transaction/account for financial crime risks.",
        "report_under_review": report_dict,
        "verified_evidence": [
            {
                "evidence_id": e.get("evidence_id"),
                "category": e.get("category"),
                "source": e.get("source"),
                "reference": e.get("reference"),
                "description": e.get("description"),
                "data": e.get("data", {}),
            }
            for e in evidence_items
        ],
        "context_anchors": {
            "transaction_id": context.get("transaction_id"),
            "account_id": context.get("account_id"),
            "transaction_facts": context.get("transaction"),
            "graph_summary": {
                "shared_devices": context.get("shared_devices"),
                "shared_ips": context.get("shared_ips"),
                "connected_accounts": context.get("connected_accounts"),
            },
            "risk_score": context.get("risk_score"),
        },
    }

    if deterministic_summary:
        payload["deterministic_pre_check"] = deterministic_summary

    if expected_labels:
        payload["benchmark_ground_truth"] = expected_labels

    prompt = (
        "Evaluate the following Omerta investigation report against the verified evidence.\n\n"
        f"INVESTIGATION PAYLOAD:\n{json.dumps(payload, default=str, indent=2)}\n\n"
        "Evaluate each dimension using the rubrics. Respond with JSON only."
    )
    return prompt

