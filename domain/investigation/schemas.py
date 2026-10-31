"""Schemas for Evidence-Based Account Investigation & Risk Reporting.

Defines typed Pydantic contracts for:
- Investigation requests & authorizations
- Verified account & transaction facts
- Behavioral metrics & rolling window metrics
- Deterministic banking rule alerts with regulatory references
- ML model prediction outputs and evaluation metadata
- Graph intelligence findings and shared entity indicators
- Aggregated evidence items with SHA-256 provenance locators
- Final comprehensive forensic investigation report
"""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


class InvestigationReason(StrEnum):
    ROUTINE_MONITORING = "ROUTINE_MONITORING"
    HIGH_VELOCITY_ALERT = "HIGH_VELOCITY_ALERT"
    AMOUNT_ESCALATION = "AMOUNT_ESCALATION"
    NEW_DEVICE_IP = "NEW_DEVICE_IP"
    UNUSUAL_HOURS = "UNUSUAL_HOURS"
    SUSPICIOUS_MULE_PATTERN = "SUSPICIOUS_MULE_PATTERN"
    SHARED_DEVICE_RING = "SHARED_DEVICE_RING"
    MANUAL_OFFICER_REQUEST = "MANUAL_OFFICER_REQUEST"


class RuleSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PipelineStageStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    SKIPPED = "SKIPPED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class PipelineStageTrace(BaseModel):
    """Execution trace of an individual LangGraph workflow stage."""
    stage_id: str
    stage_name: str
    description: str
    source_tier: str  # PostgreSQL, Neo4j, LightGBM, Banking Rules, Evidence Aggregator, LLM Synthesis, Persistence
    status: PipelineStageStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None


class RecommendedReviewAction(StrEnum):
    ROUTINE_MONITORING = "ROUTINE_MONITORING"
    REQUEST_CUSTOMER_INFO = "REQUEST_CUSTOMER_INFO"
    ENHANCED_DUE_DILIGENCE = "ENHANCED_DUE_DILIGENCE"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    ESCALATE_TO_FIU = "ESCALATE_TO_FIU"
    FREEZE_RECOMMENDATION = "FREEZE_RECOMMENDATION"
    HOLD_FOR_CUSTOMER_VERIFICATION = "HOLD_FOR_CUSTOMER_VERIFICATION"
    MANUAL_COMPLIANCE_REVIEW = "MANUAL_COMPLIANCE_REVIEW"
    RESTRICT_AND_INVESTIGATE = "RESTRICT_AND_INVESTIGATE"


class AccountInvestigationRequest(BaseModel):
    """Input parameters for account forensic investigation."""
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1, max_length=64, description="Target Account External ID (e.g. ACC-0001)")
    time_range_days: int = Field(default=30, ge=1, le=365, description="Lookback window in days")
    investigation_reason: InvestigationReason = Field(default=InvestigationReason.MANUAL_OFFICER_REQUEST)
    reason_notes: str | None = Field(default=None, max_length=500)
    persist: bool = Field(default=False, description="Whether to persist as formal case file")

    @field_validator("account_id")
    @classmethod
    def validate_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("account_id cannot be blank")
        return s


class TransactionInvestigationRequest(BaseModel):
    """Input parameters for a transaction-specific forensic investigation."""
    model_config = ConfigDict(extra="forbid")

    transaction_id: str = Field(min_length=1, max_length=64, description="Target Transaction External ID (e.g. TXN-SIM-A141F922)")
    account_id: str | None = Field(default=None, max_length=64, description="Optional associated account ID if known")
    time_range_days: int = Field(default=30, ge=1, le=365, description="Lookback window for account behavioral baseline")
    investigation_reason: InvestigationReason = Field(default=InvestigationReason.MANUAL_OFFICER_REQUEST)
    reason_notes: str | None = Field(default=None, max_length=500)
    persist: bool = Field(default=True, description="Whether to persist as formal case file")

    @field_validator("transaction_id")
    @classmethod
    def validate_not_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("transaction_id cannot be blank")
        return s


class TransactionFact(BaseModel):
    """Verified transaction record with explicit decimal amount and timestamp."""
    transaction_id: str
    external_id: str
    timestamp: datetime
    amount: Decimal
    currency: str
    transaction_type: str
    status: str
    recipient_account_id: str | None = None
    recipient_name: str | None = None
    device_id: str | None = None
    ip_address: str | None = None
    is_new_device: bool = False
    is_new_ip: bool = False
    risk_score: float | None = None
    risk_level: str | None = None
    is_vpn: bool = False


class AccountFacts(BaseModel):
    """Authoritative account details from PostgreSQL ledger."""
    account_id: str
    customer_id: str
    customer_name: str
    customer_email: str | None = None
    omerta_user_number: str | None = None
    account_type: str
    status: str
    currency: str
    ledger_balance: Decimal
    available_balance: Decimal
    risk_level: str
    created_at: datetime
    verified_identity: bool = False
    is_sandbox: bool = False


class VelocityWindowMetric(BaseModel):
    """Rolling velocity calculations over a specific time window."""
    window_minutes: int
    count: int
    total_amount: Decimal
    max_single_amount: Decimal
    window_start: datetime | None = None
    window_end: datetime | None = None


class BehavioralMetrics(BaseModel):
    """Deterministic transaction behavior and risk metrics."""
    total_transactions: int
    withdrawal_count: int
    withdrawal_volume: Decimal
    deposit_count: int
    deposit_volume: Decimal
    net_flow: Decimal
    average_withdrawal_amount: Decimal
    median_withdrawal_amount: Decimal
    max_withdrawal_amount: Decimal
    min_withdrawal_amount: Decimal
    
    # Rolling velocity metrics
    velocity_5m_max_count: int = 0
    velocity_5m_max_volume: Decimal = Decimal("0.00")
    velocity_15m_max_count: int = 0
    velocity_15m_max_volume: Decimal = Decimal("0.00")
    velocity_60m_max_count: int = 0
    velocity_60m_max_volume: Decimal = Decimal("0.00")

    # Escalation detection
    has_amount_escalation: bool = False
    escalation_sequences: list[list[float]] = Field(default_factory=list)

    # Status counts
    completed_count: int = 0
    failed_count: int = 0
    reversed_count: int = 0
    pending_count: int = 0

    # Temporal anomalies
    off_hours_count: int = 0  # Activity between 01:00 and 05:00
    weekend_count: int = 0

    # Ledger reconciliation
    ledger_reconciled: bool = True
    ledger_discrepancy: Decimal = Decimal("0.00")


class RuleReferenceType(StrEnum):
    STATUTORY_REGULATION = "STATUTORY_REGULATION"          # Legal/statutory obligation (e.g. FATF R.20 STR mandate)
    REGULATORY_GUIDANCE = "REGULATORY_GUIDANCE"            # External international guidance & red flags (e.g. FATF R.10 / Typologies)
    INTERNAL_BANKING_HEURISTIC = "INTERNAL_BANKING_HEURISTIC" # Internal bank operations policy & session rules (e.g. DOC-OPS-001)


class TriggeredRuleAlert(BaseModel):
    """Explainable deterministic banking rule alert with regulatory taxonomy."""
    rule_id: str
    rule_name: str
    severity: RuleSeverity
    reference_type: RuleReferenceType = RuleReferenceType.REGULATORY_GUIDANCE
    regulatory_reference: str  # e.g. "FATF Guidance R.10 / R.20"
    applicable_window: str
    observed_values: dict[str, Any]
    threshold_value: dict[str, Any]
    explanation: str
    evidence_references: list[str] = Field(default_factory=list)


class MLRiskOutput(BaseModel):
    """LightGBM machine learning risk prediction output and evaluation metadata."""
    model_version: str
    feature_version: str
    model_source: str = "LIGHTGBM_CLASSIFIER"
    risk_score: float  # Uncalibrated model output 0.0 - 1.0
    risk_tier: str  # LOW, MEDIUM, HIGH
    explanation_method: str = "ACTIVE_FEATURE_GAIN_IMPORTANCE"  # Honest documentation: model-native global split gain over active features, not SHAP
    top_feature_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="Renormalized tree gain importance across active features (model-native, not Shapley attribution)",
    )
    model_evaluation_metrics: dict[str, Any] = Field(default_factory=dict)
    features_complete: bool = True
    missing_features: list[str] = Field(default_factory=list)
    model_loaded: bool = True
    error_message: str | None = None


