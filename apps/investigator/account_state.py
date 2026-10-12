"""State schema for Account Forensic Investigation LangGraph workflow."""

from datetime import datetime
from typing import Annotated, Any
import operator
from pydantic import BaseModel, Field

from domain.investigation.schemas import (
    AccountFacts,
    BehavioralMetrics,
    GraphIntelligenceOutput,
    MLRiskOutput,
    PipelineStageTrace,
    RecommendedReviewAction,
    SimulatedWithdrawalResponse,
    TransactionFact,
    TriggeredRuleAlert,
)


def _merge_dict(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    return {**left, **right}


class AccountInvestigationState(BaseModel):
    """Serializable snapshot of an account- or transaction-level investigation workflow."""

    # Request inputs
    account_id: str
    transaction_id: str | None = None
    time_range_days: int = 30
    investigation_reason: str = "MANUAL_OFFICER_REQUEST"
    caller_role: str = "INVESTIGATOR"
    caller_id: str | None = None
    persist: bool = False

    # Workflow lifecycle
    investigation_id: str = ""
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    error_message: str | None = None

    # Node data payloads
    account_facts: AccountFacts | None = None
    target_transaction: TransactionFact | None = None
    transaction_facts: list[TransactionFact] = Field(default_factory=list)
    preceding_transactions: list[TransactionFact] = Field(default_factory=list)
    subsequent_transactions: list[TransactionFact] = Field(default_factory=list)
    behavioral_metrics: BehavioralMetrics | None = None
    triggered_rules: list[TriggeredRuleAlert] = Field(default_factory=list)
    rules_score: float = 0.0

    ml_risk: MLRiskOutput | None = None
    graph_intelligence: GraphIntelligenceOutput | None = None

    combined_risk_score: float = 0.0
    threshold_exceeded: bool = False
    recommended_action: RecommendedReviewAction = RecommendedReviewAction.ROUTINE_MONITORING
    recommended_action_justification: str = ""

    # Report & LLM outputs
    executive_summary: str = ""
    risk_assessment_explanation: str = ""
    factor_explanations: list[str] = Field(default_factory=list)
    missing_data_and_limitations: list[str] = Field(default_factory=list)
    forensic_report_markdown: str = ""

    # Provenance, Stages & Audit
    pipeline_stages: Annotated[list[PipelineStageTrace], operator.add] = []
    evidence_ids: Annotated[list[str], operator.add] = []
    audit_events: Annotated[list[dict[str, Any]], operator.add] = []
    charts: list[dict[str, Any]] = Field(default_factory=list)
    node_timings_ms: Annotated[dict[str, float], _merge_dict] = {}
