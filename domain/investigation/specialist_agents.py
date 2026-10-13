"""Specialist Investigation Agents for Omerta.ai.

Contains standardized implementations of:
- BankingRulesAgent
- BehavioralAnalysisAgent
- AccountTakeoverAgent
- DeviceNetworkAgent (including VPN / Proxy intelligence)
- GraphIntelligenceAgent (Neo4j topology)
- MLRiskAgent (LightGBM inference)
- MerchantIntelligenceAgent (P2P vs commercial)
- IdentitySecurityAgent (KYC and security restrictions)
- FinalDecisionAgent (Authoritative synthesis)
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging
import time
from typing import Any

from domain.investigation.agent_schemas import (
    AgentDataQuality,
    AgentExecutionStatus,
    AgentFinding,
    SpecialistAgentResult,
    VPNDetectionDetails,
)
from domain.investigation.rule_registry import BANKING_RULES_REGISTRY, RuleSeverity
from domain.investigation.scoring import calculate_final_risk_score, AuthoritativeRiskAssessment

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# 1. Banking Rules Agent
# --------------------------------------------------------------------------- #
class BankingRulesAgent:
    """Evaluates deterministic banking risk rules and computes rule-based risk score."""

    @staticmethod
    def evaluate(
        history_metrics: dict[str, Any],
        vpn_detected: bool = False,
        is_new_device: bool = False,
        shared_device_count: int = 0,
        failed_attempts: int = 0,
        has_active_restriction: bool = False,
        impossible_travel: bool = False,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        findings: list[AgentFinding] = []
        points_breakdown: dict[str, float] = {}
        total_points = 0.0

        current_amount = history_metrics.get("current_amount", 0.0)
        amount_to_avg_ratio = history_metrics.get("amount_to_average_ratio", 1.0)
        tx_5m = history_metrics.get("previous_transactions_5m", 0)
        vol_5m = history_metrics.get("outgoing_total_5m", 0.0)
        tx_15m = history_metrics.get("previous_transactions_15m", 0)
        vol_15m = history_metrics.get("outgoing_total_15m", 0.0)
        tx_60m = history_metrics.get("previous_transactions_60m", 0)
        is_first_beneficiary = history_metrics.get("is_first_transaction_with_beneficiary", False)

        # Rule: Amount Deviation
        if amount_to_avg_ratio >= 3.0:
            rule = BANKING_RULES_REGISTRY["RULE-AMOUNT-DEV-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"Current amount is {amount_to_avg_ratio}x historical average.",
                evidence_ids=["METRIC:amount_to_average_ratio"],
                observed_values={"ratio": amount_to_avg_ratio, "threshold": 3.0},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: 5-minute velocity
        if tx_5m >= 3:
            rule = BANKING_RULES_REGISTRY["RULE-VEL-5M"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"Observed {tx_5m} transactions within 5 minutes totaling {vol_5m:,.2f}.",
                evidence_ids=["METRIC:previous_transactions_5m"],
                observed_values={"count": tx_5m, "threshold": 3},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: 15-minute velocity
        if tx_15m >= 5 or vol_15m >= 40000.0:
            rule = BANKING_RULES_REGISTRY["RULE-VEL-15M"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"Recorded {tx_15m} transactions totaling {vol_15m:,.2f} in 15 minutes.",
                evidence_ids=["METRIC:previous_transactions_15m"],
                observed_values={"count": tx_15m, "volume": vol_15m},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: Cash Structuring / Smurfing
        if 45000.0 <= current_amount < 50000.0:
            rule = BANKING_RULES_REGISTRY["RULE-STR-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"Amount of {current_amount:,.2f} placed just under 50,000 statutory reporting boundary.",
                evidence_ids=["METRIC:current_amount"],
                observed_values={"amount": current_amount, "threshold_range": "45000-50000"},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: VPN / Proxy detection
        if vpn_detected:
            rule = BANKING_RULES_REGISTRY["RULE-NETWORK-VPN-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason="Commercial VPN/proxy provider detected on transaction origin.",
                evidence_ids=["TELEMETRY:is_vpn"],
                observed_values={"vpn_detected": True},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: First time beneficiary high value
        if is_first_beneficiary and current_amount >= 20000.0:
            rule = BANKING_RULES_REGISTRY["RULE-BENEF-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"First transfer to new beneficiary with elevated amount ({current_amount:,.2f}).",
                evidence_ids=["METRIC:is_first_transaction_with_beneficiary"],
                observed_values={"amount": current_amount},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: Shared device ring
        if shared_device_count >= 2:
            rule = BANKING_RULES_REGISTRY["RULE-DEV-RING"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason=f"Device is shared with {shared_device_count} distinct customer accounts.",
                evidence_ids=["GRAPH:shared_device_count"],
                observed_values={"shared_count": shared_device_count},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: Active Restriction Hold
        if has_active_restriction:
            rule = BANKING_RULES_REGISTRY["RULE-RESTRICT-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason="Account has active security restrictions prohibiting outgoing transfers.",
                evidence_ids=["POLICY:restriction_scope"],
                observed_values={"restricted": True},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Rule: Impossible Geographic Velocity
        if impossible_travel:
            rule = BANKING_RULES_REGISTRY["RULE-GEO-TRAVEL-001"]
            findings.append(AgentFinding(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                points=rule.points,
                severity=rule.severity.value,
                reason="Sequential transactions from distinct locations requiring physically impossible travel velocity.",
                evidence_ids=["METRIC:impossible_travel"],
                observed_values={"impossible_travel": True},
            ))
            points_breakdown[rule.rule_id] = rule.points
            total_points += rule.points

        # Base score scaling
        final_score = round(min(100.0, total_points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Banking Rules Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"total_rules_evaluated": len(BANKING_RULES_REGISTRY), "triggered_rules_count": len(findings)},
            findings=findings,
            points_breakdown=points_breakdown,
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(history_available=True, is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 2. Behavioral Analysis Agent
# --------------------------------------------------------------------------- #
class BehavioralAnalysisAgent:
    """Evaluates customer behavior deviation: unusual hour, frequency, amount."""

    @staticmethod
    def evaluate(
        history_metrics: dict[str, Any],
        hour_utc: int = 12,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        findings: list[AgentFinding] = []
        points = 0.0

        # Off-hours check (01:00 to 05:00 UTC)
        if 1 <= hour_utc <= 5:
            points += 20.0
            findings.append(AgentFinding(
                rule_id="BEHAV-OFF-HOURS",
                rule_name="Off-Hours Transaction Execution",
                points=20.0,
                severity="MEDIUM",
                reason=f"Transaction initiated at {hour_utc:02d}:00 UTC (dormant customer window).",
                evidence_ids=["TIMESTAMP:hour_utc"],
                observed_values={"hour": hour_utc},
            ))

        # Deviation from average
        ratio = history_metrics.get("amount_to_average_ratio", 1.0)
        if ratio >= 4.0:
            dev_pts = min(40.0, (ratio - 4.0) * 8.0 + 15.0)
            points += dev_pts
            findings.append(AgentFinding(
                rule_id="BEHAV-AMT-OUTLIER",
                rule_name="Extreme Amount Outlier Deviation",
                points=dev_pts,
                severity="HIGH",
                reason=f"Transfer amount diverges {ratio}x from customer baseline.",
                evidence_ids=["METRIC:amount_to_average_ratio"],
                observed_values={"ratio": ratio},
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Behavioral Analysis Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"hour_utc": hour_utc, "deviation_ratio": ratio},
            findings=findings,
            points_breakdown={"off_hours": 20.0 if (1 <= hour_utc <= 5) else 0.0, "amount_deviation": points - (20.0 if (1 <= hour_utc <= 5) else 0.0)},
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(history_available=True, is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 3. Account Takeover (ATO) Agent
# --------------------------------------------------------------------------- #
class AccountTakeoverAgent:
    """Evaluates chronological security event chains indicating credential compromise."""

    @staticmethod
    def evaluate(
        recent_password_change: bool = False,
        recent_failed_logins: int = 0,
        recent_device_added: bool = False,
        new_beneficiary_added: bool = False,
        time_since_pw_reset_minutes: float | None = None,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        findings: list[AgentFinding] = []
        points = 0.0
        attack_chain_steps = 0

        if recent_failed_logins >= 3:
            attack_chain_steps += 1
            points += 20.0
            findings.append(AgentFinding(
                rule_id="ATO-BRUTE-FORCE",
                rule_name="Multiple Failed Login Attempts",
                points=20.0,
                severity="MEDIUM",
                reason=f"Recorded {recent_failed_logins} failed login attempts prior to transaction.",
                evidence_ids=["AUTH:failed_logins"],
                observed_values={"failed_logins": recent_failed_logins},
            ))

        if recent_password_change and (time_since_pw_reset_minutes is None or time_since_pw_reset_minutes <= 120.0):
            attack_chain_steps += 1
            pts = 35.0
            points += pts
            findings.append(AgentFinding(
                rule_id="ATO-RECENT-PW-CHANGE",
                rule_name="Immediate Transfer Following Password Change",
                points=pts,
                severity="HIGH",
                reason="Transfer dispatched within 2 hours of password reset / change.",
                evidence_ids=["AUTH:password_changed_at"],
                observed_values={"minutes_since_change": time_since_pw_reset_minutes},
            ))

        if recent_device_added and attack_chain_steps >= 1:
            attack_chain_steps += 1
            points += 25.0
            findings.append(AgentFinding(
                rule_id="ATO-DEVICE-CHAIN",
                rule_name="New Device Paired in Compromise Window",
                points=25.0,
                severity="HIGH",
                reason="New hardware device enrolled alongside authentication changes.",
                evidence_ids=["DEVICE:enrolled_recent"],
                observed_values={"chain_steps": attack_chain_steps},
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Account Takeover Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"attack_chain_steps": attack_chain_steps, "failed_logins": recent_failed_logins},
            findings=findings,
            points_breakdown={"ato_points": final_score},
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(history_available=True, is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 4. Device and Network Agent
# --------------------------------------------------------------------------- #
class DeviceNetworkAgent:
    """Evaluates hardware fingerprint, proxy/VPN detection, and IP reputation."""

    @staticmethod
    def evaluate(
        is_new_device: bool = False,
        is_vpn: bool = False,
        ip_risk_score: float = 0.0,
        provider_available: bool = True,
        country: str = "EG",
        city: str | None = None,
        prev_country: str | None = None,
        prev_city: str | None = None,
        prev_timestamp: datetime | None = None,
        current_timestamp: datetime | None = None,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        findings: list[AgentFinding] = []
        points = 0.0

        vpn_details = VPNDetectionDetails(
            vpn_detected=is_vpn,
            proxy_detected=is_vpn,
            ip_risk_score=ip_risk_score,
            country_detected=country,
            detection_status="DETECTED" if is_vpn else ("UNAVAILABLE" if not provider_available else "NOT_DETECTED"),
        )

        if not provider_available:
            data_quality = AgentDataQuality(is_sufficient=False, quality_notes="VPN provider telemetry unavailable")
        else:
            data_quality = AgentDataQuality(is_sufficient=True)

        if is_vpn:
            points += 35.0
            findings.append(AgentFinding(
                rule_id="DEV-NET-VPN-001",
                rule_name="Commercial VPN / Proxy Anonymizer Active",
                points=35.0,
                severity="HIGH",
                reason="Traffic routed through commercial VPN/proxy server with cloaked IP origin.",
                evidence_ids=["NET:is_vpn"],
                observed_values={"vpn_detected": True, "ip_risk_score": ip_risk_score},
            ))

        if is_new_device:
            points += 20.0
            findings.append(AgentFinding(
                rule_id="DEV-NEW-HARDWARE",
                rule_name="Unrecognized Device Fingerprint",
                points=20.0,
                severity="MEDIUM",
                reason="Device fingerprint has never previously authenticated this customer account.",
                evidence_ids=["DEVICE:is_new_device"],
                observed_values={"is_new": True},
            ))

        # Geographic travel velocity & impossible location jump
        from domain.services.location_velocity import evaluate_geographic_velocity
        velocity_res = evaluate_geographic_velocity(
            prev_country=prev_country,
            prev_city=prev_city,
            prev_timestamp=prev_timestamp,
            current_country=country,
            current_city=city,
            current_timestamp=current_timestamp or started_at,
        )
        if velocity_res.is_impossible_travel:
            points += velocity_res.risk_score_penalty
            findings.append(AgentFinding(
                rule_id="IMPOSSIBLE_TRAVEL_VELOCITY",
                rule_name="Impossible Travel Geographic Velocity Anomaly",
                points=velocity_res.risk_score_penalty,
                severity="CRITICAL" if velocity_res.risk_score_penalty >= 70.0 else "HIGH",
                reason=velocity_res.reason or f"Impossible physical travel velocity detected between {velocity_res.origin} and {velocity_res.destination}.",
                evidence_ids=["GEO:velocity", f"ORIGIN:{velocity_res.origin}", f"DEST:{velocity_res.destination}"],
                observed_values={
                    "origin": velocity_res.origin,
                    "destination": velocity_res.destination,
                    "distance_km": velocity_res.distance_km,
                    "elapsed_minutes": velocity_res.elapsed_minutes,
                    "speed_kmh": velocity_res.calculated_speed_kmh,
                },
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        raw_metrics = vpn_details.model_dump()
        raw_metrics["impossible_travel"] = velocity_res.is_impossible_travel
        raw_metrics["calculated_speed_kmh"] = velocity_res.calculated_speed_kmh

        return SpecialistAgentResult(
            agent_name="Device & Network Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED if provider_available else AgentExecutionStatus.DEGRADED,
            score=final_score,
            score_scale="0-100",
            raw_metrics=raw_metrics,
            findings=findings,
            points_breakdown={
                "vpn": 35.0 if is_vpn else 0.0,
                "new_device": 20.0 if is_new_device else 0.0,
                "impossible_travel": velocity_res.risk_score_penalty if velocity_res.is_impossible_travel else 0.0,
            },
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=data_quality,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 5. Graph Intelligence Agent (Neo4j)
# --------------------------------------------------------------------------- #
class GraphIntelligenceAgent:
    """Evaluates multi-hop entity sharing, syndicate rings, and mule networks."""

    @staticmethod
    def evaluate(
        shared_devices_count: int = 0,
        connected_accounts_count: int = 0,
        graph_available: bool = True,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        findings: list[AgentFinding] = []
        points = 0.0

        if not graph_available:
            return SpecialistAgentResult(
                agent_name="Graph Intelligence Agent",
                agent_version="1.0.0",
                status=AgentExecutionStatus.UNAVAILABLE,
                score=0.0,
                score_scale="0-100",
                raw_metrics={"graph_connected": False},
                findings=[],
                points_breakdown={},
                evidence_ids=[],
                data_quality=AgentDataQuality(is_sufficient=False, quality_notes="Neo4j cluster unavailable"),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
                error_code="NEO4J_UNAVAILABLE",
            )

        if shared_devices_count >= 1:
            pts = min(70.0, 30.0 + shared_devices_count * 20.0)
            points += pts
            findings.append(AgentFinding(
                rule_id="GRAPH-SHARED-DEVICE-RING",
                rule_name="Shared Device Hardware Ring",
                points=pts,
                severity="HIGH",
                reason=f"Hardware fingerprint is linked to {shared_devices_count} shared devices across {connected_accounts_count} accounts.",
                evidence_ids=["GRAPH:shared_devices"],
                observed_values={"shared_devices": shared_devices_count, "connected_accounts": connected_accounts_count},
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Graph Intelligence Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"shared_devices": shared_devices_count, "connected_accounts": connected_accounts_count},
            findings=findings,
            points_breakdown={"graph_ring_points": final_score},
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(is_sufficient=True, record_count=connected_accounts_count),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 6. ML Risk Agent (LightGBM)
# --------------------------------------------------------------------------- #
class MLRiskAgent:
    """Evaluates gradient boosted decision trees for probabilistic fraud scoring."""

    @staticmethod
    def evaluate(
        model_risk_probability: float | None = None,
        model_loaded: bool = True,
        top_features: dict[str, float] | None = None,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        if not model_loaded or model_risk_probability is None:
            return SpecialistAgentResult(
                agent_name="ML Risk Agent (LightGBM)",
                agent_version="risk_lgbm_v1",
                status=AgentExecutionStatus.UNAVAILABLE,
                score=0.0,
                score_scale="0-100",
                raw_metrics={"model_loaded": False},
                findings=[],
                points_breakdown={},
                evidence_ids=[],
                data_quality=AgentDataQuality(is_sufficient=False, quality_notes="Trained LightGBM model weights unavailable"),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
                error_code="MODEL_WEIGHTS_NOT_FOUND",
            )

        # Scale 0.0-1.0 probability to 0-100 score
        ml_score_100 = round(max(0.0, min(1.0, model_risk_probability)) * 100.0, 2)

        findings: list[AgentFinding] = []
        if ml_score_100 >= 60.0:
            findings.append(AgentFinding(
                rule_id="ML-ELEVATED-INFERENCE",
                rule_name="Elevated LightGBM Classifier Score",
                points=ml_score_100,
                severity="HIGH" if ml_score_100 >= 75.0 else "MEDIUM",
                reason=f"Machine learning model inference classified transaction at {ml_score_100:.1f}% risk.",
                evidence_ids=["MODEL:risk_lgbm_v1"],
                observed_values={"probability": model_risk_probability, "top_features": top_features or {}},
            ))

        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="ML Risk Agent (LightGBM)",
            agent_version="risk_lgbm_v1",
            status=AgentExecutionStatus.COMPLETED,
            score=ml_score_100,
            score_scale="0-100",
            raw_metrics={"probability": model_risk_probability, "top_feature_contributions": top_features or {}},
            findings=findings,
            points_breakdown={"ml_inference": ml_score_100},
            evidence_ids=["MODEL:risk_lgbm_v1"],
            data_quality=AgentDataQuality(is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 7. Merchant Intelligence Agent
# --------------------------------------------------------------------------- #
class MerchantIntelligenceAgent:
    """Evaluates merchant chargeback rates, age, and risk categories."""

    @staticmethod
    def evaluate(
        is_merchant_tx: bool = False,
        merchant_age_days: int = 365,
        chargeback_ratio: float = 0.0,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        if not is_merchant_tx:
            return SpecialistAgentResult(
                agent_name="Merchant Intelligence Agent",
                agent_version="1.0.0",
                status=AgentExecutionStatus.NOT_APPLICABLE,
                score=0.0,
                score_scale="0-100",
                raw_metrics={"is_merchant": False},
                findings=[],
                points_breakdown={},
                evidence_ids=[],
                data_quality=AgentDataQuality(is_sufficient=True, quality_notes="Not applicable for peer-to-peer customer transfers"),
                started_at=started_at,
                completed_at=datetime.now(UTC),
                duration_ms=round((time.perf_counter() - t_start) * 1000.0, 2),
            )

        points = 0.0
        findings: list[AgentFinding] = []
        if chargeback_ratio >= 0.02:
            pts = min(60.0, chargeback_ratio * 1000.0)
            points += pts
            findings.append(AgentFinding(
                rule_id="MERCH-HIGH-CHARGEBACK",
                rule_name="Elevated Merchant Chargeback Ratio",
                points=pts,
                severity="HIGH",
                reason=f"Merchant has chargeback ratio of {chargeback_ratio:.1%}, exceeding 1.5% threshold.",
                evidence_ids=["MERCH:chargeback_ratio"],
                observed_values={"chargeback_ratio": chargeback_ratio},
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Merchant Intelligence Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"chargeback_ratio": chargeback_ratio, "merchant_age_days": merchant_age_days},
            findings=findings,
            points_breakdown={"merchant_risk": final_score},
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 8. Identity and Security Agent
# --------------------------------------------------------------------------- #
class IdentitySecurityAgent:
    """Evaluates customer KYC status, failed attempts, and active security restrictions."""

    @staticmethod
    def evaluate(
        identity_status: str = "VERIFIED",
        transfer_status: str = "ACTIVE",
        has_active_restriction: bool = False,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        points = 0.0
        findings: list[AgentFinding] = []

        if has_active_restriction or transfer_status == "BLOCKED":
            points += 80.0
            findings.append(AgentFinding(
                rule_id="ID-RESTRICTION-ACTIVE",
                rule_name="Active Customer Security Restriction",
                points=80.0,
                severity="CRITICAL",
                reason="Customer account is under active transfer restrictions or administrative hold.",
                evidence_ids=["CUST:transfer_status"],
                observed_values={"transfer_status": transfer_status, "has_restriction": has_active_restriction},
            ))

        if identity_status in ("NOT_VERIFIED", "REJECTED"):
            points += 30.0
            findings.append(AgentFinding(
                rule_id="ID-KYC-INCOMPLETE",
                rule_name="Incomplete Identity Verification",
                points=30.0,
                severity="MEDIUM",
                reason="Customer national ID or KYC credentials are not formally verified.",
                evidence_ids=["CUST:identity_status"],
                observed_values={"identity_status": identity_status},
            ))

        final_score = round(min(100.0, points), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Identity & Security Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_score,
            score_scale="0-100",
            raw_metrics={"identity_status": identity_status, "transfer_status": transfer_status},
            findings=findings,
            points_breakdown={"identity_hold": final_score},
            evidence_ids=[f.evidence_ids[0] for f in findings if f.evidence_ids],
            data_quality=AgentDataQuality(is_sufficient=True),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )


# --------------------------------------------------------------------------- #
# 9. Final Decision Agent
# --------------------------------------------------------------------------- #
class FinalDecisionAgent:
    """Executes the authoritative formula calculation across all specialist agents."""

    @staticmethod
    def evaluate(
        agent_results: dict[str, SpecialistAgentResult],
        hard_restrictions_active: bool = False,
        vpn_detected: bool = False,
        is_merchant_tx: bool = False,
        customer_confirmed: bool | None = None,
    ) -> SpecialistAgentResult:
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)

        assessment: AuthoritativeRiskAssessment = calculate_final_risk_score(
            agent_results=agent_results,
            hard_restrictions_active=hard_restrictions_active,
            vpn_detected=vpn_detected,
            is_merchant_tx=is_merchant_tx,
            customer_confirmed=customer_confirmed,
        )

        findings: list[AgentFinding] = []
        for reason in assessment.hold_reasons:
            findings.append(AgentFinding(
                rule_id="POLICY-DECISION",
                rule_name="Policy Hold / Review Determination",
                points=assessment.final_score,
                severity="CRITICAL" if assessment.risk_tier == "CRITICAL" else "HIGH",
                reason=reason,
                evidence_ids=assessment.evidence_ids[:3],
                observed_values={"decision": assessment.decision.value, "tier": assessment.risk_tier.value},
            ))

        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Final Decision Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=assessment.final_score,
            score_scale="0-100",
            raw_metrics=assessment.model_dump(),
            findings=findings,
            points_breakdown={c.component: c.weighted_contribution for c in assessment.calculation},
            evidence_ids=assessment.evidence_ids,
            data_quality=AgentDataQuality(is_sufficient=assessment.assessment_confidence == "SUFFICIENT"),
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )
