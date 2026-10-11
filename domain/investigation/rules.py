"""Banking Rules Engine and Risk Threshold Configuration for Account Investigations.

Follows FATF Guidance, ISO-20022 typologies, and internal Banking Operations Policy (DOC-OPS-001).
Maintains strict separation between:
1. ML model probability/score (from LightGBM)
2. Deterministic rules score (from rule triggers)
3. Combined risk score (weighted and calibrated combination)
4. Operational alert threshold (configurable application threshold: default 0.40)
5. Final analyst decision (bounded recommendations for human compliance officer)
"""

from decimal import Decimal
from typing import Any
from domain.investigation.schemas import (
    AccountFacts,
    BehavioralMetrics,
    GraphIntelligenceOutput,
    MLRiskOutput,
    RecommendedReviewAction,
    RuleReferenceType,
    RuleSeverity,
    TriggeredRuleAlert,
)

# Documented application operational threshold (configurable, not universal international law)
APPLICATION_ALERT_THRESHOLD = 0.40

# Rule weights for deterministic rules score calculation (normalized)
RULE_SEVERITY_WEIGHTS = {
    RuleSeverity.LOW: 0.15,
    RuleSeverity.MEDIUM: 0.35,
    RuleSeverity.HIGH: 0.70,
    RuleSeverity.CRITICAL: 1.00,
}


def evaluate_banking_rules(
    account: AccountFacts | None,
    metrics: BehavioralMetrics,
    graph: GraphIntelligenceOutput,
    currency: str = "EGP",
) -> tuple[list[TriggeredRuleAlert], float]:
    """Evaluate deterministic behavioral rules against account metrics and graph signals."""
    alerts: list[TriggeredRuleAlert] = []

    # 1. Rapid 5-Minute Withdrawal Velocity (FATF Typologies: Rapid Movement of Funds)
    if metrics.velocity_5m_max_count >= 3:
        alerts.append(
            TriggeredRuleAlert(
                rule_id="RULE-VEL-001",
                rule_name="Rapid 5-Minute Withdrawal Velocity",
                severity=RuleSeverity.HIGH,
                reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
                regulatory_reference="FATF Guidance on Financial Investigations (R.10 / R.20) — Rapid velocity tranches",
                applicable_window="5-Minute Rolling Window",
                observed_values={
                    "max_5m_count": metrics.velocity_5m_max_count,
                    "max_5m_volume": float(metrics.velocity_5m_max_volume),
                    "currency": currency,
                },
                threshold_value={"count_threshold": 3, "window_minutes": 5},
                explanation=(
                    f"Observed {metrics.velocity_5m_max_count} withdrawals totaling "
                    f"{metrics.velocity_5m_max_volume:,.2f} {currency} within a 5-minute rolling window, "
                    f"indicating automated cash-out or account drain behavior."
                ),
                evidence_references=["METRIC: velocity_5m_max_count", "METRIC: velocity_5m_max_volume"],
            )
        )

    # 2. Amount Escalation Sequence (FATF Red Flag: Account Testing and Escalation)
    if metrics.has_amount_escalation:
        alerts.append(
            TriggeredRuleAlert(
                rule_id="RULE-ESC-001",
                rule_name="Monotonic Amount Escalation Pattern",
                severity=RuleSeverity.HIGH,
                reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
                regulatory_reference="FATF Red Flags for Account Takeover & Fraud — Progressive amount testing sequences",
                applicable_window="24-Hour Rolling Window",
                observed_values={
                    "escalation_sequences": metrics.escalation_sequences,
                },
                threshold_value={"min_sequence_length": 3, "min_multiplier": 1.5},
                explanation=(
                    f"Detected {len(metrics.escalation_sequences)} escalating withdrawal sequence(s) "
                    f"(e.g., {metrics.escalation_sequences[0] if metrics.escalation_sequences else 'N/A'}), "
                    f"characteristic of preliminary micro-testing followed by rapid balance liquidation."
                ),
                evidence_references=["METRIC: has_amount_escalation", "METRIC: escalation_sequences"],
            )
        )

    # 3. Structuring / Smurfing Pattern (FATF R.10 / R.20: Amounts just below 50,000 EGP reporting limit)
    structuring_txns = 0
    if metrics.total_transactions > 0 and metrics.withdrawal_count >= 2:
        # Check if max withdrawal is near 48,000 - 49,999 EGP
        if Decimal("45000.00") <= metrics.max_withdrawal_amount < Decimal("50000.00"):
            alerts.append(
                TriggeredRuleAlert(
                    rule_id="RULE-STR-001",
                    rule_name="Potential Cash Structuring / Smurfing",
                    severity=RuleSeverity.CRITICAL,
                    reference_type=RuleReferenceType.STATUTORY_REGULATION,
                    regulatory_reference="FATF Recommendation 20 (Suspicious Transaction Reporting Mandate) & National AML Statutory Reporting Laws",
                    applicable_window="30-Day Analysis Period",
                    observed_values={
                        "max_withdrawal": float(metrics.max_withdrawal_amount),
                        "withdrawal_count": metrics.withdrawal_count,
                    },
                    threshold_value={"reporting_threshold": 50000.00, "lower_bound": 45000.00},
                    explanation=(
                        f"Withdrawal amounts closely approach but remain beneath the 50,000 {currency} statutory "
                        f"reporting threshold (peak: {metrics.max_withdrawal_amount:,.2f} {currency}), "
                        f"warranting SAR review for deliberate threshold evasion."
                    ),
                    evidence_references=["METRIC: max_withdrawal_amount"],
                )
            )

    # 4. Off-Hours Financial Activity (DOC-OPS-001 Section 1: Account Lifecycle & Session Governance)
    if metrics.off_hours_count >= 2:
        alerts.append(
            TriggeredRuleAlert(
                rule_id="RULE-OFF-001",
                rule_name="Unusual Off-Hours Transaction Activity",
                severity=RuleSeverity.MEDIUM,
                reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
                regulatory_reference="Internal Banking Operations Policy DOC-OPS-001 — Section 1: Session Governance",
                applicable_window="01:00 - 05:00 UTC",
                observed_values={"off_hours_count": metrics.off_hours_count},
                threshold_value={"threshold": 2},
                explanation=(
                    f"Recorded {metrics.off_hours_count} transactions initiated during off-hours (01:00-05:00), "
                    f"diverging from normal retail customer operational windows."
                ),
                evidence_references=["METRIC: off_hours_count"],
            )
        )

    # 5. Shared Device Network Ring (Neo4j Graph Topology)
    if graph.available and graph.shared_device_count >= 1:
        alerts.append(
            TriggeredRuleAlert(
                rule_id="RULE-DEV-001",
                rule_name="Shared Device Syndicate / Device Ring",
                severity=RuleSeverity.CRITICAL,
                reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
                regulatory_reference="FATF Typologies on Cyber-Enabled Financial Crime — Multi-account hardware sharing",
                applicable_window="Graph Network Analysis",
                observed_values={
                    "shared_devices_count": graph.shared_device_count,
                    "connected_accounts_count": graph.connected_accounts_count,
                },
                threshold_value={"shared_device_limit": 1},
                explanation=(
                    f"Account is linked via hardware fingerprints to {graph.shared_device_count} shared device(s) "
                    f"operating across {graph.connected_accounts_count} distinct account holder(s)."
                ),
                evidence_references=["GRAPH: shared_devices", "GRAPH: connected_accounts"],
            )
        )

    # Calculate deterministic rules score (bounded 0.0 - 1.0)
    if not alerts:
        rules_score = 0.05 if metrics.total_transactions > 0 else 0.0
    else:
        # Highest severity alert establishes base score, secondary alerts add cumulative weight
        severities = [a.severity for a in alerts]
        max_base = max(RULE_SEVERITY_WEIGHTS[s] for s in severities)
        secondary_additive = sum(0.08 for _ in alerts[1:])
        rules_score = round(min(1.0, max_base + secondary_additive), 4)

    return alerts, rules_score


def calculate_combined_risk_score(
    ml_output: MLRiskOutput,
    rules_score: float,
) -> tuple[float, bool]:
    """Combine ML model prediction and deterministic rules score.

    Mathematical Formulation:
    - If ML model loaded & features complete:
        combined = 0.55 * ml_score + 0.45 * rules_score
    - If ML model unavailable / failed:
        combined = 1.00 * rules_score
    Bounded strictly in [0.00, 1.00].
    """
    if ml_output.model_loaded and ml_output.error_message is None:
        ml_score = max(0.0, min(1.0, ml_output.risk_score))
        combined = round(0.55 * ml_score + 0.45 * rules_score, 4)
    else:
        # Fallback to deterministic rules when ML model cannot score
        combined = round(rules_score, 4)

    threshold_exceeded = combined >= APPLICATION_ALERT_THRESHOLD
    return combined, threshold_exceeded


def determine_recommended_action(
    combined_score: float,
    alerts: list[TriggeredRuleAlert],
    account: AccountFacts | None,
) -> tuple[RecommendedReviewAction, str]:
    """Map combined risk score and alert severities to bounded compliance recommendations."""
    critical_alerts = [a for a in alerts if a.severity == RuleSeverity.CRITICAL]
    high_alerts = [a for a in alerts if a.severity == RuleSeverity.HIGH]

    if critical_alerts or combined_score >= 0.85:
        return (
            RecommendedReviewAction.ESCALATE_TO_FIU,
            (
                f"Combined risk score of {combined_score:.1%} exceeds critical thresholds with "
                f"{len(critical_alerts)} CRITICAL rule indicator(s). Immediate multi-eye compliance "
                f"escalation and formal Suspicious Activity Report (SAR) filing evaluation recommended."
            ),
        )
    elif high_alerts or combined_score >= APPLICATION_ALERT_THRESHOLD:
        return (
            RecommendedReviewAction.HUMAN_REVIEW,
            (
                f"Combined risk score of {combined_score:.1%} triggers mandatory human review under "
                f"the 40.0% application operational threshold. Assigned to tier-2 compliance queue "
                f"for source-of-funds verification."
            ),
        )
    elif combined_score >= 0.20:
        return (
            RecommendedReviewAction.REQUEST_CUSTOMER_INFO,
            (
                f"Moderate risk score of {combined_score:.1%}. Recommend requesting updated KYC documentation "
                f"or transaction justification prior to higher-limit outbound transfers."
            ),
        )
    else:
        return (
            RecommendedReviewAction.ROUTINE_MONITORING,
            (
                f"Risk score of {combined_score:.1%} is within standard parameters. Continue routine automated "
                f"continuous ledger monitoring without human intervention."
            ),
        )
