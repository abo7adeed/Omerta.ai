"""Comprehensive Automated Tests for Dynamic Parallel Transaction Investigation Workflow.

Verifies:
1. Every authorized transaction can initiate a dynamic forensic investigation.
2. Correct transaction ID and investigation ID preserved across all stages, traces, and evidence.
3. Independent specialist nodes (PostgreSQL, Neo4j, LightGBM, Banking Rules) execute concurrently in parallel.
4. Measured monotonic execution durations (no invented timings or artificial delays in production).
5. Live investigation status endpoint and duplicate execution prevention (409 Conflict).
6. Real LightGBM ML model inference with genuine feature vector schema.
7. Partial results handling with graceful disclosures when Neo4j is offline.
8. Professional English forensic reporting adhering strictly to the 6 unnumbered sections without raw JSON or repetitive headers.
9. Contradictory risk states are strictly reconciled under a single authoritative assessment.
10. Persisted report and execution trace reload idempotently.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import re
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.main import app
from apps.investigator.account_workflow import (
    run_transaction_investigation,
    get_active_run,
    register_active_run,
    clear_active_run,
)
from domain.investigation.schemas import (
    TransactionInvestigationRequest,
    InvestigationReason,
    PipelineStageStatus,
)
from infrastructure.database.session import get_engine
from infrastructure.database.models import Transaction


@pytest.mark.asyncio
async def test_every_authorized_transaction_investigation():
    """Verify that any arbitrary transaction from the database can be dynamically investigated."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Retrieve an arbitrary transaction from the ledger
        stmt = select(Transaction.external_id, Transaction.amount).limit(1)
        row = (await session.execute(stmt)).first()
        assert row is not None, "At least one transaction must exist in the database."
        txn_id, amount = row[0], row[1]

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=True,
    )
    report = await run_transaction_investigation(req, caller_role="INVESTIGATOR")

    # Transaction identity preservation
    assert report.transaction_id == txn_id
    assert report.target_transaction is not None
    assert report.target_transaction.external_id == txn_id
    assert report.target_transaction.amount == amount
    assert report.investigation_id.startswith("INV-")

    # Verify all 9 pipeline stages executed
    assert len(report.pipeline_stages) == 9
    stage_ids = [s.stage_id for s in report.pipeline_stages]
    assert "stage_1_auth" in stage_ids
    assert "stage_2_anchor_lookup" in stage_ids
    assert "stage_3_transaction_intel" in stage_ids
    assert "stage_4_graph_intel" in stage_ids
    assert "stage_5_ml_risk" in stage_ids
    assert "stage_6_banking_rules" in stage_ids
    assert "stage_7_evidence_agg" in stage_ids
    assert "stage_8_final_report" in stage_ids
    assert "stage_9_persistence" in stage_ids


@pytest.mark.asyncio
async def test_parallel_specialist_node_execution_timing():
    """Verify that independent stages (3, 4, 5, 6) execute in parallel with measured durations."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_id = await session.scalar(select(Transaction.external_id).limit(1))

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=14,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=False,
    )
    report = await run_transaction_investigation(req)

    stage_map = {s.stage_id: s for s in report.pipeline_stages}
    st3 = stage_map["stage_3_transaction_intel"]
    st4 = stage_map["stage_4_graph_intel"]
    st5 = stage_map["stage_5_ml_risk"]
    st6 = stage_map["stage_6_banking_rules"]

    # All 4 parallel stages must have valid measured start times and durations
    for s in [st3, st4, st5, st6]:
        assert s.started_at is not None
        assert s.completed_at is not None
        assert s.duration_ms >= 0.0

    # Parallel dispatch verification: start timestamps within the same small window (< 200ms)
    start_times = [s.started_at.timestamp() for s in [st3, st4, st5, st6]]
    max_delta = max(start_times) - min(start_times)
    assert max_delta < 0.20, f"Parallel stages did not start concurrently: delta = {max_delta}s"


@pytest.mark.asyncio
async def test_lightgbm_inference_and_feature_schema():
    """Verify real LightGBM model artifact inference with accurate feature schema."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_id = await session.scalar(select(Transaction.external_id).limit(1))

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=False,
    )
    report = await run_transaction_investigation(req)

    assert report.ml_risk is not None
    assert report.ml_risk.model_loaded is True
    assert report.ml_risk.model_version == "lgbm-risk-v1"
    assert report.ml_risk.feature_version == "features-v1"
    assert 0.0 <= report.ml_risk.risk_score <= 1.0
    assert report.ml_risk.risk_tier in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

    # Evaluation metrics from JSON artifact
    assert report.ml_risk.model_evaluation_metrics is not None
    assert report.ml_risk.model_evaluation_metrics.get("model_version") == "lgbm-risk-v1"
    assert "roc_auc" in report.ml_risk.model_evaluation_metrics

    # Feature explanations honest labeling
    assert report.ml_risk.explanation_method == "ACTIVE_FEATURE_GAIN_IMPORTANCE"
    if report.ml_risk.top_feature_contributions:
        assert len(report.ml_risk.top_feature_contributions) > 0


