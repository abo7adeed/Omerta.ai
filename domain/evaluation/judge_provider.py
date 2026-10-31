"""Judge LLM provider factory for Omerta.ai.

Allows configuring the evaluation judge model independently from the primary
investigation model, while preserving offline fake provider support and
local Ollama experimentation.
"""

import json
import logging
import re
from typing import Any

from infrastructure.config import get_settings
from infrastructure.llm.base import LLMProvider, LLMResponse
from infrastructure.llm.fake_provider import FakeLLMProvider
from infrastructure.llm.openai_provider import OpenAICompatibleProvider

logger = logging.getLogger(__name__)


class FakeJudgeLLMProvider:
    """Deterministic judge provider for unit tests and offline testing.

    Analyzes the user prompt payload to produce realistic, rubric-aligned evaluations
    without requiring external network or API keys.
    """

    name = "fake-judge"
    model = "fake-judge-v1"

    async def complete(self, system: str, user: str, **kwargs: Any) -> LLMResponse:
        """Analyze prompt and return valid, rubric-conforming JSON evaluation."""
        has_fabricated_id = "TXN-99999-FAKE" in user or "fabricated" in user.lower()
        has_wrong_amount = "85000" in user or "85,000" in user
        has_bad_relation = "subsidiary" in user.lower() or "parent company" in user.lower()
        has_weak_reasoning = "cartel leader" in user.lower() or "criminal mastermind" in user.lower()
        is_legitimate_clean = "legitimate" in user.lower() or "payroll" in user.lower()
        is_incomplete = "incomplete" in user.lower() or "missing device" in user.lower()

        if has_fabricated_id:
            data = {
                "scores": {
                    "evidence_grounding": 1,
                    "reasoning_quality": 2,
                    "investigation_completeness": 3,
                    "report_quality": 3,
                    "overall_quality": 1,
                },
                "dimension_explanations": {
                    "evidence_grounding": "Severe hallucination: report references non-existent transaction TXN-99999-FAKE.",
                    "reasoning_quality": "Reasoning is invalidated by false factual premises.",
                    "investigation_completeness": "Investigated fabricated transactions rather than verified evidence.",
                    "report_quality": "Report format is structured but conveys completely false data.",
                    "overall_quality": "Defective investigation due to fabricated transaction identifier.",
                },
                "unsupported_claims": ["Report cites fabricated transaction TXN-99999-FAKE."],
                "evidence_gaps": ["Verification of transaction against core banking ledger."],
                "strengths": ["Structured format."],
                "weaknesses": ["Severe factual hallucination of non-existent transaction."],
                "human_review_required": True,
                "review_reasons": ["Fabricated transaction ID TXN-99999-FAKE detected."],
                "summary": "Investigation rejected: cites fabricated transaction ID unsupported by ledger.",
            }
        elif has_wrong_amount:
            data = {
                "scores": {
                    "evidence_grounding": 2,
                    "reasoning_quality": 3,
                    "investigation_completeness": 4,
                    "report_quality": 4,
                    "overall_quality": 2,
                },
                "dimension_explanations": {
                    "evidence_grounding": "Major factual error: transaction amount claimed is tenfold higher than verified ledger record.",
                    "reasoning_quality": "Severity assessment was exaggerated based on wrong amount.",
                    "investigation_completeness": "All relevant categories were examined.",
                    "report_quality": "Clear structure but inaccurate numbers.",
                    "overall_quality": "Factual error compromises risk assessment.",
                },
                "unsupported_claims": ["Transaction amount claimed is $85,000 instead of verified $8,500."],
                "evidence_gaps": [],
                "strengths": ["Clear typology identification."],
                "weaknesses": ["Inaccurate transaction amount cited."],
                "human_review_required": True,
                "review_reasons": ["Significant amount discrepancy requires manual correction."],
                "summary": "Investigation contains serious amount mismatch that distorts risk severity.",
            }
        elif has_bad_relation:
            data = {
                "scores": {
                    "evidence_grounding": 2,
                    "reasoning_quality": 2,
                    "investigation_completeness": 3,
                    "report_quality": 4,
                    "overall_quality": 2,
                },
                "dimension_explanations": {
                    "evidence_grounding": "Asserts formal corporate relationship not present in graph topology.",
                    "reasoning_quality": "Assumes corporate control without registry or ownership evidence.",
                    "investigation_completeness": "Graph was checked but mischaracterized.",
                    "report_quality": "Report is well written.",
                    "overall_quality": "Structural relationship incorrectly asserted.",
                },
                "unsupported_claims": ["Account B is claimed to be a wholly owned subsidiary of Account A."],
                "evidence_gaps": ["Beneficial ownership and corporate registry documentation."],
                "strengths": ["Detailed entity breakdown."],
                "weaknesses": ["Uncorroborated corporate ownership claim."],
                "human_review_required": True,
                "review_reasons": ["Uncorroborated entity relationship asserted."],
                "summary": "Report asserts corporate hierarchy unsupported by graph or documentary evidence.",
            }
        elif has_weak_reasoning:
            data = {
                "scores": {
                    "evidence_grounding": 4,
                    "reasoning_quality": 2,
                    "investigation_completeness": 4,
                    "report_quality": 3,
                    "overall_quality": 2,
                },
                "dimension_explanations": {
                    "evidence_grounding": "Underlying transactions and IPs are grounded in evidence.",
                    "reasoning_quality": "Major logical leap: equates routine VPN usage directly with organized cartel leadership.",
                    "investigation_completeness": "Evidence was retrieved.",
                    "report_quality": "Sensationalized tone unsuitable for regulatory reporting.",
                    "overall_quality": "Unsound conclusions drawn from weak circumstantial signals.",
                },
                "unsupported_claims": ["Subject is definitively an international cartel operative."],
                "evidence_gaps": ["Corroborating law enforcement or SAR intelligence."],
                "strengths": ["Accurate transaction facts."],
                "weaknesses": ["Severe leap from correlation to causation."],
                "human_review_required": True,
                "review_reasons": ["Sensationalized hypothesis presented as established fact."],
                "summary": "Evidence is grounded but reasoning exhibits severe logical fallacies and inflammatory assumptions.",
            }
        elif is_incomplete:
            data = {
                "scores": {
                    "evidence_grounding": 4,
                    "reasoning_quality": 3,
                    "investigation_completeness": 2,
                    "report_quality": 3,
                    "overall_quality": 3,
                },
                "dimension_explanations": {
                    "evidence_grounding": "Facts presented are correct.",
                    "reasoning_quality": "Reasoning is constrained by omitted evidence tiers.",
                    "investigation_completeness": "Crucial device and network signals were completely omitted.",
                    "report_quality": "Incomplete sections.",
                    "overall_quality": "Partially complete investigation requiring further evidence gathering.",
                },
                "unsupported_claims": [],
                "evidence_gaps": ["Device footprint and IP velocity signals were not retrieved."],
                "strengths": ["Accurate ledger parsing."],
                "weaknesses": ["Premature conclusion before key evidence sources were queried."],
                "human_review_required": True,
                "review_reasons": ["Key evidence sources uncollected."],
                "summary": "Investigation is incomplete; critical technical signals must be gathered before closing.",
            }
        else:
            data = {
                "scores": {
                    "evidence_grounding": 5,
                    "reasoning_quality": 5,
                    "investigation_completeness": 5,
                    "report_quality": 5,
                    "overall_quality": 5,
                },
                "dimension_explanations": {
                    "evidence_grounding": "All statements and identifiers strictly match verified evidence.",
                    "reasoning_quality": "Clear, objective distinction between observed facts and hypotheses.",
                    "investigation_completeness": "Thorough coverage of all available evidence tiers with limitations noted.",
                    "report_quality": "Professional, actionable executive summary adhering to compliance standards.",
                    "overall_quality": "Exemplary investigation ready for compliance disposition.",
                },
                "unsupported_claims": [],
                "evidence_gaps": [],
                "strengths": ["Airtight evidence citations", "Objective risk analysis", "Clear audit trail"],
                "weaknesses": [],
                "human_review_required": False,
                "review_reasons": [],
                "summary": "Exemplary investigation report: fully grounded, logically rigorous, and structured for compliance action.",
            }

        return LLMResponse(content=json.dumps(data), provider=self.name, model=self.model)


