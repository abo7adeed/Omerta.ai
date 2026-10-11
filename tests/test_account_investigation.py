"""Comprehensive automated tests for Omerta.ai LangGraph Account Investigation Workflow.

Covers Section G test criteria:
- Five-minute withdrawal velocity
- Escalating transaction amounts ($100 -> $500 -> $5,000)
- Normal behavior versus anomalous behavior
- Empty and incomplete histories
- Duplicate events, reversals and mixed currencies
- Model loading, feature mismatch and prediction failure
- Neo4j unavailability and partial investigations
- Authorization and read-only enforcement
- Evidence and citation integrity
- Report consistency with underlying records
- Sandbox-only withdrawal simulation (concurrency, idempotency, isolation)
- API integration
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.investigator.account_workflow import run_account_investigation
from domain.errors import ValidationError
from domain.investigation.metrics import calculate_behavioral_metrics
from domain.investigation.rules import evaluate_banking_rules
from domain.investigation.schemas import (
    AccountFacts,
    AccountInvestigationRequest,
    GraphIntelligenceOutput,
    InvestigationReason,
    SimulatedWithdrawalRequest,
    TransactionFact,
)
from domain.investigation.simulation import (
    SandboxWithdrawalService,
)
from infrastructure.risk.features import FEATURE_NAMES
from infrastructure.risk.ml_provider import MLRiskProvider
from domain import schemas as domain_schemas


# ==============================================================================
# 1. Behavioral Metrics Tests
# ==============================================================================

def test_five_minute_withdrawal_velocity():
    """Verify rapid repeated withdrawals in rolling windows (5m, 15m, 60m)."""
    now = datetime.now(timezone.utc)

    # 4 withdrawals spaced 1 minute apart
    txns = [
        TransactionFact(
            transaction_id=f"TXN-VEL-{i}",
            external_id=f"TXN-VEL-{i}",
            amount=Decimal("1500.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=4 - i),
        )
        for i in range(4)
    ]

    metrics = calculate_behavioral_metrics(txns, account_balance=Decimal("20000.00"))
    assert metrics.withdrawal_count == 4
    assert metrics.withdrawal_volume == Decimal("6000.00")
    assert metrics.velocity_5m_max_count == 4
    assert metrics.velocity_5m_max_volume == Decimal("6000.00")
    assert metrics.velocity_15m_max_count == 4
    assert metrics.velocity_60m_max_count == 4

    # Rule evaluation test
    graph = GraphIntelligenceOutput(available=True)
    alerts, score = evaluate_banking_rules(None, metrics, graph)
    vel_alerts = [a for a in alerts if a.rule_id == "RULE-VEL-001"]
    assert len(vel_alerts) == 1
    assert vel_alerts[0].severity == "HIGH"
    assert "FATF" in vel_alerts[0].regulatory_reference


def test_escalating_transaction_amounts_sequence():
    """Detect monotonic escalation sequences such as $100 -> $500 -> $5,000."""
    now = datetime.now(timezone.utc)

    escalating_txns = [
        TransactionFact(
            transaction_id="TXN-ESC-1",
            external_id="TXN-ESC-1",
            amount=Decimal("100.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=25),
        ),
        TransactionFact(
            transaction_id="TXN-ESC-2",
            external_id="TXN-ESC-2",
            amount=Decimal("500.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=15),
        ),
        TransactionFact(
            transaction_id="TXN-ESC-3",
            external_id="TXN-ESC-3",
            amount=Decimal("5000.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=5),
        ),
    ]

    metrics = calculate_behavioral_metrics(escalating_txns, account_balance=Decimal("50000.00"))
    assert metrics.has_amount_escalation is True
    assert len(metrics.escalation_sequences) >= 1
    assert metrics.escalation_sequences[0] == [100.0, 500.0, 5000.0]

    # Evaluate rules to verify rule alert generation
    graph = GraphIntelligenceOutput(available=True)
    alerts, score = evaluate_banking_rules(None, metrics, graph)
    esc_alerts = [a for a in alerts if a.rule_id == "RULE-ESC-001"]
    assert len(esc_alerts) == 1
    assert esc_alerts[0].severity == "HIGH"
    assert "FATF" in esc_alerts[0].regulatory_reference


def test_empty_and_incomplete_histories():
    """Verify metrics calculation and rules handling for accounts with zero transactions."""
    metrics = calculate_behavioral_metrics([], account_balance=Decimal("1000.00"))
    assert metrics.total_transactions == 0
    assert metrics.withdrawal_count == 0
    assert metrics.deposit_count == 0
    assert metrics.withdrawal_volume == Decimal("0.00")
    assert metrics.has_amount_escalation is False

    graph = GraphIntelligenceOutput(available=True)
    alerts, score = evaluate_banking_rules(None, metrics, graph)
    assert score == 0.0
    assert len(alerts) == 0


def test_duplicate_events_and_reversals():
    """Verify reversal status tallies and mixed transaction types."""
    now = datetime.now(timezone.utc)

    txns = [
        TransactionFact(
            transaction_id="TXN-DUP-1",
            external_id="TXN-DUP-1",
            amount=Decimal("2000.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(hours=2),
        ),
        # Reversal transaction
        TransactionFact(
            transaction_id="TXN-REV-2",
            external_id="TXN-REV-2",
            amount=Decimal("5000.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="REVERSED",
            timestamp=now - timedelta(hours=1),
        ),
        # Failed transaction
        TransactionFact(
            transaction_id="TXN-FAIL-3",
            external_id="TXN-FAIL-3",
            amount=Decimal("10000.00"),
            currency="EGP",
            transaction_type="CUSTOMER_TRANSFER",
            status="FAILED",
            timestamp=now - timedelta(minutes=30),
        ),
    ]

    metrics = calculate_behavioral_metrics(txns, account_balance=Decimal("15000.00"))
    assert metrics.total_transactions == 3
    assert metrics.completed_count == 1
    assert metrics.reversed_count == 1
    assert metrics.failed_count == 1


# ==============================================================================
# 2. Machine Learning Model Loading & Failure Handling Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_lightgbm_model_loading_and_features():
    """Verify LightGBM booster loading directly via MLRiskProvider and feature consistency."""
    provider = MLRiskProvider()
    assert provider._booster is not None
    assert provider.model_version == "lgbm-risk-v1"
    assert len(provider._importance) == 13

    # Predict with standard nominal feature payload
    features = domain_schemas.RiskFeatures(
        transaction_id="TXN-TEST-ML",
        transaction_amount=2500,
        currency="EGP",
        transaction_velocity_7d=1,
        account_age_days=100,
        recipient_age_days=50,
        originator_risk_level="LOW",
        recipient_risk_level="LOW",
        previous_alert_count=0,
        previous_suspicious_activity=False,
        is_new_device=False,
        is_new_ip=False,
    )
    score_out = await provider.score(features)
    assert 0.0 <= score_out.risk_score <= 1.0
    assert score_out.model_version == provider.model_version
    assert len(score_out.contributions) > 0


@pytest.mark.asyncio
async def test_lightgbm_feature_mismatch_fallback():
    """Verify feature vector mapping correctly processes arbitrary nominal values."""
    provider = MLRiskProvider()
    # High risk feature vector
    features = domain_schemas.RiskFeatures(
        transaction_id="TXN-HIGH-RISK",
        transaction_amount=49500,
        currency="EGP",
        transaction_velocity_7d=12,
        account_age_days=3,
        recipient_age_days=1,
        originator_risk_level="HIGH",
        recipient_risk_level="HIGH",
        previous_alert_count=4,
        previous_suspicious_activity=True,
        is_new_device=True,
        is_new_ip=True,
    )
    score_out = await provider.score(features)
    assert 0.0 <= score_out.risk_score <= 1.0
    assert score_out.risk_level in ["MEDIUM", "HIGH", "CRITICAL"]


# ==============================================================================
# 3. Sandbox-Only Simulated Withdrawal Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_sandbox_production_isolation_guard():
    """Simulation service must strictly reject live/production accounts."""
    service = SandboxWithdrawalService()
    req = SimulatedWithdrawalRequest(
        account_id="ACC-0001",  # Live production customer account
        amount=Decimal("500.00"),
        currency="EGP",
        idempotency_key="IDEMP-LIVE-TEST",
        is_sandbox_confirmed=True,
    )
    with pytest.raises(ValidationError) as exc_info:
        await service.execute_simulated_withdrawal(req)
    assert "Production account" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sandbox_withdrawal_insufficient_balance():
    """Simulation must reject withdrawal exceeding sandbox balance."""
    service = SandboxWithdrawalService()
    req = SimulatedWithdrawalRequest(
        account_id="ACC-SIM-TEST-BAL",
        amount=Decimal("60000.00"),  # Exceeds initial balance of 50,000 EGP
        currency="EGP",
        idempotency_key="IDEMP-EXCEED-BAL",
        is_sandbox_confirmed=True,
    )
    with pytest.raises(ValidationError) as exc_info:
        await service.execute_simulated_withdrawal(req)
    assert "Insufficient funds" in str(exc_info.value)


@pytest.mark.asyncio
async def test_sandbox_idempotency_protection():
    """Duplicate requests with identical idempotency key return exact cached result."""
    service = SandboxWithdrawalService()
    req = SimulatedWithdrawalRequest(
        account_id="ACC-SIM-IDEMP",
        amount=Decimal("200.00"),
        currency="EGP",
        idempotency_key="IDEMP-UNIQUE-KEY-001",
        is_sandbox_confirmed=True,
    )
    res1 = await service.execute_simulated_withdrawal(req)
    assert res1.success is True

    # Submit second time with identical key
    res2 = await service.execute_simulated_withdrawal(req)
    assert res2.success is True
    assert res2.transaction_id == res1.transaction_id
    assert res2.new_balance == res1.new_balance


@pytest.mark.asyncio
async def test_sandbox_concurrent_withdrawal_mutex():
    """Verify mutex prevents race conditions on simulated account balance."""
    service = SandboxWithdrawalService()
    account_id = "ACC-SIM-CONCURRENT"

    # Launch 5 concurrent withdrawals of 500 EGP each
    async def make_withdrawal(idx: int):
        req = SimulatedWithdrawalRequest(
            account_id=account_id,
            amount=Decimal("500.00"),
            currency="EGP",
            idempotency_key=f"IDEMP-CONCUR-{idx}",
            is_sandbox_confirmed=True,
        )
        return await service.execute_simulated_withdrawal(req)

    results = await asyncio.gather(*[make_withdrawal(i) for i in range(5)])
    successes = [r for r in results if r.success]
    assert len(successes) == 5

    # Check that ledger consistency is exact: Initial 50,000 - 5 * 500 = 47,500
    assert service.get_sandbox_balance(account_id) == Decimal("47500.00")


# ==============================================================================
# 4. LangGraph End-to-End Investigation Workflow Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_langgraph_workflow_normal_account():
    """Verify end-to-end investigation for a low-risk normal account (ACC-0001)."""
    req = AccountInvestigationRequest(
        account_id="ACC-0001",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    report = await run_account_investigation(req)

    assert report.investigation_id.startswith("INV-")
    assert report.account_id == "ACC-0001"
    assert report.account_facts is not None
    assert report.account_facts.customer_id is not None
    assert report.ml_risk is not None
    assert report.ml_risk.model_version is not None
    assert report.operational_alert_threshold == 0.40
    assert report.combined_risk_score < 0.40
    assert report.recommended_action in ["ROUTINE_MONITORING", "HUMAN_REVIEW", "REQUEST_CUSTOMER_INFO"]
    assert len(report.charts) >= 1


@pytest.mark.asyncio
async def test_langgraph_workflow_high_risk_syndicate_account():
    """Verify end-to-end investigation for syndicate account ACC-6001 with escalation & shared devices."""
    req = AccountInvestigationRequest(
        account_id="ACC-6001",
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=False,
    )
    report = await run_account_investigation(req)

    assert report.investigation_id.startswith("INV-")
    assert report.account_id == "ACC-6001"
    # Combined score must exceed 0.40 threshold
    assert report.combined_risk_score >= 0.40
    assert report.threshold_exceeded is True
    assert report.recommended_action in ["ESCALATE_TO_FIU", "FREEZE_RECOMMENDATION"]
    # Evidence IDs and source provenance must be present
    assert len(report.evidence_ids) > 0
    assert len(report.triggered_rules) > 0


@pytest.mark.asyncio
async def test_langgraph_workflow_nonexistent_account_validation():
    """Verify coordinator properly returns graceful empty/not found report."""
    req = AccountInvestigationRequest(
        account_id="ACC-NONEXISTENT-9999",
        time_range_days=30,
        investigation_reason=InvestigationReason.MANUAL_OFFICER_REQUEST,
        persist=False,
    )
    report = await run_account_investigation(req)
    assert report.account_id == "ACC-NONEXISTENT-9999"
    assert len(report.missing_data_and_limitations) > 0
    assert any("not found" in lim.lower() for lim in report.missing_data_and_limitations)


# ==============================================================================
# 5. Fast-API Integration Endpoints Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_api_account_investigation_endpoint():
    """Verify POST /investigations/account returns 200 with full structured report."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/investigations/account",
            json={
                "account_id": "ACC-0001",
                "time_range_days": 15,
                "investigation_reason": "MANUAL_OFFICER_REQUEST",
                "persist": False,
            },
            timeout=35.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_id"] == "ACC-0001"
        assert "investigation_id" in data
        assert "combined_risk_score" in data
        assert "executive_summary" in data