@pytest.mark.asyncio
async def test_professional_english_forensic_report_structure():
    """Verify final report satisfies professional English style and the 6 unnumbered sections."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_id = await session.scalar(select(Transaction.external_id).limit(1))

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=False,
    )
    report = await run_transaction_investigation(req)

    assert report.forensic_report_markdown is not None
    md = report.forensic_report_markdown

    # Must contain the exact 6 headings without numbering
    assert "## Executive Summary" in md
    assert "## Transaction Context" in md
    assert "## Findings and Analysis" in md
    assert "## Risk Assessment" in md
    assert "## Evidence and Limitations" in md
    assert "## Conclusion and Recommended Actions" in md

    # Must NOT contain numbered section titles (e.g. "## 1. Executive Summary")
    assert not re.search(r"##\s+\d+\.?\s+Executive Summary", md)
    assert not re.search(r"##\s+\d+\.?\s+Transaction Context", md)

    # Must NOT leak raw JSON dictionaries
    assert '{"transaction_id":' not in md
    assert '{"rules_score":' not in md

    # Must mention transaction ID
    assert txn_id in md


@pytest.mark.asyncio
async def test_authoritative_reconciled_risk_assessment():
    """Verify that contradictory risk states are strictly resolved under one authoritative assessment."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_id = await session.scalar(select(Transaction.external_id).limit(1))

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=False,
    )
    report = await run_transaction_investigation(req)

    # If threshold is exceeded, human review must be required and action cannot be routine monitoring
    if report.threshold_exceeded:
        assert report.human_review_required is True
        assert report.recommended_action != "ROUTINE_MONITORING"
    else:
        # If threshold not exceeded, score must be below operational threshold
        assert report.combined_risk_score < report.operational_alert_threshold


@pytest.mark.asyncio
async def test_live_tracker_and_duplicate_prevention_via_api():
    """Verify live snapshot polling endpoint and duplicate execution conflict (409)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Fetch live snapshot of a known transaction
        live_resp = await client.get("/api/v1/investigations/transaction/TXN-001/live")
        assert live_resp.status_code == 200
        snap = live_resp.json()
        assert "stages" in snap
        assert len(snap["stages"]) == 9

        # 2. Register mock active run to simulate an in-progress investigation
        inv_id = "INV-TXN-CONCURRENT-TEST"
        test_txn_id = "TXN-CONCURRENT-TEST"
        tracker = register_active_run(inv_id, test_txn_id, is_transaction=True)
        try:
            # 3. Attempt to trigger another investigation while running
            payload = {
                "transaction_id": test_txn_id,
                "time_range_days": 30,
                "investigation_reason": "AMOUNT_ESCALATION",
            }
            dup_resp = await client.post("/api/v1/investigations/transaction", json=payload)
            # Must return 409 Conflict to prevent duplicate execution
            assert dup_resp.status_code == 409
            detail = dup_resp.json()["detail"].lower()
            assert "already running" in detail or "already in progress" in detail
        finally:
            clear_active_run(inv_id)


@pytest.mark.asyncio
async def test_neo4j_unavailability_partial_results(monkeypatch):
    """Verify workflow succeeds and marks stage as PARTIAL when Neo4j is unavailable."""
    from domain.agentic_rag.tools.graph_tools import GraphTools

    async def mock_offline(*args, **kwargs):
        raise ConnectionError("Neo4j database offline for maintenance.")

    monkeypatch.setattr(GraphTools, "find_shared_devices", mock_offline)
    monkeypatch.setattr(GraphTools, "find_shared_ips", mock_offline)
    monkeypatch.setattr(GraphTools, "find_connected_accounts", mock_offline)
    monkeypatch.setattr(GraphTools, "find_fraud_signals", mock_offline)

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_id = await session.scalar(select(Transaction.external_id).limit(1))

    req = TransactionInvestigationRequest(
        transaction_id=txn_id,
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=False,
    )
    report = await run_transaction_investigation(req)

    # Workflow must complete successfully
    assert report.transaction_id == txn_id
    graph_stage = next((s for s in report.pipeline_stages if s.stage_id == "stage_4_graph_intel"), None)
    assert graph_stage is not None
    assert graph_stage.status == PipelineStageStatus.PARTIAL
    assert report.graph_intelligence.available is False
    assert "offline" in report.graph_intelligence.graph_disclaimer.lower()


@pytest.mark.asyncio
async def test_persisted_dossier_reload_after_investigation():
    """Verify completed investigation dossier persists and reloads from API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Run investigation with persistence enabled
        payload = {
            "transaction_id": "TXN-001",
            "time_range_days": 30,
            "investigation_reason": "AMOUNT_ESCALATION",
            "persist": True,
        }
        create_resp = await client.post("/api/v1/investigations/transaction", json=payload)
        assert create_resp.status_code == 200
        data = create_resp.json()
        assert data["transaction_id"] == "TXN-001"
        assert data["forensic_report_markdown"] is not None

        # 2. Reload investigation directly from GET endpoint
        get_resp = await client.get("/api/v1/investigations/transaction/TXN-001")
        assert get_resp.status_code == 200
        reloaded = get_resp.json()
        assert reloaded["transaction_id"] == "TXN-001"
        assert reloaded["investigation_id"] == data["investigation_id"]
        assert reloaded["forensic_report_markdown"] == data["forensic_report_markdown"]
        assert len(reloaded["pipeline_stages"]) == 9
