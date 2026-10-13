"""Centralized, Versioned Banking Risk Rules Registry for Omerta.ai.

Defines deterministic rules for transaction security, velocity analysis, AML compliance,
network integrity (including VPN/proxy detection), and account takeover defenses.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Callable


class RuleSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RuleReferenceType(StrEnum):
    STATUTORY_REGULATION = "STATUTORY_REGULATION"
    REGULATORY_GUIDANCE = "REGULATORY_GUIDANCE"
    INTERNAL_BANKING_HEURISTIC = "INTERNAL_BANKING_HEURISTIC"
    CYBER_THREAT_INTELLIGENCE = "CYBER_THREAT_INTELLIGENCE"


@dataclass(frozen=True)
class BankingRuleDefinition:
    """Immutable specification for an executable banking risk rule."""

    rule_id: str
    version: str
    name: str
    description: str
    enabled: bool
    severity: RuleSeverity
    points: float  # Point contribution on 0-100 scale
    requires_transaction_hold: bool
    requires_customer_verification: bool
    requires_human_review: bool
    reference_type: RuleReferenceType
    regulatory_reference: str
    evidence_fields: list[str]
    missing_data_behavior: str = "TREAT_AS_SAFE"  # TREAT_AS_SAFE | TREAT_AS_UNKNOWN | TREAT_AS_FLAGGED


# --------------------------------------------------------------------------- #
# Versioned Rules Registry (16 Comprehensive Banking Risk Rules)
# --------------------------------------------------------------------------- #

BANKING_RULES_REGISTRY: dict[str, BankingRuleDefinition] = {
    # 1. Historical Amount Deviation
    "RULE-AMOUNT-DEV-001": BankingRuleDefinition(
        rule_id="RULE-AMOUNT-DEV-001",
        version="1.0.0",
        name="Historical Amount Multiplier Spike",
        description="Current transfer amount is greater than 3.0x the customer's historical 30-day average amount.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=25.0,
        requires_transaction_hold=False,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Internal Banking Risk Model DOC-OPS-001 — Outlier Amount Deviation",
        evidence_fields=["historical_average_amount", "current_amount", "amount_to_average_ratio"],
    ),

    # 2. 95th Percentile Deviation
    "RULE-AMOUNT-P95-001": BankingRuleDefinition(
        rule_id="RULE-AMOUNT-P95-001",
        version="1.0.0",
        name="95th Percentile Threshold Breach",
        description="Current transfer amount exceeds the customer's 95th percentile historical transfer value.",
        enabled=True,
        severity=RuleSeverity.MEDIUM,
        points=15.0,
        requires_transaction_hold=False,
        requires_customer_verification=False,
        requires_human_review=False,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Internal Operational Baselines — Upper Decile Breach",
        evidence_fields=["historical_p95_amount", "current_amount"],
    ),

    # 3. 5-Minute Velocity Spike
    "RULE-VEL-5M": BankingRuleDefinition(
        rule_id="RULE-VEL-5M",
        version="1.0.0",
        name="Rapid 5-Minute Velocity Burst",
        description="Three or more transactions dispatched within a rolling 5-minute lookback window.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=30.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Guidance on Financial Investigations R.10 / R.20 — Rapid Velocity",
        evidence_fields=["previous_transactions_5m", "outgoing_total_5m"],
    ),

    # 4. 15-Minute Aggregation
    "RULE-VEL-15M": BankingRuleDefinition(
        rule_id="RULE-VEL-15M",
        version="1.0.0",
        name="15-Minute Volume Escalation",
        description="Five or more transactions within 15 minutes, or total 15m volume exceeding 40,000 EGP.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=25.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Typologies on Automated Cash-Outs",
        evidence_fields=["previous_transactions_15m", "outgoing_total_15m"],
    ),

    # 5. 60-Minute Velocity
    "RULE-VEL-60M": BankingRuleDefinition(
        rule_id="RULE-VEL-60M",
        version="1.0.0",
        name="60-Minute Frequency Anomaly",
        description="Eight or more transactions within a 60-minute rolling window.",
        enabled=True,
        severity=RuleSeverity.MEDIUM,
        points=20.0,
        requires_transaction_hold=False,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Internal Fraud Policy — High Frequency Retail Flow",
        evidence_fields=["previous_transactions_60m", "outgoing_total_60m"],
    ),

    # 6. Rapid Cash-out
    "RULE-CASHOUT-001": BankingRuleDefinition(
        rule_id="RULE-CASHOUT-001",
        version="1.0.0",
        name="Rapid Inflow-to-Outflow Cash-Out",
        description="Incoming deposit or transfer followed by an immediate draining outflow within 30 minutes.",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=40.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Money Laundering Typologies — Pass-through / Mule Transit Account",
        evidence_fields=["incoming_total_30d", "current_amount", "available_balance"],
    ),

    # 7. Beneficiary Risk (New Recipient with High Value)
    "RULE-BENEF-001": BankingRuleDefinition(
        rule_id="RULE-BENEF-001",
        version="1.0.0",
        name="High-Value First-Time Beneficiary Transfer",
        description="Transfer exceeding 20,000 EGP directed to a beneficiary never previously transacted with.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=25.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Anti-Fraud Counterparty Governance — Untrusted Destination Hold",
        evidence_fields=["is_first_transaction_with_beneficiary", "current_amount"],
    ),

    # 8. Beneficiary Concentration
    "RULE-BENEF-CONC": BankingRuleDefinition(
        rule_id="RULE-BENEF-CONC",
        version="1.0.0",
        name="Unusual Beneficiary Concentration",
        description="Sudden surge of multiple distinct new beneficiaries added and funded within 24 hours.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=30.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Mule Ring Typologies — Dispersal to Multiple New Accounts",
        evidence_fields=["distinct_beneficiaries_count", "previous_transactions_24h"],
    ),

    # 9. Account Takeover (ATO) Chain
    "RULE-ATO-001": BankingRuleDefinition(
        rule_id="RULE-ATO-001",
        version="1.0.0",
        name="Account Takeover (ATO) Multi-Event Chain",
        description="Password reset, login failure, or MFA change followed by high-value transfer within 2 hours.",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=50.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.CYBER_THREAT_INTELLIGENCE,
        regulatory_reference="NIST SP 800-63B & FATF Digital Identity Guidance — Credential Compromise Chain",
        evidence_fields=["ato_events", "time_since_last_security_change"],
    ),

    # 10. New Device Identifier
    "RULE-DEV-NEW": BankingRuleDefinition(
        rule_id="RULE-DEV-NEW",
        version="1.0.0",
        name="Unrecognized Hardware Device Fingerprint",
        description="Transaction initiated from a hardware device fingerprint never previously associated with customer.",
        enabled=True,
        severity=RuleSeverity.MEDIUM,
        points=15.0,
        requires_transaction_hold=False,
        requires_customer_verification=False,
        requires_human_review=False,
        reference_type=RuleReferenceType.CYBER_THREAT_INTELLIGENCE,
        regulatory_reference="Device Telemetry Standards — Unregistered Endpoint",
        evidence_fields=["is_new_device", "device_id"],
    ),

    # 11. Commercial VPN / Proxy Observed (Additional Requirement 1)
    "RULE-NETWORK-VPN-001": BankingRuleDefinition(
        rule_id="RULE-NETWORK-VPN-001",
        version="1.0.0",
        name="Commercial VPN / Proxy Anonymizer Detected",
        description="Session network intelligence indicates origin via commercial VPN, datacenter proxy, or anonymizer.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=30.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=False,
        reference_type=RuleReferenceType.CYBER_THREAT_INTELLIGENCE,
        regulatory_reference="Omerta Network Security Policy — Mandatory Customer Identity Confirmation for VPN Transfers",
        evidence_fields=["vpn_detected", "proxy_detected", "detection_provider", "ip_risk_score"],
    ),

    # 12. Geographic Anomaly / Impossible Travel
    "RULE-GEO-TRAVEL-001": BankingRuleDefinition(
        rule_id="RULE-GEO-TRAVEL-001",
        version="1.0.0",
        name="Impossible Geographic Velocity",
        description="Sequential transactions from distinct countries requiring physically impossible travel velocity (> 800 km/h).",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=45.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.CYBER_THREAT_INTELLIGENCE,
        regulatory_reference="Geographic Anomaly Telemetry — Impossible Travel Attack Indicator",
        evidence_fields=["prev_country", "current_country", "calculated_speed_kmh"],
    ),

    # 13. Shared Device Syndicate / Device Ring
    "RULE-DEV-RING": BankingRuleDefinition(
        rule_id="RULE-DEV-RING",
        version="1.0.0",
        name="Multi-Account Shared Hardware Syndicate",
        description="Device identifier is shared across 2 or more distinct customer accounts within Neo4j topology.",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=40.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Typologies on Cyber-Enabled Crime — Multi-Account Hardware Sharing",
        evidence_fields=["shared_device_count", "connected_accounts_count"],
    ),

    # 14. Cash Structuring / Smurfing
    "RULE-STR-001": BankingRuleDefinition(
        rule_id="RULE-STR-001",
        version="1.0.0",
        name="Statutory Reporting Threshold Evasion (Structuring)",
        description="Transfer amount placed directly below the 50,000 EGP statutory AML reporting limit (45k - 49.9k EGP).",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=35.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.STATUTORY_REGULATION,
        regulatory_reference="FATF Recommendation 20 & AML Law 80/2002 — Structured Reporting Threshold Evasion",
        evidence_fields=["current_amount"],
    ),

    # 15. Failed Authentication / Password Lockout
    "RULE-AUTH-FAIL": BankingRuleDefinition(
        rule_id="RULE-AUTH-FAIL",
        version="1.0.0",
        name="Excessive Failed Authentication Attempts",
        description="Customer or account has recorded 3 or more failed transfer password or authentication attempts.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=30.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Identity & Access Governance — Authentication Lockout",
        evidence_fields=["transfer_failed_attempts"],
    ),

    # 16. Active Account Privilege Restriction
    "RULE-RESTRICT-001": BankingRuleDefinition(
        rule_id="RULE-RESTRICT-001",
        version="1.0.0",
        name="Active Security Restriction Hold",
        description="Customer account is subject to an active OUTGOING_TRANSFERS_ONLY or administrative restriction.",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=100.0,
        requires_transaction_hold=True,
        requires_customer_verification=False,
        requires_human_review=True,
        reference_type=RuleReferenceType.INTERNAL_BANKING_HEURISTIC,
        regulatory_reference="Internal Security Governance — Server-Enforced Transfer Restriction",
        evidence_fields=["restriction_id", "restriction_scope"],
    ),

    # 17. High-Value Transfer Threshold Exceeded
    "RULE-HIGH-VALUE": BankingRuleDefinition(
        rule_id="RULE-HIGH-VALUE",
        version="1.0.0",
        name="High-Value Transfer Threshold Exceeded",
        description="Transfer amount exceeds 50,000 EGP statutory threshold, or exceeds 10,000 EGP on a newly registered account (< 14 days).",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=45.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.STATUTORY_REGULATION,
        regulatory_reference="Anti-Fraud High-Value Escalation Directive — Mandatory Customer Authorization Hold",
        evidence_fields=["current_amount", "account_age_days"],
    ),

    # 18. Rapid Multi-Source Inflow Funnel (Mule Collector)
    "RULE-MULE-COLLECTOR-001": BankingRuleDefinition(
        rule_id="RULE-MULE-COLLECTOR-001",
        version="1.0.0",
        name="Rapid Multi-Source Inflow Funnel (Mule Collector)",
        description="Beneficiary account received transfers from 2 or more distinct accounts in a 15-minute window, indicative of rapid mule fund aggregation.",
        enabled=True,
        severity=RuleSeverity.CRITICAL,
        points=50.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF Typologies on Digital Money Mules & Aggregation Nodes",
        evidence_fields=["recipient_distinct_senders_15m", "recipient_incoming_count_15m"],
    ),

    # 19. Rapid Velocity Burst Security Hold
    "RULE-VEL-BURST-HOLD": BankingRuleDefinition(
        rule_id="RULE-VEL-BURST-HOLD",
        version="1.0.0",
        name="Rapid Velocity Burst Security Hold",
        description="Account dispatched 2 or more transactions within 5 minutes or 4 or more within 15 minutes, triggering mandatory customer verification hold.",
        enabled=True,
        severity=RuleSeverity.HIGH,
        points=35.0,
        requires_transaction_hold=True,
        requires_customer_verification=True,
        requires_human_review=True,
        reference_type=RuleReferenceType.REGULATORY_GUIDANCE,
        regulatory_reference="FATF High-Velocity Rapid Dispatch Monitoring",
        evidence_fields=["previous_transactions_5m", "previous_transactions_15m"],
    ),
}


def get_rule(rule_id: str) -> BankingRuleDefinition | None:
    """Retrieve a rule definition by its unique identifier."""
    return BANKING_RULES_REGISTRY.get(rule_id)


def list_rules() -> list[BankingRuleDefinition]:
    """Return all defined banking risk rules in the registry."""
    return list(BANKING_RULES_REGISTRY.values())
