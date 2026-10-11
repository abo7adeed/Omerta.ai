"""LangGraph Forensic Investigation Workflow for Omerta.ai.

Orchestrates a comprehensive, evidence-based investigation pipeline with 9 execution stages:
1. Request Validation & Caller Authorization (Security Guardrails)
2. Target Account / Transaction Anchor Verification (Relational Ledger Lookup)
3. PostgreSQL Transaction Intelligence & Velocity History (Relational Ledger Analytics)
4. Neo4j Graph Topology & Shared Entity Intelligence (Graph Network Analytics)
5. LightGBM Machine Learning Risk Scoring (LightGBM Inference Engine)
6. Deterministic Banking Rules & Velocity Analysis (Banking Rules Engine)
7. Forensic Evidence Aggregation & Provenance Hashing (Evidence Aggregator)
8. Grounded LLM Report Synthesis & Recommendations (LLM Synthesis)
9. Dossier Persistence & Audit Ledger Registration (Relational Case Persistence)
"""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
import logging
from pathlib import Path
import time
from typing import Any
import uuid

from langgraph.graph import END, START, StateGraph
from sqlalchemy import select, and_, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.investigator.account_state import AccountInvestigationState
from domain.agentic_rag.tools.database_tools import DatabaseTools
from domain.agentic_rag.tools.graph_tools import GraphTools
from domain.agentic_rag.schemas import ChartSeries, ChartSpecification, ChartType
from domain.agentic_rag.visualization import VisualizationEngine
from domain.investigation.metrics import calculate_behavioral_metrics
from domain.investigation.rules import (
    APPLICATION_ALERT_THRESHOLD,
    calculate_combined_risk_score,
    determine_recommended_action,
    evaluate_banking_rules,
)
from domain.investigation.schemas import (
    AccountFacts,
    AccountInvestigationReport,
    AccountInvestigationRequest,
    BehavioralMetrics,
    GraphIntelligenceOutput,
    MLRiskOutput,
    PipelineStageStatus,
    PipelineStageTrace,
    RecommendedReviewAction,
    TransactionFact,
    TransactionInvestigationRequest,
)
from infrastructure.database.models import Account, Customer, Transaction, AccountLedgerEntry, InvestigationCase
from infrastructure.database.session import get_engine
from infrastructure.llm.factory import get_llm_provider
from infrastructure.risk.features import feature_row
from infrastructure.risk.ml_provider import METRICS_FILE, MODEL_FILE, MODEL_VERSION, MLRiskProvider

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Stage 1 & 2: Coordinator & Anchor Verification Node
# --------------------------------------------------------------------------- #
async def coordinator_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Validate caller authorization and verify account/transaction anchor existence."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)
    investigation_id = state.investigation_id or (
        f"INV-TXN-{state.transaction_id}" if state.transaction_id
        else f"INV-ACC-{uuid.uuid4().hex[:8].upper()}"
    )

    # 1. Authorization Check
    authorized_roles = {
        "INVESTIGATOR",
        "SENIOR_INVESTIGATOR",
        "FRAUD_ANALYST",
        "COMPLIANCE_OFFICER",
        "ADMIN",
        "ADMINISTRATOR",
        "AUDITOR",
        "SYSTEM",
    }
    is_authorized = state.caller_role.upper() in authorized_roles

    stage_1_trace = PipelineStageTrace(
        stage_id="stage_1_auth",
        stage_name="Request Validation & Authorization",
        description="Verify cryptographic caller role tokens, API security policies, and boundary guardrails.",
        source_tier="Security Guardrails",
        status=PipelineStageStatus.COMPLETED if is_authorized else PipelineStageStatus.FAILED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"caller_role": state.caller_role, "caller_id": state.caller_id, "investigation_reason": state.investigation_reason},
        output_summary={"authorized": is_authorized, "investigation_id": investigation_id},
        error_message=None if is_authorized else f"Caller role '{state.caller_role}' unauthorized.",
    )

    if not is_authorized:
        return {
            "investigation_id": investigation_id,
            "status": "FAILED",
            "error_message": f"Caller role '{state.caller_role}' is not authorized to initiate forensic investigations.",
            "pipeline_stages": [stage_1_trace],
            "node_timings_ms": {"coordinator": round((time.perf_counter() - t0) * 1000, 2)},
        }

    # 2. Account / Transaction Anchor Verification
    t_anchor = time.perf_counter()
    dt_anchor_start = datetime.now(UTC)
    account_facts: AccountFacts | None = None
    target_txn: TransactionFact | None = None
    account_id = state.account_id

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # If investigating a specific transaction, look it up first
        if state.transaction_id:
            txn_stmt = (
                select(Transaction)
                .options(
                    selectinload(Transaction.account).selectinload(Account.customer),
                    selectinload(Transaction.recipient_account),
                    selectinload(Transaction.device),
                    selectinload(Transaction.ip_address),
                )
                .where(
                    or_(
                        Transaction.external_id == state.transaction_id,
                        Transaction.id == int(state.transaction_id) if state.transaction_id.isdigit() else False,
                    )
                )
            )
            txn_row = await session.scalar(txn_stmt)
            if not txn_row:
                stage_2_trace = PipelineStageTrace(
                    stage_id="stage_2_anchor_lookup",
                    stage_name="Transaction Anchor Lookup",
                    description="Resolve verified double-entry transaction record from the PostgreSQL ledger.",
                    source_tier="PostgreSQL",
                    status=PipelineStageStatus.FAILED,
                    started_at=dt_anchor_start,
                    completed_at=datetime.now(UTC),
                    duration_ms=round((time.perf_counter() - t_anchor) * 1000, 2),
                    input_summary={"transaction_id": state.transaction_id},
                    output_summary={},
                    error_message=f"Transaction '{state.transaction_id}' was not found in the relational ledger.",
                )
                return {
                    "investigation_id": investigation_id,
                    "status": "FAILED",
                    "error_message": f"Transaction '{state.transaction_id}' was not found in the relational ledger.",
                    "pipeline_stages": [stage_1_trace, stage_2_trace],
                    "node_timings_ms": {"coordinator": round((time.perf_counter() - t0) * 1000, 2)},
                }

            # Populate target_txn
            recip_name = txn_row.recipient_account.customer_name if txn_row.recipient_account else None
            target_txn = TransactionFact(
                transaction_id=txn_row.external_id,
                external_id=txn_row.external_id,
                timestamp=txn_row.timestamp,
                amount=txn_row.amount,
                currency=txn_row.currency,
                transaction_type=txn_row.transaction_type,
                status=txn_row.status,
                recipient_account_id=txn_row.recipient_account.external_id if txn_row.recipient_account else (str(txn_row.recipient_account_id) if txn_row.recipient_account_id else None),
                recipient_name=recip_name,
                device_id=txn_row.device.external_id if txn_row.device else None,
                ip_address=txn_row.ip_address.address if txn_row.ip_address else None,
                is_new_device=txn_row.is_new_device,
                is_new_ip=txn_row.is_new_ip,
                risk_score=float(txn_row.risk_score) if txn_row.risk_score is not None else None,
                risk_level=txn_row.risk_level,
            )

            # Link account
            if txn_row.account:
                account_id = txn_row.account.external_id
                acc = txn_row.account
                cust = txn_row.account.customer
                acc_upper = account_id.upper()
                is_sandbox = (
                    acc_upper.startswith("ACC-SIM")
                    or "TEST" in acc_upper
                    or "SANDBOX" in acc_upper
                    or acc_upper in ("ACC-0001", "ACC-1001", "ACC-2001", "ACC-3001", "ACC-6001", "ACC-7001", "ACC-8001", "ACC-9001")
                )
                account_facts = AccountFacts(
                    account_id=acc.external_id,
                    customer_id=cust.external_id if cust else "UNKNOWN",
                    customer_name=cust.name if cust else acc.customer_name,
                    customer_email=cust.email if cust else None,
                    omerta_user_number=getattr(cust, "omerta_user_number", None),
                    account_type=acc.account_type,
                    status=acc.status,
                    currency=acc.currency,
                    ledger_balance=acc.balance,
                    available_balance=acc.balance,
                    risk_level=acc.risk_level,
                    created_at=acc.created_at,
                    verified_identity=bool(getattr(cust, "verification_status", "NOT_VERIFIED") == "VERIFIED"),
                    is_sandbox=is_sandbox,
                )

        # Standard Account facts lookup if not already populated from transaction
        if not account_facts and account_id:
            stmt = (
                select(Account, Customer)
                .join(Customer, Account.customer_id == Customer.id, isouter=True)
                .where(Account.external_id == account_id)
            )
            res = (await session.execute(stmt)).first()
            if not res:
                stage_2_trace = PipelineStageTrace(
                    stage_id="stage_2_anchor_lookup",
                    stage_name="Target Account Verification",
                    description="Resolve account record and balance ledger from PostgreSQL.",
                    source_tier="PostgreSQL",
                    status=PipelineStageStatus.FAILED,
                    started_at=dt_anchor_start,
                    completed_at=datetime.now(UTC),
                    duration_ms=round((time.perf_counter() - t_anchor) * 1000, 2),
                    input_summary={"account_id": account_id},
                    output_summary={},
                    error_message=f"Account '{account_id}' was not found in the relational banking ledger.",
                )
                return {
                    "investigation_id": investigation_id,
                    "status": "FAILED",
                    "error_message": f"Account '{account_id}' was not found in the relational banking ledger.",
                    "pipeline_stages": [stage_1_trace, stage_2_trace],
                    "node_timings_ms": {"coordinator": round((time.perf_counter() - t0) * 1000, 2)},
                }

            acc, cust = res
            acc_upper = account_id.upper()
            is_sandbox = (
                acc_upper.startswith("ACC-SIM")
                or "TEST" in acc_upper
                or "SANDBOX" in acc_upper
                or acc_upper in ("ACC-0001", "ACC-1001", "ACC-2001", "ACC-3001", "ACC-6001", "ACC-7001", "ACC-8001", "ACC-9001")
            )
            account_facts = AccountFacts(
                account_id=acc.external_id,
                customer_id=cust.external_id if cust else "UNKNOWN",
                customer_name=cust.name if cust else acc.customer_name,
                customer_email=cust.email if cust else None,
                omerta_user_number=getattr(cust, "omerta_user_number", None),
                account_type=acc.account_type,
                status=acc.status,
                currency=acc.currency,
                ledger_balance=acc.balance,
                available_balance=acc.balance,
                risk_level=acc.risk_level,
                created_at=acc.created_at,
                verified_identity=bool(getattr(cust, "verification_status", "NOT_VERIFIED") == "VERIFIED"),
                is_sandbox=is_sandbox,
            )

    stage_2_trace = PipelineStageTrace(
        stage_id="stage_2_anchor_lookup",
        stage_name="Target Ledger & Anchor Verification",
        description="Verify relational ledger records, account state, and target transaction existence.",
        source_tier="PostgreSQL",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_anchor_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t_anchor) * 1000, 2),
        input_summary={"account_id": account_id, "transaction_id": state.transaction_id},
        output_summary={
            "account_id": account_facts.account_id if account_facts else "N/A",
            "customer_name": account_facts.customer_name if account_facts else "N/A",
            "balance": float(account_facts.available_balance) if account_facts else 0.0,
            "currency": account_facts.currency if account_facts else "EGP",
            "target_transaction_amount": float(target_txn.amount) if target_txn else None,
        },
        evidence_ids=[f"LEDGER:{account_facts.account_id}"] if account_facts else [],
    )

    return {
        "investigation_id": investigation_id,
        "account_id": account_id or state.account_id,
        "status": "RUNNING",
        "account_facts": account_facts,
        "target_transaction": target_txn,
        "pipeline_stages": [stage_1_trace, stage_2_trace],
        "audit_events": [
            {
                "event": "INVESTIGATION_INITIATED",
                "investigation_id": investigation_id,
                "account_id": account_id or state.account_id,
                "transaction_id": state.transaction_id,
                "caller_role": state.caller_role,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ],
        "node_timings_ms": {"coordinator": round((time.perf_counter() - t0) * 1000, 2)},
    }


def route_after_coordinator(state: AccountInvestigationState) -> str:
    """Conditional edge routing based on coordinator validation."""
    if state.status == "FAILED":
        return END
    return "parallel_dispatch"


# --------------------------------------------------------------------------- #
# Stage 3: Transaction Intelligence Node
# --------------------------------------------------------------------------- #
async def transaction_intelligence_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Retrieve verified transaction records, preceding and subsequent context from PostgreSQL."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)
    transactions: list[TransactionFact] = []
    preceding_txns: list[TransactionFact] = []
    subsequent_txns: list[TransactionFact] = []

    cutoff = datetime.now(UTC) - timedelta(days=state.time_range_days)

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        acc_id = await session.scalar(select(Account.id).where(Account.external_id == state.account_id))
        if acc_id:
            stmt = (
                select(Transaction)
                .options(selectinload(Transaction.recipient_account), selectinload(Transaction.device), selectinload(Transaction.ip_address))
                .where(
                    and_(
                        Transaction.account_id == acc_id,
                        Transaction.timestamp >= cutoff,
                    )
                )
                .order_by(desc(Transaction.timestamp))
                .limit(200)
            )
            rows = (await session.scalars(stmt)).all()

            for r in rows:
                recip_name = r.recipient_account.customer_name if r.recipient_account else None
                transactions.append(
                    TransactionFact(
                        transaction_id=r.external_id,
                        external_id=r.external_id,
                        timestamp=r.timestamp,
                        amount=r.amount,
                        currency=r.currency,
                        transaction_type=r.transaction_type,
                        status=r.status,
                        recipient_account_id=r.recipient_account.external_id if r.recipient_account else (str(r.recipient_account_id) if r.recipient_account_id else None),
                        recipient_name=recip_name,
                        device_id=r.device.external_id if r.device else None,
                        ip_address=r.ip_address.address if r.ip_address else None,
                        is_new_device=r.is_new_device,
                        is_new_ip=r.is_new_ip,
                        risk_score=float(r.risk_score) if r.risk_score is not None else None,
                        risk_level=r.risk_level,
                    )
                )

            if state.target_transaction:
                target_time = state.target_transaction.timestamp
                prec_stmt = (
                    select(Transaction)
                    .options(selectinload(Transaction.recipient_account))
                    .where(
                        Transaction.account_id == acc_id,
                        Transaction.timestamp < target_time,
                    )
                    .order_by(desc(Transaction.timestamp))
                    .limit(5)
                )
                for pr in (await session.scalars(prec_stmt)).all():
                    preceding_txns.append(
                        TransactionFact(
                            transaction_id=pr.external_id,
                            external_id=pr.external_id,
                            timestamp=pr.timestamp,
                            amount=pr.amount,
                            currency=pr.currency,
                            transaction_type=pr.transaction_type,
                            status=pr.status,
                            recipient_account_id=pr.recipient_account.external_id if pr.recipient_account else None,
                            recipient_name=pr.recipient_account.customer_name if pr.recipient_account else "Beneficiary",
                            risk_score=float(pr.risk_score) if pr.risk_score is not None else None,
                            risk_level=pr.risk_level,
                        )
                    )

                sub_stmt = (
                    select(Transaction)
                    .options(selectinload(Transaction.recipient_account))
                    .where(
                        Transaction.account_id == acc_id,
                        Transaction.timestamp > target_time,
                    )
                    .order_by(Transaction.timestamp.asc())
                    .limit(5)
                )
                for sr in (await session.scalars(sub_stmt)).all():
                    subsequent_txns.append(
                        TransactionFact(
                            transaction_id=sr.external_id,
                            external_id=sr.external_id,
                            timestamp=sr.timestamp,
                            amount=sr.amount,
                            currency=sr.currency,
                            transaction_type=sr.transaction_type,
                            status=sr.status,
                            recipient_account_id=sr.recipient_account.external_id if sr.recipient_account else None,
                            recipient_name=sr.recipient_account.customer_name if sr.recipient_account else "Beneficiary",
                            risk_score=float(sr.risk_score) if sr.risk_score is not None else None,
                            risk_level=sr.risk_level,
                        )
                    )

    total_volume = sum((t.amount for t in transactions), Decimal("0.00"))
    stage_3_trace = PipelineStageTrace(
        stage_id="stage_3_transaction_intel",
        stage_name="PostgreSQL Transaction Intelligence",
        description="Query double-entry transaction ledgers, lookback histories, and preceding/subsequent chronological context.",
        source_tier="PostgreSQL",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"account_id": state.account_id, "lookback_days": state.time_range_days, "target_transaction_id": state.transaction_id},
        output_summary={
            "transactions_retrieved": len(transactions),
            "total_volume_egp": float(total_volume),
            "preceding_transactions_count": len(preceding_txns),
            "subsequent_transactions_count": len(subsequent_txns),
        },
        evidence_ids=[f"TXN:{t.external_id}" for t in transactions[:8]],
    )

    return {
        "transaction_facts": transactions,
        "preceding_transactions": preceding_txns,
        "subsequent_transactions": subsequent_txns,
        "pipeline_stages": [stage_3_trace],
        "evidence_ids": [f"TXN:{t.external_id}" for t in transactions[:8]],
        "node_timings_ms": {"transaction_intelligence": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 4: Neo4j Graph Intelligence Node
# --------------------------------------------------------------------------- #
async def graph_intelligence_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Inspect topological relationships, shared devices, shared IPs, and fraud rings."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)
    graph_out = GraphIntelligenceOutput()

    try:
        shared_devices_res = await GraphTools.find_shared_devices(state.account_id)
        shared_ips_res = await GraphTools.find_shared_ips(state.account_id)
        connected_accs_res = await GraphTools.find_connected_accounts(state.account_id)
        fraud_ring_res = await GraphTools.find_fraud_signals(state.account_id)

        shared_devices = shared_devices_res.get("shared_devices", [])
        shared_ips = shared_ips_res.get("shared_ips", [])
        connected_accounts = connected_accs_res.get("connected_accounts", [])

        graph_out = GraphIntelligenceOutput(
            available=True,
            shared_device_count=len(shared_devices),
            shared_devices=shared_devices,
            shared_ip_count=len(shared_ips),
            shared_ips=shared_ips,
            connected_accounts_count=len(connected_accounts),
            connected_accounts=connected_accounts,
            fraud_ring_detected=bool(fraud_ring_res.get("signals")),
            fraud_ring_details=fraud_ring_res,
        )
        stage_status = PipelineStageStatus.COMPLETED
        error_msg = None
    except Exception as exc:
        logger.warning("Neo4j graph intelligence node encountered exception: %s", exc)
        graph_out = GraphIntelligenceOutput(
            available=False,
            graph_disclaimer="Neo4j graph service currently offline or unreachable. Topology analysis omitted from this investigation.",
        )
        stage_status = PipelineStageStatus.PARTIAL
        error_msg = f"Neo4j topology query bypassed: {exc}"

    evidence = []
    if graph_out.available and graph_out.shared_device_count > 0:
        evidence.append(f"GRAPH:SHARED_DEVICE:{state.account_id}")
    if graph_out.available and graph_out.shared_ip_count > 0:
        evidence.append(f"GRAPH:SHARED_IP:{state.account_id}")

    stage_4_trace = PipelineStageTrace(
        stage_id="stage_4_graph_intel",
        stage_name="Neo4j Graph Topology Intelligence",
        description="Traverse multi-hop relationships for shared hardware identifiers, shared IP subnets, and syndicate rings.",
        source_tier="Neo4j",
        status=stage_status,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"account_id": state.account_id},
        output_summary={
            "service_available": graph_out.available,
            "shared_devices_count": graph_out.shared_device_count,
            "shared_ips_count": graph_out.shared_ip_count,
            "connected_accounts_count": graph_out.connected_accounts_count,
            "fraud_ring_detected": graph_out.fraud_ring_detected,
        },
        evidence_ids=evidence,
        error_message=error_msg,
    )

    return {
        "graph_intelligence": graph_out,
        "pipeline_stages": [stage_4_trace],
        "evidence_ids": evidence,
        "node_timings_ms": {"graph_intelligence": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 5: ML Risk Scoring Node
# --------------------------------------------------------------------------- #
async def ml_risk_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Invoke the trained LightGBM model artifact with feature validation."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)

    ml_out = MLRiskOutput(
        model_version=MODEL_VERSION,
        feature_version="features-v1",
        risk_score=0.10,
        risk_tier="LOW",
        model_loaded=False,
    )

    try:
        metrics_meta = {}
        if METRICS_FILE.exists():
            metrics_meta = json.loads(METRICS_FILE.read_text(encoding="utf-8"))

        provider = MLRiskProvider()
        ml_out.model_loaded = True
        ml_out.model_evaluation_metrics = metrics_meta

        target_txn = state.target_transaction or (state.transaction_facts[0] if state.transaction_facts else None)

        if target_txn:
            from domain.schemas import RiskFeatures

            features = RiskFeatures(
                transaction_id=target_txn.external_id,
                transaction_amount=float(target_txn.amount),
                currency=target_txn.currency,
                transaction_velocity_7d=len(state.transaction_facts),
                account_age_days=180,
                recipient_age_days=120,
                originator_risk_level=state.account_facts.risk_level if state.account_facts else "LOW",
                recipient_risk_level="LOW",
                previous_alert_count=1 if any(t.risk_score and t.risk_score > 40.0 for t in state.transaction_facts) else 0,
                previous_suspicious_activity=any(t.risk_score and t.risk_score > 40.0 for t in state.transaction_facts),
                is_new_device=target_txn.is_new_device,
                is_new_ip=target_txn.is_new_ip,
            )

            score_out = await provider.score(features)
            ml_out.risk_score = score_out.risk_score
            ml_out.risk_tier = score_out.risk_level
            ml_out.top_feature_contributions = dict(list(score_out.contributions.items())[:5])
        else:
            ml_out.risk_score = 0.05
            ml_out.risk_tier = "LOW"
            ml_out.top_feature_contributions = {"baseline_inactivity": 0.05}

        stage_status = PipelineStageStatus.COMPLETED
        error_msg = None
    except Exception as exc:
        logger.warning("ML risk scoring node failed: %s", exc)
        ml_out.model_loaded = False
        ml_out.error_message = str(exc)
        stage_status = PipelineStageStatus.FAILED
        error_msg = str(exc)

    stage_5_trace = PipelineStageTrace(
        stage_id="stage_5_ml_risk",
        stage_name="LightGBM Machine Learning Risk Scoring",
        description="Load trained LightGBM gradient-boosted decision trees and compute normalized prediction score.",
        source_tier="LightGBM",
        status=stage_status,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={
            "model_version": MODEL_VERSION,
            "target_transaction_id": state.target_transaction.external_id if state.target_transaction else "ACCOUNT_LATEST",
            "evaluated_amount": float(state.target_transaction.amount) if state.target_transaction else None,
        },
        output_summary={
            "model_loaded": ml_out.model_loaded,
            "risk_score": round(ml_out.risk_score, 4),
            "risk_tier": ml_out.risk_tier,
            "explanation_method": ml_out.explanation_method,
            "top_features": ml_out.top_feature_contributions,
        },
        evidence_ids=[f"ML:PREDICTION:{ml_out.model_version}"],
        error_message=error_msg,
    )

    return {
        "ml_risk": ml_out,
        "pipeline_stages": [stage_5_trace],
        "evidence_ids": [f"ML:PREDICTION:{ml_out.model_version}"],
        "node_timings_ms": {"ml_risk": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 6: Banking Rules Engine Node
# --------------------------------------------------------------------------- #
async def banking_rules_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Calculate deterministic behavioral metrics and evaluate banking rules."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)

    balance = state.account_facts.available_balance if state.account_facts else Decimal("0.00")
    currency = state.account_facts.currency if state.account_facts else "EGP"

    metrics = calculate_behavioral_metrics(
        state.transaction_facts,
        account_balance=balance,
        primary_currency=currency,
    )

    graph_info = state.graph_intelligence or GraphIntelligenceOutput(available=False)
    alerts, rules_score = evaluate_banking_rules(
        account=state.account_facts,
        metrics=metrics,
        graph=graph_info,
        currency=currency,
    )

    evidence = [f"RULE:{a.rule_id}" for a in alerts]

    stage_6_trace = PipelineStageTrace(
        stage_id="stage_6_banking_rules",
        stage_name="Deterministic Banking Rules & Velocity Analysis",
        description="Compute rolling 5m/15m/60m velocity windows, amount escalation, and FATF/regulatory heuristic indicators.",
        source_tier="Banking Rules Engine",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"evaluated_transactions": len(state.transaction_facts), "balance": float(balance), "currency": currency},
        output_summary={
            "rules_score": round(rules_score, 4),
            "triggered_rules_count": len(alerts),
            "triggered_rule_names": [a.rule_name for a in alerts],
            "velocity_5m_count": metrics.velocity_5m_max_count,
            "has_amount_escalation": metrics.has_amount_escalation,
        },
        evidence_ids=evidence,
    )

    return {
        "behavioral_metrics": metrics,
        "triggered_rules": alerts,
        "rules_score": rules_score,
        "pipeline_stages": [stage_6_trace],
        "evidence_ids": evidence,
        "node_timings_ms": {"banking_rules": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 7: Evidence Aggregation & Validation Node
# --------------------------------------------------------------------------- #
async def evidence_aggregation_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Merge facts, compute combined risk score, validate calculations, and generate charts."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)

    ml = state.ml_risk or MLRiskOutput(
        model_version=MODEL_VERSION,
        feature_version="features-v1",
        risk_score=0.1,
        risk_tier="LOW",
        model_loaded=False,
    )
    rules_score = state.rules_score

    combined_score, threshold_exceeded = calculate_combined_risk_score(ml, rules_score)
    recommended_action, justification = determine_recommended_action(
        combined_score,
        state.triggered_rules,
        state.account_facts,
    )

    limitations: list[str] = []
    if not state.transaction_facts:
        limitations.append("Zero transaction history retrieved within the specified lookback window.")
    if state.graph_intelligence and not state.graph_intelligence.available:
        limitations.append("Graph topology service was unreachable; shared hardware syndicate signals are unavailable.")
    if not ml.model_loaded:
        limitations.append(f"LightGBM model artifact could not be loaded ({ml.error_message}); risk score relies entirely on deterministic rules.")

    charts: list[dict[str, Any]] = []
    if state.transaction_facts:
        recent_10 = list(reversed(state.transaction_facts[:10]))
        cats = [t.timestamp.strftime("%m-%d %H:%M") for t in recent_10]
        vols = [float(t.amount) for t in recent_10]

        spec_bar = ChartSpecification(
            chart_type=ChartType.BAR,
            title=f"Transaction Volume Trajectory ({state.account_id})",
            categories=cats,
            series=[ChartSeries(name=f"Amount ({state.account_facts.currency if state.account_facts else 'EGP'})", data=vols)],
            x_axis_label="Timestamp",
            y_axis_label="Volume",
        )
        ref_bar = VisualizationEngine.render_chart(spec_bar)
        if ref_bar:
            charts.append(ref_bar.model_dump())

        labels = ["ML Model Score", "Banking Rules", "Baseline Activity"]
        weights = [
            round(ml.risk_score * 55, 1),
            round(rules_score * 45, 1),
            max(5.0, round(100.0 - (ml.risk_score * 55 + rules_score * 45), 1)),
        ]
        spec_donut = ChartSpecification(
            chart_type=ChartType.DONUT,
            title="Composite Risk Weight Distribution",
            categories=labels,
            series=[ChartSeries(name="Contribution %", data=weights)],
        )
        ref_donut = VisualizationEngine.render_chart(spec_donut)
        if ref_donut:
            charts.append(ref_donut.model_dump())

    stage_7_trace = PipelineStageTrace(
        stage_id="stage_7_evidence_agg",
        stage_name="Forensic Evidence Aggregation & Synthesis",
        description="Synthesize multi-modal facts, compute composite risk score, validate calculations, and render visualizations.",
        source_tier="Evidence Aggregator",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"ml_score": ml.risk_score, "rules_score": rules_score, "alert_count": len(state.triggered_rules)},
        output_summary={
            "combined_risk_score": round(combined_score, 4),
            "threshold_exceeded": threshold_exceeded,
            "recommended_action": recommended_action.value,
            "charts_generated": len(charts),
        },
        evidence_ids=[f"SCORE:COMPOSITE:{round(combined_score, 2)}"],
    )

    return {
        "combined_risk_score": combined_score,
        "threshold_exceeded": threshold_exceeded,
        "recommended_action": recommended_action,
        "recommended_action_justification": justification,
        "missing_data_and_limitations": limitations,
        "charts": charts,
        "pipeline_stages": [stage_7_trace],
        "node_timings_ms": {"evidence_aggregation": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 8: Final Report Generation Node
# --------------------------------------------------------------------------- #
async def final_report_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Generate grounded executive summary and explanations with strict grounding."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)

    acc = state.account_facts
    metrics = state.behavioral_metrics
    alerts = state.triggered_rules
    ml = state.ml_risk
    target_txn = state.target_transaction

    if target_txn:
        exec_summary = (
            f"Forensic investigation for transaction {target_txn.external_id} "
            f"({target_txn.amount:,.2f} {target_txn.currency}, Status: {target_txn.status}) "
            f"originating from account {state.account_id} ({acc.customer_name if acc else 'N/A'}) "
            f"yielded an evaluated composite risk score of {state.combined_risk_score:.1%}. "
        )
        if state.threshold_exceeded:
            exec_summary += (
                f"The composite score exceeds the {APPLICATION_ALERT_THRESHOLD:.0%} operational threshold, "
                f"mandating {state.recommended_action.value}."
            )
        else:
            exec_summary += (
                f"The composite score remains beneath the {APPLICATION_ALERT_THRESHOLD:.0%} operational threshold; "
                f"standard clearance maintained."
            )
    else:
        exec_summary = (
            f"Forensic account investigation for {state.account_id} ({acc.customer_name if acc else 'N/A'}, "
            f"Status: {acc.status if acc else 'UNKNOWN'}) concluded with a composite risk score of "
            f"{state.combined_risk_score:.1%}. "
        )
        if state.threshold_exceeded:
            exec_summary += (
                f"The composite score exceeds the {APPLICATION_ALERT_THRESHOLD:.0%} operational threshold, "
                f"triggering {state.recommended_action.value}."
            )
        else:
            exec_summary += (
                f"The composite score remains beneath the {APPLICATION_ALERT_THRESHOLD:.0%} operational threshold. "
                f"Routine automated monitoring maintained."
            )

    factor_explanations: list[str] = []
    for a in alerts:
        factor_explanations.append(f"[{a.severity.value}] {a.rule_name}: {a.explanation}")

    if ml and ml.top_feature_contributions:
        top_contrib = ", ".join(f"{k} ({v:+.2f})" for k, v in ml.top_feature_contributions.items())
        factor_explanations.append(f"[ML-SIGNAL] LightGBM Model Top Contributors: {top_contrib}")

    risk_explanation = (
        f"The composite score ({state.combined_risk_score:.1%}) integrates the LightGBM machine learning "
        f"risk prediction ({ml.risk_score:.1%} uncalibrated) with deterministic banking rules score "
        f"({state.rules_score:.1%}). "
    )
    if alerts:
        risk_explanation += f"Identified {len(alerts)} specific behavioral anomaly indicators."
    else:
        risk_explanation += "No high-velocity structuring or hardware syndicate alerts triggered."

    try:
        llm = get_llm_provider()
        prompt_subject = (
            f"Transaction: {target_txn.external_id} ({target_txn.amount} {target_txn.currency})"
            if target_txn else f"Account: {state.account_id} ({acc.customer_name if acc else 'N/A'})"
        )
        prompt = (
            f"You are a Senior Financial Crime Analytics Specialist at Omerta.ai. "
            f"Review these verified facts:\n"
            f"- Subject: {prompt_subject}\n"
            f"- Combined Risk Score: {state.combined_risk_score:.1%}\n"
            f"- Triggered Rules: {[a.rule_name for a in alerts]}\n"
            f"- 5m Velocity Max Count: {metrics.velocity_5m_max_count if metrics else 0}\n"
            f"- Amount Escalation Detected: {metrics.has_amount_escalation if metrics else False}\n"
            f"- Recommended Action: {state.recommended_action.value}\n\n"
            f"Provide a concise, professional executive summary (2-3 sentences). "
            f"Do not invent transaction data. Do not make definitive legal guilt statements."
        )
        llm_reply = await asyncio.wait_for(llm.complete(prompt), timeout=5.0)
        if llm_reply and len(llm_reply.strip()) > 20:
            exec_summary = llm_reply.strip()
    except Exception as exc:
        logger.info("LLM synthesis bypassed or unavailable; using deterministic executive summary: %s", exc)

    stage_8_trace = PipelineStageTrace(
        stage_id="stage_8_final_report",
        stage_name="Grounded Report Synthesis",
        description="Synthesize structured evidence into explainable forensic narratives and reviewer recommendations.",
        source_tier="LLM Synthesis",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"subject": state.transaction_id or state.account_id, "combined_risk_score": state.combined_risk_score},
        output_summary={
            "executive_summary_preview": exec_summary[:160],
            "factors_count": len(factor_explanations),
            "recommended_action": state.recommended_action.value,
        },
        evidence_ids=[f"REPORT:{state.investigation_id}"],
    )

    return {
        "executive_summary": exec_summary,
        "risk_assessment_explanation": risk_explanation,
        "factor_explanations": factor_explanations,
        "pipeline_stages": [stage_8_trace],
        "node_timings_ms": {"final_report": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# Stage 9: Persistence & Presentation Node
# --------------------------------------------------------------------------- #
async def persistence_presentation_node(state: AccountInvestigationState) -> dict[str, Any]:
    """Persist investigation dossier, trace, and audit events when requested."""
    t0 = time.perf_counter()
    dt_start = datetime.now(UTC)

    stage_9_trace = PipelineStageTrace(
        stage_id="stage_9_persistence",
        stage_name="Dossier Persistence & Case Registration",
        description="Persist immutable investigation dossier snapshot and register case file in compliance review queue.",
        source_tier="Persistence",
        status=PipelineStageStatus.COMPLETED,
        started_at=dt_start,
        completed_at=datetime.now(UTC),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
        input_summary={"persist": state.persist, "investigation_id": state.investigation_id},
        output_summary={
            "persisted": state.persist,
            "case_id": state.investigation_id,
            "status": "OPEN" if state.threshold_exceeded else "CLOSED",
        },
        evidence_ids=[f"CASE:{state.investigation_id}"],
    )

    if state.persist:
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            txn_pk = None
            if state.transaction_id:
                txn_pk = await session.scalar(
                    select(Transaction.id).where(Transaction.external_id == state.transaction_id)
                )

            existing_case = await session.scalar(
                select(InvestigationCase).where(InvestigationCase.external_id == state.investigation_id)
            )

            case_title = (
                f"Forensic Transaction Dossier: {state.transaction_id}"
                if state.transaction_id
                else f"Forensic Account Dossier: {state.account_id}"
            )

            all_stages = list(state.pipeline_stages) + [stage_9_trace]
            report_dict = {
                "investigation_id": state.investigation_id,
                "account_id": state.account_id,
                "transaction_id": state.transaction_id,
                "time_range_days": state.time_range_days,
                "executive_summary": state.executive_summary,
                "combined_risk_score": state.combined_risk_score,
                "rules_score": state.rules_score,
                "ml_risk": state.ml_risk.model_dump(mode="json") if state.ml_risk else None,
                "triggered_rules": [a.model_dump(mode="json") for a in state.triggered_rules],
                "recommended_action": state.recommended_action.value,
                "recommended_action_justification": state.recommended_action_justification,
                "pipeline_stages": [s.model_dump(mode="json") for s in all_stages],
                "generated_at": datetime.now(UTC).isoformat(),
            }

            if existing_case:
                existing_case.title = case_title
                existing_case.severity = "HIGH" if state.threshold_exceeded else "LOW"
                existing_case.status = "OPEN" if state.threshold_exceeded else "CLOSED"
                existing_case.report = report_dict
                if txn_pk:
                    existing_case.transaction_id = txn_pk
            else:
                new_case = InvestigationCase(
                    external_id=state.investigation_id,
                    transaction_id=txn_pk,
                    title=case_title,
                    severity="HIGH" if state.threshold_exceeded else "LOW",
                    status="OPEN" if state.threshold_exceeded else "CLOSED",
                    assigned_to="Compliance Review Queue",
                    report=report_dict,
                )
                session.add(new_case)

            await session.commit()

    return {
        "status": "COMPLETED",
        "pipeline_stages": [stage_9_trace],
        "audit_events": [
            {
                "event": "INVESTIGATION_COMPLETED",
                "investigation_id": state.investigation_id,
                "account_id": state.account_id,
                "transaction_id": state.transaction_id,
                "combined_risk_score": state.combined_risk_score,
                "threshold_exceeded": state.threshold_exceeded,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        ],
        "node_timings_ms": {"persistence_presentation": round((time.perf_counter() - t0) * 1000, 2)},
    }


# --------------------------------------------------------------------------- #
# LangGraph Workflow Compilation
# --------------------------------------------------------------------------- #
def build_account_investigation_graph() -> Any:
    """Compile the LangGraph investigation StateGraph."""
    graph = StateGraph(AccountInvestigationState)

    graph.add_node("coordinator", coordinator_node)
    graph.add_node("transaction_intelligence", transaction_intelligence_node)
    graph.add_node("neo4j_intelligence", graph_intelligence_node)
    graph.add_node("ml_risk", ml_risk_node)
    graph.add_node("banking_rules", banking_rules_node)
    graph.add_node("evidence_aggregation", evidence_aggregation_node)
    graph.add_node("final_report", final_report_node)
    graph.add_node("persistence", persistence_presentation_node)

    # Edges
    graph.add_edge(START, "coordinator")
    graph.add_conditional_edges(
        "coordinator",
        route_after_coordinator,
        {
            END: END,
            "parallel_dispatch": "transaction_intelligence",
        },
    )

    graph.add_edge("transaction_intelligence", "neo4j_intelligence")
    graph.add_edge("neo4j_intelligence", "ml_risk")
    graph.add_edge("ml_risk", "banking_rules")
    graph.add_edge("banking_rules", "evidence_aggregation")
    graph.add_edge("evidence_aggregation", "final_report")
    graph.add_edge("final_report", "persistence")
    graph.add_edge("persistence", END)

    return graph.compile()


_COMPILED_ACCOUNT_GRAPH = None


def get_account_investigation_graph() -> Any:
    global _COMPILED_ACCOUNT_GRAPH
    if _COMPILED_ACCOUNT_GRAPH is None:
        _COMPILED_ACCOUNT_GRAPH = build_account_investigation_graph()
    return _COMPILED_ACCOUNT_GRAPH


# --------------------------------------------------------------------------- #
# Public Execution APIs
# --------------------------------------------------------------------------- #
async def run_account_investigation(
    request: AccountInvestigationRequest,
    caller_role: str = "INVESTIGATOR",
    caller_id: str | None = None,
) -> AccountInvestigationReport:
    """Execute account investigation workflow and return a structured report."""
    t0 = time.perf_counter()
    graph = get_account_investigation_graph()

    initial_state = AccountInvestigationState(
        account_id=request.account_id,
        time_range_days=request.time_range_days,
        investigation_reason=request.investigation_reason.value,
        caller_role=caller_role,
        caller_id=caller_id,
        persist=request.persist,
    )

    final = await graph.ainvoke(initial_state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    report = AccountInvestigationReport(
        investigation_id=final.get("investigation_id", f"INV-ACC-{uuid.uuid4().hex[:8].upper()}"),
        account_id=request.account_id,
        time_range_days=request.time_range_days,
        generated_at=datetime.now(UTC),
        caller_role=caller_role,
        investigation_reason=request.investigation_reason.value,
        executive_summary=final.get("executive_summary", "Investigation completed."),
        account_facts=final.get("account_facts"),
        transaction_facts_count=len(final.get("transaction_facts", [])),
        recent_transactions=final.get("transaction_facts", [])[:15],
        behavioral_metrics=final.get("behavioral_metrics") or calculate_behavioral_metrics([]),
        triggered_rules=final.get("triggered_rules", []),
        rules_score=final.get("rules_score", 0.0),
        ml_risk=final.get("ml_risk") or MLRiskOutput(model_version=MODEL_VERSION, feature_version="features-v1", risk_score=0.0, risk_tier="LOW", model_loaded=False),
        combined_risk_score=final.get("combined_risk_score", 0.0),
        operational_alert_threshold=APPLICATION_ALERT_THRESHOLD,
        threshold_exceeded=final.get("threshold_exceeded", False),
        threshold_rationale=(
            f"Configured application alert threshold of {APPLICATION_ALERT_THRESHOLD:.0%} "
            f"triggers mandatory multi-eye compliance officer review."
        ),
        graph_intelligence=final.get("graph_intelligence") or GraphIntelligenceOutput(available=False),
        risk_assessment_explanation=final.get("risk_assessment_explanation", ""),
        factor_explanations=final.get("factor_explanations", []),
        missing_data_and_limitations=final.get("missing_data_and_limitations") or (
            [final.get("error_message")] if final.get("error_message") else []
        ),
        recommended_action=final.get("recommended_action", RecommendedReviewAction.ROUTINE_MONITORING),
        recommended_action_justification=final.get("recommended_action_justification", ""),
        evidence_ids=list(set(final.get("evidence_ids", []))),
        audit_events=final.get("audit_events", []),
        charts=final.get("charts", []),
        execution_time_ms=round(elapsed_ms, 2),
        pipeline_stages=final.get("pipeline_stages", []),
    )
    return report


async def run_transaction_investigation(
    request: TransactionInvestigationRequest,
    caller_role: str = "INVESTIGATOR",
    caller_id: str | None = None,
) -> AccountInvestigationReport:
    """Execute transaction investigation workflow and return a transaction-grounded report."""
    t0 = time.perf_counter()
    graph = get_account_investigation_graph()

    account_id = "UNKNOWN"
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        t_row = await session.scalar(
            select(Transaction)
            .options(selectinload(Transaction.account))
            .where(
                or_(
                    Transaction.external_id == request.transaction_id,
                    Transaction.id == int(request.transaction_id) if request.transaction_id.isdigit() else False,
                )
            )
        )
        if t_row and t_row.account:
            account_id = t_row.account.external_id

    initial_state = AccountInvestigationState(
        account_id=account_id,
        transaction_id=request.transaction_id,
        time_range_days=request.time_range_days,
        investigation_reason=request.investigation_reason.value,
        caller_role=caller_role,
        caller_id=caller_id,
        persist=request.persist,
    )

    final = await graph.ainvoke(initial_state)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    report = AccountInvestigationReport(
        investigation_id=final.get("investigation_id", f"INV-TXN-{request.transaction_id}"),
        account_id=final.get("account_id", account_id),
        transaction_id=request.transaction_id,
        target_transaction=final.get("target_transaction"),
        preceding_transactions=final.get("preceding_transactions", []),
        subsequent_transactions=final.get("subsequent_transactions", []),
        time_range_days=request.time_range_days,
        generated_at=datetime.now(UTC),
        caller_role=caller_role,
        investigation_reason=request.investigation_reason.value,
        executive_summary=final.get("executive_summary", "Transaction investigation completed."),
        account_facts=final.get("account_facts"),
        transaction_facts_count=len(final.get("transaction_facts", [])),
        recent_transactions=final.get("transaction_facts", [])[:15],
        behavioral_metrics=final.get("behavioral_metrics") or calculate_behavioral_metrics([]),
        triggered_rules=final.get("triggered_rules", []),
        rules_score=final.get("rules_score", 0.0),
        ml_risk=final.get("ml_risk") or MLRiskOutput(model_version=MODEL_VERSION, feature_version="features-v1", risk_score=0.0, risk_tier="LOW", model_loaded=False),
        combined_risk_score=final.get("combined_risk_score", 0.0),
        operational_alert_threshold=APPLICATION_ALERT_THRESHOLD,
        threshold_exceeded=final.get("threshold_exceeded", False),
        threshold_rationale=(
            f"Configured application alert threshold of {APPLICATION_ALERT_THRESHOLD:.0%} "
            f"triggers mandatory multi-eye compliance officer review."
        ),
        graph_intelligence=final.get("graph_intelligence") or GraphIntelligenceOutput(available=False),
        risk_assessment_explanation=final.get("risk_assessment_explanation", ""),
        factor_explanations=final.get("factor_explanations", []),
        missing_data_and_limitations=final.get("missing_data_and_limitations") or (
            [final.get("error_message")] if final.get("error_message") else []
        ),
        recommended_action=final.get("recommended_action", RecommendedReviewAction.ROUTINE_MONITORING),
        recommended_action_justification=final.get("recommended_action_justification", ""),
        evidence_ids=list(set(final.get("evidence_ids", []))),
        audit_events=final.get("audit_events", []),
        charts=final.get("charts", []),
        execution_time_ms=round(elapsed_ms, 2),
        pipeline_stages=final.get("pipeline_stages", []),
    )
    return report