class GraphIntelligenceOutput(BaseModel):
    """Neo4j graph structural relationships and network indicators."""
    available: bool = True
    shared_device_count: int = 0
    shared_devices: list[dict[str, Any]] = Field(default_factory=list)
    shared_ip_count: int = 0
    shared_ips: list[dict[str, Any]] = Field(default_factory=list)
    connected_accounts_count: int = 0
    connected_accounts: list[dict[str, Any]] = Field(default_factory=list)
    fraud_ring_detected: bool = False
    fraud_ring_details: dict[str, Any] = Field(default_factory=dict)
    graph_disclaimer: str = "Graph connectivity represents structural association and does not constitute confirmation of illicit activity."


class SimulatedWithdrawalRequest(BaseModel):
    """Sandbox-only simulated withdrawal operation."""
    model_config = ConfigDict(extra="forbid")

    account_id: str = Field(min_length=1, max_length=64)
    amount: Decimal = Field(gt=Decimal("0.00"), le=Decimal("1000000.00"))
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    recipient_account_id: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=128)
    note: str = Field(default="Sandbox test withdrawal", max_length=256)
    is_sandbox_confirmed: bool = Field(default=True, description="Explicit confirmation of sandbox environment")


class SimulatedWithdrawalResponse(BaseModel):
    """Result of sandbox simulated withdrawal."""
    success: bool
    transaction_id: str
    account_id: str
    amount: Decimal
    currency: str
    new_balance: Decimal
    status: str
    idempotency_key: str
    timestamp: datetime
    audit_event_id: str
    triggered_rules: list[str] = Field(default_factory=list)
    risk_score: float | None = None
    message: str


class AccountInvestigationReport(BaseModel):
    """Comprehensive, structured forensic investigation report."""
    investigation_id: str
    account_id: str
    time_range_days: int
    generated_at: datetime
    caller_role: str
    investigation_reason: str

    # Transaction-Specific Investigation Context (when investigating a transaction)
    transaction_id: str | None = None
    target_transaction: TransactionFact | None = None
    preceding_transactions: list[TransactionFact] = Field(default_factory=list)
    subsequent_transactions: list[TransactionFact] = Field(default_factory=list)

    # 1. Executive Summary
    executive_summary: str

    # 2. Verified Account & Transaction Facts
    account_facts: AccountFacts | None = None
    transaction_facts_count: int = 0
    recent_transactions: list[TransactionFact] = Field(default_factory=list)

    # 3. Behavioral Metrics
    behavioral_metrics: BehavioralMetrics

    # 4. Triggered Banking Rules
    triggered_rules: list[TriggeredRuleAlert] = Field(default_factory=list)
    rules_score: float = 0.0  # 0.0 - 1.0

    # 5. ML Risk Result
    ml_risk: MLRiskOutput

    # 6. Combined Risk Score & Thresholds
    combined_risk_score: float = 0.0
    operational_alert_threshold: float = 0.40  # Documented configurable app threshold
    threshold_exceeded: bool = False
    threshold_rationale: str = "Configured application alert threshold of 0.40 (40%) triggers mandatory multi-eye compliance officer review."

    # 7. Neo4j Graph Relationships
    graph_intelligence: GraphIntelligenceOutput

    # 8. LLM Synthesis & Explanations
    risk_assessment_explanation: str
    factor_explanations: list[str] = Field(default_factory=list)
    forensic_report_markdown: str | None = None

    # 9. Data Limitations & Missing Data
    missing_data_and_limitations: list[str] = Field(default_factory=list)

    # 10. Human Reviewer Recommendations
    recommended_action: RecommendedReviewAction
    recommended_action_justification: str

    # 11. Audit Trail, Provenance & Execution Pipeline Stages
    evidence_ids: list[str] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    charts: list[dict[str, Any]] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    pipeline_stages: list[PipelineStageTrace] = Field(default_factory=list)
    evaluation: dict[str, Any] | None = None
