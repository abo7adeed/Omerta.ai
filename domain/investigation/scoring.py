"""Authoritative Risk Scoring & Transaction Policy Decision Service for Omerta.ai.

Defines `calculate_final_risk_score(assessment)`:
- Strictly calibrated on a 0-100 scale.
- Versioned formula: 'risk-v1'.
- Explicit specialist weights: rules (0.20), ml (0.25), history (0.20), behavior (0.10),
  ato (0.10), device (0.05), graph (0.05), merchant (0.05).
- Proportional weight normalization for genuinely non-applicable agents.
- Degraded confidence tracking when models or agents are unavailable.
- Deterministic hard security overrides for holds, ATO, VPN verification, and restrictions.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, Field

from domain.investigation.agent_schemas import AgentExecutionStatus, SpecialistAgentResult


class RiskTier(StrEnum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    ELEVATED = "ELEVATED"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class TransactionDecision(StrEnum):
    ALLOW = "ALLOW"
    PENDING_CUSTOMER_VERIFICATION = "PENDING_CUSTOMER_VERIFICATION"
    PENDING_REVIEW = "PENDING_REVIEW"
    HOLD = "HOLD"
    REJECT = "REJECT"


class AssessmentConfidence(StrEnum):
    SUFFICIENT = "SUFFICIENT"
    DEGRADED = "DEGRADED"
    INSUFFICIENT = "INSUFFICIENT"


# Default Configurable Formula Weights (Sum = 1.00)
DEFAULT_RISK_WEIGHTS: dict[str, float] = {
    "rules": 0.20,
    "ml": 0.25,
    "history": 0.20,
    "behavior": 0.10,
    "ato": 0.10,
    "device": 0.05,
    "graph": 0.05,
    "merchant": 0.05,
}

FORMULA_VERSION = "risk-v1"


class CalculationStep(BaseModel):
    """Individual mathematical contribution in the composite formula."""

    component: str
    raw_score: float | None
    weight: float
    effective_weight: float
    weighted_contribution: float
    status: str
    notes: str


class AuthoritativeRiskAssessment(BaseModel):
    """Complete, validated final scoring contract."""

    final_score: float = Field(ge=0.0, le=100.0, description="Authoritative composite score on 0-100 scale")
    score_scale: str = "0-100"
    formula_version: str = FORMULA_VERSION
    risk_tier: RiskTier
    decision: TransactionDecision
    requires_human_review: bool
    requires_customer_verification: bool
    requires_transaction_hold: bool
    hold_reasons: list[str] = Field(default_factory=list)
    assessment_confidence: AssessmentConfidence
    components: dict[str, float | None] = Field(default_factory=dict)
    calculation: list[CalculationStep] = Field(default_factory=list)
    triggered_rule_ids: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)


def calculate_final_risk_score(
    agent_results: dict[str, SpecialistAgentResult],
    weights: dict[str, float] | None = None,
    hard_restrictions_active: bool = False,
    vpn_detected: bool = False,
    is_merchant_tx: bool = False,
    customer_confirmed: bool | None = None,  # None: unverified, True: confirmed, False: denied
) -> AuthoritativeRiskAssessment:
    """Compute the single authoritative final risk score across all specialist agents.

    Parameters:
    - agent_results: Dictionary mapping agent keys ('rules', 'ml', 'history', etc.) to SpecialistAgentResult
    - weights: Optional custom weights dict (defaults to DEFAULT_RISK_WEIGHTS)
    - hard_restrictions_active: Whether server-enforced transfer restrictions exist on the customer/account
    - vpn_detected: Whether commercial VPN or proxy telemetry was confirmed
    - is_merchant_tx: Whether this transaction type involves a commercial merchant (False for P2P transfers)
    - customer_confirmed: Result of customer confirmation step if applicable
    """
    active_weights = dict(weights or DEFAULT_RISK_WEIGHTS)

    # 1. Determine agent applicability and availability
    applicable_agents: dict[str, SpecialistAgentResult] = {}
    calculation_steps: list[CalculationStep] = []
    components: dict[str, float | None] = {}
    triggered_rule_ids: list[str] = []
    evidence_ids: list[str] = []

    has_degraded_agent = False
    has_failed_required_agent = False

    for comp_key, base_weight in active_weights.items():
        agent = agent_results.get(comp_key)

        if not agent:
            # Missing agent
            has_failed_required_agent = True
            components[comp_key] = None
            calculation_steps.append(
                CalculationStep(
                    component=comp_key,
                    raw_score=None,
                    weight=base_weight,
                    effective_weight=0.0,
                    weighted_contribution=0.0,
                    status="MISSING",
                    notes="Agent was not provided to assessment engine",
                )
            )
            continue

        # Collect evidence & findings
        for f in agent.findings:
            if f.rule_id and f.rule_id not in triggered_rule_ids:
                triggered_rule_ids.append(f.rule_id)
        for ev in agent.evidence_ids:
            if ev not in evidence_ids:
                evidence_ids.append(ev)

        if comp_key == "merchant" and not is_merchant_tx:
            # Genuine peer-to-peer transfer: merchant risk is NOT_APPLICABLE
            components[comp_key] = None
            calculation_steps.append(
                CalculationStep(
                    component=comp_key,
                    raw_score=None,
                    weight=base_weight,
                    effective_weight=0.0,
                    weighted_contribution=0.0,
                    status="NOT_APPLICABLE",
                    notes="Peer-to-peer customer transfer; merchant risk does not apply",
                )
            )
            continue

        if agent.status in (AgentExecutionStatus.UNAVAILABLE, AgentExecutionStatus.FAILED, AgentExecutionStatus.TIMED_OUT):
            has_degraded_agent = True
            components[comp_key] = None
            calculation_steps.append(
                CalculationStep(
                    component=comp_key,
                    raw_score=None,
                    weight=base_weight,
                    effective_weight=0.0,
                    weighted_contribution=0.0,
                    status=agent.status.value,
                    notes=f"Agent returned {agent.status.value}: {agent.error_message or 'Service unavailable'}",
                )
            )
            continue

        # Valid applicable agent with numeric score
        applicable_agents[comp_key] = agent
        components[comp_key] = round(agent.score, 2)

    # 2. Normalize weights over applicable & available agents
    total_applicable_weight = sum(active_weights[k] for k in applicable_agents.keys())
    composite_score = 0.0

    if total_applicable_weight > 0.0:
        for comp_key, agent in applicable_agents.items():
            base_w = active_weights[comp_key]
            effective_w = base_w / total_applicable_weight
            contrib = agent.score * effective_w
            composite_score += contrib

            calculation_steps.append(
                CalculationStep(
                    component=comp_key,
                    raw_score=round(agent.score, 2),
                    weight=base_w,
                    effective_weight=round(effective_w, 4),
                    weighted_contribution=round(contrib, 2),
                    status=agent.status.value,
                    notes=f"Contributed {contrib:.2f} points via {agent.agent_name}",
                )
            )
    else:
        # Fallback if no agents scored: default to 50.0 high-caution score
        composite_score = 50.0

    final_score = round(max(0.0, min(100.0, composite_score)), 2)

    # 3. Determine Risk Tier from Configured Thresholds
    # Geographic impossible travel escalates minimum score to HIGH tier
    if "RULE-GEO-TRAVEL-001" in triggered_rule_ids or "IMPOSSIBLE_TRAVEL_VELOCITY" in triggered_rule_ids:
        final_score = max(final_score, 65.0)

    if final_score < 20.0:
        risk_tier = RiskTier.LOW
    elif final_score < 40.0:
        risk_tier = RiskTier.MODERATE
    elif final_score < 60.0:
        risk_tier = RiskTier.ELEVATED
    elif final_score < 80.0:
        risk_tier = RiskTier.HIGH
    else:
        risk_tier = RiskTier.CRITICAL

    # 4. Assess Confidence
    if has_failed_required_agent:
        confidence = AssessmentConfidence.INSUFFICIENT
    elif has_degraded_agent:
        confidence = AssessmentConfidence.DEGRADED
    else:
        confidence = AssessmentConfidence.SUFFICIENT

    # 5. Evaluate Hard Security Controls & Hold Overrides
    hold_reasons: list[str] = []
    requires_hold = False
    requires_verification = False
    requires_review = False

    # Overriding Control A: Customer explicit denial
    if customer_confirmed is False:
        requires_hold = True
        decision = TransactionDecision.REJECT
        hold_reasons.append("Customer reported transaction as unrecognized/fraudulent (CUSTOMER_DENIED).")
        return AuthoritativeRiskAssessment(
            final_score=max(85.0, final_score),
            score_scale="0-100",
            formula_version=FORMULA_VERSION,
            risk_tier=RiskTier.CRITICAL,
            decision=decision,
            requires_human_review=True,
            requires_customer_verification=False,
            requires_transaction_hold=True,
            hold_reasons=hold_reasons,
            assessment_confidence=confidence,
            components=components,
            calculation=calculation_steps,
            triggered_rule_ids=triggered_rule_ids,
            evidence_ids=evidence_ids,
        )

    # Overriding Control B: Hard transfer restrictions active on customer account
    if hard_restrictions_active or "RULE-RESTRICT-001" in triggered_rule_ids:
        requires_hold = True
        requires_review = True
        hold_reasons.append("Account is subject to active OUTGOING_TRANSFERS_ONLY restriction.")

    # Overriding Control C: Confirmed Account Takeover (ATO) chain
    ato_score = components.get("ato") or 0.0
    if ato_score >= 70.0 or "RULE-ATO-001" in triggered_rule_ids:
        requires_hold = True
        requires_verification = True
        requires_review = True
        hold_reasons.append("High-probability Account Takeover sequence observed across credential/session events.")

    # Overriding Control D: VPN / Proxy detection rule
    if vpn_detected or "RULE-NETWORK-VPN-001" in triggered_rule_ids:
        requires_hold = True
        requires_verification = True
        hold_reasons.append("Commercial VPN/proxy detected on transfer session origin. Mandatory customer confirmation triggered.")

    # Overriding Control E: Composite score thresholds
    if final_score >= 80.0:
        requires_hold = True
        requires_review = True
        hold_reasons.append(f"Composite risk score ({final_score:.1f}/100) exceeds critical-risk policy threshold (80.0).")
    elif final_score >= 40.0:
        requires_review = True
        hold_reasons.append(f"Composite risk score ({final_score:.1f}/100) triggers elevated review threshold (40.0).")

    # Overriding Control F: Fail-safe conservative hold for missing or failed mandatory evidence
    if has_failed_required_agent:
        requires_hold = True
        requires_review = True
        hold_reasons.append("Mandatory specialist risk evidence unavailable or failed. Fail-safe conservative security hold applied awaiting analyst review.")

    # 6. Synthesize Final Policy Decision
    if requires_hold:
        if requires_verification and customer_confirmed is not True:
            decision = TransactionDecision.PENDING_CUSTOMER_VERIFICATION
        else:
            decision = TransactionDecision.PENDING_REVIEW
    else:
        decision = TransactionDecision.ALLOW

    return AuthoritativeRiskAssessment(
        final_score=final_score,
        score_scale="0-100",
        formula_version=FORMULA_VERSION,
        risk_tier=risk_tier,
        decision=decision,
        requires_human_review=requires_review,
        requires_customer_verification=requires_verification and (customer_confirmed is not True),
        requires_transaction_hold=requires_hold,
        hold_reasons=hold_reasons,
        assessment_confidence=confidence,
        components=components,
        calculation=calculation_steps,
        triggered_rule_ids=triggered_rule_ids,
        evidence_ids=evidence_ids,
    )
