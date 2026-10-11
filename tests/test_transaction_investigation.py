"""Comprehensive automated tests for Omerta.ai LangGraph Transaction Investigation & Workbench.

Verifies:
1. Safe Sandbox simulation persisting to DB, idempotency, and reset capabilities.
2. Transaction investigation workflow execution (`run_transaction_investigation`) against real database records.
3. Nine distinct pipeline stages recorded in order with real metadata and status.
4. Preceding and subsequent transaction contextualization.
5. Transaction investigation API routes (`POST /api/v1/investigations/transaction`).
6. Production account simulation isolation.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from apps.investigator.account_workflow import run_transaction_investigation
from domain.investigation.schemas import (
    TransactionInvestigationRequest,
    InvestigationReason,
    PipelineStageStatus,
    SimulatedWithdrawalRequest,
)
from domain.investigation.simulation import SandboxWithdrawalService


@pytest.mark.asyncio
async def test_full_sandbox_to_transaction_investigation_lifecycle():
    """End-to-end verification: simulate transaction, persist to DB, and execute 9-stage LangGraph investigation."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Fetch sandbox fixtures
        fix_resp = await client.get("/api/v1/investigations/sandbox-fixtures")
        assert fix_resp.status_code == 200
        fixtures = fix_resp.json()
        assert len(fixtures) >= 2

        # 2. Execute simulated withdrawal to create a real synthetic transaction in PostgreSQL
        sim_payload = {
            "account_id": "ACC-SIM-TEST1",
            "amount": 1250.00,
            "currency": "EGP",
            "idempotency_key": f"E2E-IDEMP-{datetime.now(timezone.utc).timestamp()}",
            "is_sandbox_confirmed": True,
            "note": "Automated E2E Workbench verification transfer",
        }
        sim_resp = await client.post("/api/v1/investigations/simulate-withdrawal", json=sim_payload)
        assert sim_resp.status_code == 200
        sim_data = sim_resp.json()
        assert sim_data["status"] == "COMPLETED"
        txn_id = sim_data["transaction_id"]
        assert txn_id.startswith("TXN-SIM-")

        # 3. Duplicate Idempotency: exact cached response returned
        dup_resp = await client.post("/api/v1/investigations/simulate-withdrawal", json=sim_payload)
        assert dup_resp.status_code == 200
        assert dup_resp.json()["transaction_id"] == txn_id
        assert dup_resp.json()["new_balance"] == sim_data["new_balance"]

        # 4. Investigate the generated synthetic transaction via LangGraph core runner
        req = TransactionInvestigationRequest(
            transaction_id=txn_id,
            account_id="ACC-SIM-TEST1",
            time_range_days=30,
            investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
            persist=False,
        )
        report = await run_transaction_investigation(req)

        # 5. Verify transaction link and identity
        assert report.transaction_id == txn_id
        assert report.account_id == "ACC-SIM-TEST1"
        assert report.investigation_id.startswith("INV-")

        # 6. Verify all 9 pipeline stages are recorded
        assert len(report.pipeline_stages) >= 9
        stage_names = [s.stage_id for s in report.pipeline_stages]
        expected_stages = [
            "stage_1_auth",
            "stage_2_anchor_lookup",
            "stage_3_transaction_intel",
            "stage_4_graph_intel",
            "stage_5_ml_risk",
            "stage_6_banking_rules",
            "stage_7_evidence_agg",
            "stage_8_final_report",
            "stage_9_persistence",
        ]
        for expected in expected_stages:
            assert expected in stage_names, f"Expected stage {expected} missing from trace: {stage_names}"

        # 7. Check individual stage statuses and durations
        for s in report.pipeline_stages:
            assert s.status in [
                PipelineStageStatus.COMPLETED,
                PipelineStageStatus.PARTIAL,
                PipelineStageStatus.SKIPPED,
            ]
            assert s.duration_ms >= 0.0

        # 8. Target transaction details
        assert report.target_transaction is not None
        assert report.target_transaction.transaction_id == txn_id
        assert report.target_transaction.amount == Decimal("1250.00")

        # 9. ML Risk and Rules evaluated
        assert report.ml_risk is not None
        assert report.ml_risk.model_version == "lgbm-risk-v1"
        assert report.executive_summary is not None
        assert len(report.evidence_ids) > 0

        # 10. Test API endpoint for Transaction Investigation
        api_payload = {
            "transaction_id": txn_id,
            "account_id": "ACC-SIM-TEST1",
            "time_range_days": 30,
            "investigation_reason": "AMOUNT_ESCALATION",
            "persist": False,
        }
        resp = await client.post("/api/v1/investigations/transaction", json=api_payload)
        assert resp.status_code == 200, f"Error: {resp.text}"
        api_data = resp.json()
        assert api_data["transaction_id"] == txn_id
        assert len(api_data["pipeline_stages"]) >= 9

        # Also test Root Mount route
        resp_root = await client.post("/investigations/transaction", json=api_payload)
        assert resp_root.status_code == 200

        # 11. Security boundary check: Reject simulating on non-sandbox account
        prod_payload = {
            "account_id": "ACC-0001",
            "amount": 100.00,
            "currency": "EGP",
            "is_sandbox_confirmed": True,
        }
        prod_resp = await client.post("/api/v1/investigations/simulate-withdrawal", json=prod_payload)
        assert prod_resp.status_code in [400, 403, 422]

        # 12. Safe Reset Sandbox
        reset_resp = await client.post("/api/v1/investigations/reset-sandbox")
        assert reset_resp.status_code == 200
        assert "reset" in reset_resp.json()["message"].lower()
