"""Dedicated Transaction History Intelligence Agent for Omerta.ai.

Calculates rolling statistical baselines, velocity windows (5m, 15m, 60m, 24h, 7d, 30d),
counterparty relationships, and amount escalation factors from persisted relational ledger records.
Strictly excludes current transaction from pre-transaction historical metrics.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import logging
import math
import time
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.investigation.agent_schemas import (
    AgentDataQuality,
    AgentExecutionStatus,
    AgentFinding,
    SpecialistAgentResult,
    TransactionHistoryMetrics,
)
from infrastructure.database.models import Account, Transaction

logger = logging.getLogger(__name__)


class TransactionHistoryAgent:
    """Specialist agent analyzing customer transaction history and velocity patterns."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def analyze(
        self,
        account_id: int,
        current_amount: float,
        current_timestamp: datetime | None = None,
        recipient_account_id: int | None = None,
        current_transaction_id: int | None = None,
    ) -> SpecialistAgentResult:
        """Execute historical intelligence extraction against verified ledger records."""
        t_start = time.perf_counter()
        started_at = datetime.now(UTC)
        anchor_time = current_timestamp or started_at

        # Ensure anchor_time is timezone-aware UTC
        if anchor_time.tzinfo is None:
            anchor_time = anchor_time.replace(tzinfo=UTC)

        # 1. Fetch Account Details (Age, Balance)
        acc_stmt = select(Account).where(Account.id == account_id).limit(1)
        account = await self.session.scalar(acc_stmt)
        available_balance = float(account.balance) if account else 0.0
        account_age_days = 0
        if account and hasattr(account, "created_at") and account.created_at:
            created_dt = account.created_at
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=UTC)
            account_age_days = max(0, (anchor_time - created_dt).days)

        # 2. Query Pre-Transaction Historical Outgoing Transactions (up to 30 days)
        # Excludes current transaction strictly (t.timestamp < anchor_time or t.id != current_transaction_id)
        thirty_days_ago = anchor_time - timedelta(days=30)
        history_filters = [
            Transaction.account_id == account_id,
            Transaction.timestamp < anchor_time,
            Transaction.status == "COMPLETED",
        ]
        if current_transaction_id:
            history_filters.append(Transaction.id != current_transaction_id)

        history_stmt = (
            select(Transaction)
            .where(and_(*history_filters))
            .order_by(Transaction.timestamp.desc())
        )
        res = await self.session.scalars(history_stmt)
        tx_history = res.all()

        # 3. Query Pre-Transaction Incoming Transactions (30 days)
        incoming_stmt = (
            select(Transaction)
            .where(
                and_(
                    Transaction.recipient_account_id == account_id,
                    Transaction.timestamp < anchor_time,
                    Transaction.status == "COMPLETED",
                )
            )
        )
        res_inc = await self.session.scalars(incoming_stmt)
        tx_incoming = res_inc.all()
        incoming_total_30d = sum(float(t.amount) for t in tx_incoming)

        # 4. Check for Failed / Reversed Transactions (30 days)
        failed_stmt = (
            select(func.count(Transaction.id))
            .where(
                and_(
                    Transaction.account_id == account_id,
                    Transaction.timestamp < anchor_time,
                    Transaction.status.in_(["FAILED", "REVERSED", "CANCELLED"]),
                )
            )
        )
        failed_reversed_count = await self.session.scalar(failed_stmt) or 0

        # 5. Extract Historical Amounts & Rolling Metrics
        outgoing_amounts = [float(t.amount) for t in tx_history]
        total_history_count = len(outgoing_amounts)

        # Rolling window partitions
        five_min_ago = anchor_time - timedelta(minutes=5)
        fifteen_min_ago = anchor_time - timedelta(minutes=15)
        sixty_min_ago = anchor_time - timedelta(minutes=60)
        twenty_four_h_ago = anchor_time - timedelta(hours=24)
        seven_days_ago = anchor_time - timedelta(days=7)

        tx_5m = [t for t in tx_history if t.timestamp >= five_min_ago]
        tx_15m = [t for t in tx_history if t.timestamp >= fifteen_min_ago]
        tx_60m = [t for t in tx_history if t.timestamp >= sixty_min_ago]
        tx_24h = [t for t in tx_history if t.timestamp >= twenty_four_h_ago]
        tx_7d = [t for t in tx_history if t.timestamp >= seven_days_ago]

        # Time since last completed transaction
        time_since_last_sec: float | None = None
        if tx_history:
            last_ts = tx_history[0].timestamp
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=UTC)
            time_since_last_sec = max(0.0, (anchor_time - last_ts).total_seconds())

        # Beneficiary Analysis
        historical_beneficiaries = {t.recipient_account_id for t in tx_history}
        distinct_beneficiaries_count = len(historical_beneficiaries)
        is_first_with_beneficiary = False
        if recipient_account_id:
            is_first_with_beneficiary = recipient_account_id not in historical_beneficiaries

        # Statistical Calculations (Average, Median, Max, P95)
        if total_history_count >= 1:
            historical_avg = sum(outgoing_amounts) / total_history_count
            historical_max = max(outgoing_amounts)
            sorted_amounts = sorted(outgoing_amounts)
            # Median
            mid = total_history_count // 2
            if total_history_count % 2 == 0:
                historical_median = (sorted_amounts[mid - 1] + sorted_amounts[mid]) / 2.0
            else:
                historical_median = sorted_amounts[mid]

            # 95th Percentile
            if total_history_count >= 5:
                p95_idx = min(total_history_count - 1, int(math.ceil(0.95 * total_history_count)) - 1)
                historical_p95 = sorted_amounts[p95_idx]
            else:
                historical_p95 = historical_max
        else:
            historical_avg = current_amount
            historical_median = current_amount
            historical_max = current_amount
            historical_p95 = current_amount

        # Compute Ratios
        amount_to_avg_ratio = round(current_amount / max(1.0, historical_avg), 2)
        amount_to_p95_ratio = round(current_amount / max(1.0, historical_p95), 2)

        metrics = TransactionHistoryMetrics(
            previous_transactions_5m=len(tx_5m),
            outgoing_total_5m=sum(float(t.amount) for t in tx_5m),
            previous_transactions_15m=len(tx_15m),
            outgoing_total_15m=sum(float(t.amount) for t in tx_15m),
            previous_transactions_60m=len(tx_60m),
            outgoing_total_60m=sum(float(t.amount) for t in tx_60m),
            previous_transactions_24h=len(tx_24h),
            outgoing_total_24h=sum(float(t.amount) for t in tx_24h),
            previous_transactions_7d=len(tx_7d),
            outgoing_total_7d=sum(float(t.amount) for t in tx_7d),
            previous_transactions_30d=total_history_count,
            outgoing_total_30d=sum(outgoing_amounts),
            incoming_total_30d=incoming_total_30d,
            historical_average_amount=round(historical_avg, 2),
            historical_median_amount=round(historical_median, 2),
            historical_max_amount=round(historical_max, 2),
            historical_p95_amount=round(historical_p95, 2),
            current_amount=current_amount,
            amount_to_average_ratio=amount_to_avg_ratio,
            amount_to_p95_ratio=amount_to_p95_ratio,
            withdrawal_count=total_history_count,
            withdrawal_total=sum(outgoing_amounts),
            distinct_beneficiaries_count=distinct_beneficiaries_count,
            is_first_transaction_with_beneficiary=is_first_with_beneficiary,
            failed_reversed_count=failed_reversed_count,
            time_since_last_transaction_seconds=time_since_last_sec,
            account_age_days=account_age_days,
            available_balance=available_balance,
        )

        # 6. Evaluate Findings & Compute Agent Risk Score
        findings: list[AgentFinding] = []
        points_breakdown: dict[str, float] = {}
        base_score = 0.0

        if total_history_count < 3:
            # Insufficient history baseline
            data_quality = AgentDataQuality(
                history_available=total_history_count > 0,
                record_count=total_history_count,
                lookback_days=30,
                is_sufficient=False,
                quality_notes="INSUFFICIENT_HISTORY: Fewer than 3 historical records. Baseline uncalibrated.",
            )
            # Moderately elevated caution score for new accounts without history
            base_score = 25.0
            points_breakdown["INSUFFICIENT_HISTORY"] = 25.0
            findings.append(
                AgentFinding(
                    rule_id="HIST-NEW-ACC-001",
                    rule_name="Uncalibrated Baseline / New Account",
                    points=25.0,
                    severity="LOW",
                    reason=f"Account has only {total_history_count} previous recorded transaction(s). Operating under conservative baseline.",
                    evidence_ids=[f"ACC:{account_id}"],
                    observed_values={"history_count": total_history_count},
                )
            )
        else:
            data_quality = AgentDataQuality(
                history_available=True,
                record_count=total_history_count,
                lookback_days=30,
                is_sufficient=True,
                quality_notes=f"Established baseline over {total_history_count} transactions across 30 days.",
            )

            # Finding: Outlier Amount Ratio
            if amount_to_avg_ratio >= 3.0:
                pts = min(40.0, 15.0 + (amount_to_avg_ratio - 3.0) * 4.0)
                base_score += pts
                points_breakdown["HIST-AMOUNT-001"] = pts
                findings.append(
                    AgentFinding(
                        rule_id="HIST-AMOUNT-001",
                        rule_name="Elevated Amount Deviation",
                        points=pts,
                        severity="HIGH" if amount_to_avg_ratio >= 5.0 else "MEDIUM",
                        reason=f"Current amount is {amount_to_avg_ratio}x the customer's historical average ({historical_avg:,.2f}).",
                        evidence_ids=[f"HIST:AVG:{historical_avg}"],
                        observed_values={"current": current_amount, "average": historical_avg, "ratio": amount_to_avg_ratio},
                    )
                )

            # Finding: 5-Minute Velocity Surge
            if metrics.previous_transactions_5m >= 3:
                pts = 35.0
                base_score += pts
                points_breakdown["HIST-VEL-5M"] = pts
                findings.append(
                    AgentFinding(
                        rule_id="HIST-VEL-5M",
                        rule_name="5-Minute Rolling Velocity Surge",
                        points=pts,
                        severity="HIGH",
                        reason=f"Observed {metrics.previous_transactions_5m} transactions in 5 minutes totaling {metrics.outgoing_total_5m:,.2f}.",
                        evidence_ids=[f"HIST:VEL:5M:{metrics.previous_transactions_5m}"],
                        observed_values={"count_5m": metrics.previous_transactions_5m, "volume_5m": metrics.outgoing_total_5m},
                    )
                )

            # Finding: First-Time Beneficiary with Elevated Amount
            if is_first_with_beneficiary and current_amount >= 20000.0:
                pts = 25.0
                base_score += pts
                points_breakdown["HIST-BENEF-001"] = pts
                findings.append(
                    AgentFinding(
                        rule_id="HIST-BENEF-001",
                        rule_name="First-Time Beneficiary Elevated Transfer",
                        points=pts,
                        severity="HIGH",
                        reason=f"First recorded transfer to beneficiary account {recipient_account_id} with elevated amount ({current_amount:,.2f}).",
                        evidence_ids=[f"ACC:RECIPIENT:{recipient_account_id}"],
                        observed_values={"recipient_account_id": recipient_account_id, "amount": current_amount},
                    )
                )

        final_agent_score = round(min(100.0, base_score), 2)
        duration_ms = round((time.perf_counter() - t_start) * 1000.0, 2)
        completed_at = datetime.now(UTC)

        return SpecialistAgentResult(
            agent_name="Transaction History Agent",
            agent_version="1.0.0",
            status=AgentExecutionStatus.COMPLETED,
            score=final_agent_score,
            score_scale="0-100",
            raw_metrics=metrics.model_dump(),
            findings=findings,
            points_breakdown=points_breakdown,
            evidence_ids=[f"ACC:{account_id}"] + [f"TXN:{t.external_id}" for t in tx_history[:5]],
            data_quality=data_quality,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
        )