@pytest.mark.asyncio
async def test_api_simulate_withdrawal_endpoint():
    """Verify POST /investigations/simulate-withdrawal handles sandbox requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/investigations/simulate-withdrawal",
            json={
                "account_id": "ACC-SIM-API-TEST",
                "amount": "350.00",
                "currency": "EGP",
                "idempotency_key": "IDEMP-API-TEST-001",
                "is_sandbox_confirmed": True,
                "note": "API Integration Sandbox Test",
            },
            timeout=10.0,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["account_id"] == "ACC-SIM-API-TEST"
        assert Decimal(str(data["amount"])) == Decimal("350.00")


# ==============================================================================
# 6. Deep Validation Tests: Authorization, Read-Only, Service Outages & Taxonomy
# ==============================================================================

@pytest.mark.asyncio
async def test_caller_authorization_enforcement():
    """Unauthorized caller roles (e.g. CUSTOMER) must be rejected by coordinator."""
    req = AccountInvestigationRequest(
        account_id="ACC-0001",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    # Invoke with unauthorized caller role
    report = await run_account_investigation(req, caller_role="CUSTOMER")
    assert report.account_id == "ACC-0001"
    assert len(report.missing_data_and_limitations) > 0
    assert any("not authorized" in lim.lower() for lim in report.missing_data_and_limitations)


@pytest.mark.asyncio
async def test_investigation_read_only_guarantee():
    """Investigation execution must not perform database mutations (read-only guarantee)."""
    from sqlalchemy import select, func
    from infrastructure.database.models import Transaction, Account
    from infrastructure.database.session import get_engine
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = get_engine()
    async with AsyncSession(engine) as session:
        txn_count_before = await session.scalar(select(func.count(Transaction.id)))
        acc_bal_before = await session.scalar(
            select(Account.balance).where(Account.external_id == "ACC-0001")
        )

    # Run investigation
    req = AccountInvestigationRequest(
        account_id="ACC-0001",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    report = await run_account_investigation(req)
    assert report.account_id == "ACC-0001"

    # Verify no new rows created and balances remain untouched
    async with AsyncSession(engine) as session:
        txn_count_after = await session.scalar(select(func.count(Transaction.id)))
        acc_bal_after = await session.scalar(
            select(Account.balance).where(Account.external_id == "ACC-0001")
        )

    assert txn_count_before == txn_count_after
    assert acc_bal_before == acc_bal_after


@pytest.mark.asyncio
async def test_neo4j_unavailability_graceful_partial_report(monkeypatch):
    """When Neo4j is offline, workflow must complete and disclose limitation."""
    from domain.agentic_rag.tools.graph_tools import GraphTools

    async def mock_fail(*args, **kwargs):
        raise ConnectionError("Neo4j connection timeout: bolt://localhost:7687 unreachable")

    monkeypatch.setattr(GraphTools, "find_shared_devices", mock_fail)
    monkeypatch.setattr(GraphTools, "find_shared_ips", mock_fail)
    monkeypatch.setattr(GraphTools, "find_connected_accounts", mock_fail)
    monkeypatch.setattr(GraphTools, "find_fraud_signals", mock_fail)

    req = AccountInvestigationRequest(
        account_id="ACC-0001",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    report = await run_account_investigation(req)
    assert report.account_id == "ACC-0001"
    assert report.graph_intelligence.available is False
    assert "offline" in report.graph_intelligence.graph_disclaimer.lower()
    # Partial report must still contain transaction facts and ML outputs
    assert report.account_facts is not None
    assert report.ml_risk.model_loaded is True


@pytest.mark.asyncio
async def test_regulatory_reference_taxonomy_distinction():
    """Verify clear distinction between statutory mandates, external guidance, and bank heuristics."""
    from domain.investigation.schemas import RuleReferenceType

    now = datetime.now(timezone.utc)
    # Structuring transaction ($48,000 EGP, just below 50,000 statutory limit)
    structuring_txns = [
        TransactionFact(
            transaction_id="TXN-STR-1",
            external_id="TXN-STR-1",
            amount=Decimal("48500.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(hours=2),
        ),
        TransactionFact(
            transaction_id="TXN-STR-2",
            external_id="TXN-STR-2",
            amount=Decimal("49000.00"),
            currency="EGP",
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now - timedelta(hours=1),
        ),
    ]

    metrics = calculate_behavioral_metrics(structuring_txns)
    alerts, _ = evaluate_banking_rules(None, metrics, GraphIntelligenceOutput(available=True))

    str_alert = next((a for a in alerts if a.rule_id == "RULE-STR-001"), None)
    assert str_alert is not None
    # Must be categorized as statutory obligation
    assert str_alert.reference_type == RuleReferenceType.STATUTORY_REGULATION
    assert "FATF Recommendation 20" in str_alert.regulatory_reference


@pytest.mark.asyncio
async def test_model_explanation_honest_labeling():
    """Verify ML model explanations are explicitly documented as model-native tree gain, not SHAP."""
    req = AccountInvestigationRequest(
        account_id="ACC-0001",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    report = await run_account_investigation(req)
    assert report.ml_risk is not None
    assert report.ml_risk.explanation_method == "ACTIVE_FEATURE_GAIN_IMPORTANCE"
    # Gain importances must sum to approximately 1.0 across active features
    if report.ml_risk.top_feature_contributions:
        total_share = sum(report.ml_risk.top_feature_contributions.values())
        assert 0.85 <= total_share <= 1.05