def get_judge_llm_provider(
    force_fake: bool = False,
    provider_override: str | None = None,
    model_override: str | None = None,
) -> LLMProvider:
    """Build the LLM provider configured specifically for evaluation.

    Allows separate judge model/provider from the primary investigation model.
    Falls back gracefully to platform defaults, local Ollama, or Fake provider.
    """
    settings = get_settings()

    if force_fake:
        return FakeJudgeLLMProvider()

    provider_name = (
        provider_override
        or settings.omerta_evaluation_provider
        or settings.llm_provider
        or "fake"
    ).strip().lower()

    # Local Ollama toggle (only applies if evaluation provider is not explicitly set to something else)
    if (
        getattr(settings, "use_local_llm", False)
        and not settings.omerta_evaluation_provider
        and not provider_override
    ):
        model = model_override or getattr(settings, "ollama_model", "qwen3.5:4b")
        base_url = getattr(settings, "ollama_base_url", "http://localhost:11434/v1")
        return OpenAICompatibleProvider(
            name="ollama-judge",
            model=model,
            api_key=settings.llm_api_key or "ollama",
            api_keys=["ollama"],
            base_url=base_url,
            timeout=settings.omerta_evaluation_timeout,
            max_tokens=2048,
        )

    if provider_name in {"fake", ""}:
        return FakeJudgeLLMProvider()

    if provider_name in {"openai", "groq", "ollama", "openai_compatible"}:
        keys: list[str] = []
        raw_candidates = [
            settings.omerta_evaluation_api_keys,
            settings.omerta_evaluation_api_key,
            getattr(settings, "groq_api_keys", None) if provider_name == "groq" else None,
            getattr(settings, "groq_api_key", None) if provider_name == "groq" else None,
            settings.llm_api_keys,
            settings.llm_api_key,
        ]

        for raw in raw_candidates:
            if raw:
                for k in re.split(r"[\s,;]+", str(raw)):
                    if k.strip() and k.strip() not in keys:
                        keys.append(k.strip())

        primary_api_key = keys[0] if keys else None
        if provider_name in {"openai", "groq"} and not keys:
            logger.warning("No API key for judge provider '%s'; falling back to fake judge.", provider_name)
            return FakeJudgeLLMProvider()

        default_base = {
            "openai": "https://api.openai.com/v1",
            "groq": "https://api.groq.com/openai/v1",
            "ollama": "http://localhost:11434/v1",
        }.get(provider_name, "https://api.openai.com/v1")

        base_url = settings.omerta_evaluation_base_url or settings.llm_base_url or default_base
        model = (
            model_override
            or settings.omerta_evaluation_model
            or settings.llm_model
            or ("gpt-4o" if provider_name == "openai" else "openai/gpt-oss-120b")
        )

        return OpenAICompatibleProvider(
            name=f"{provider_name}-judge",
            model=model,
            api_key=primary_api_key,
            api_keys=keys,
            base_url=base_url,
            timeout=settings.omerta_evaluation_timeout,
            max_tokens=2048,
        )

    return FakeJudgeLLMProvider()
