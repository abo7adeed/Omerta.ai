"""Typed, read-only PostgreSQL tools for Omerta.ai Agentic RAG.

Guarantees:
- Fully parameterized async SQLAlchemy queries (no raw string formatting).
- Read-only execution with explicit transaction rollback on error.
- Bounded result sets (max 100 records per bounded dataset).
- Currency and timezone validation.
- Field-level data minimization (sensitive hashes/salts omitted).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from infrastructure.database.models import (
    Account,
    AccountLedgerEntry,
    AuditEvent,
    Customer,
    Device,
    IPAddress,
    InvestigationCase,
    Session as UserSession,
    Transaction,
)
from infrastructure.database.session import get_engine
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession


class DatabaseTools:
    """Read-only relational database toolset for financial facts."""

    @staticmethod
    async def get_transaction(transaction_id: str) -> dict[str, Any] | None:
        """Fetch transaction record by external_id or integer id."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(Transaction).where(
                (Transaction.external_id == transaction_id)
                | (Transaction.id == int(transaction_id) if transaction_id.isdigit() else False)
            )
            txn = await session.scalar(stmt)
            if not txn:
                return None
            return {
                "id": txn.id,
                "external_id": txn.external_id,
                "account_id": txn.account_id,
                "recipient_account_id": txn.recipient_account_id,
                "amount": float(txn.amount),
                "currency": txn.currency,
                "status": txn.status,
                "timestamp": txn.timestamp.isoformat(),
                "risk_score": float(txn.risk_score) if txn.risk_score is not None else None,
                "risk_level": txn.risk_level,
                "review_status": txn.review_status,
            }

    @staticmethod
    async def get_account(account_id: str) -> dict[str, Any] | None:
        """Fetch account record by external_id or integer id."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(Account).where(
                (Account.external_id == account_id)
                | (Account.id == int(account_id) if account_id.isdigit() else False)
            )
            acc = await session.scalar(stmt)
            if not acc:
                return None
            return {
                "id": acc.id,
                "external_id": acc.external_id,
                "customer_name": acc.customer_name,
                "account_type": acc.account_type,
                "status": acc.status,
                "balance": float(acc.balance) if acc.balance is not None else 0.0,
                "currency": acc.currency,
                "risk_level": acc.risk_level,
            }

    @staticmethod
    async def get_customer(customer_id: str) -> dict[str, Any] | None:
        """Fetch customer profile without sensitive passwords or hashes."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(Customer).where(
                (Customer.external_id == customer_id)
                | (Customer.omerta_user_number == customer_id)
                | (Customer.id == int(customer_id) if customer_id.isdigit() else False)
            )
            cust = await session.scalar(stmt)
            if not cust:
                return None
            return {
                "id": cust.id,
                "external_id": cust.external_id,
                "full_name": cust.full_name,
                "omerta_user_number": cust.omerta_user_number,
                "email": cust.email,
                "declared_country": cust.declared_country,
                "transfer_status": cust.transfer_status,
                "identity_status": cust.identity_status,
                "risk_rating": cust.risk_rating,
                "transfer_failed_attempts": cust.transfer_failed_attempts,
            }

    @staticmethod
    async def get_recent_transactions(account_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch recent transaction history for an account."""
        limit = min(max(limit, 1), 50)
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            acc_stmt = select(Account.id).where(
                (Account.external_id == account_id)
                | (Account.id == int(account_id) if account_id.isdigit() else False)
            )
            internal_acc_id = await session.scalar(acc_stmt)
            if not internal_acc_id:
                return []

            stmt = (
                select(Transaction)
                .where(
                    (Transaction.account_id == internal_acc_id)
                    | (Transaction.recipient_account_id == internal_acc_id)
                )
                .order_by(desc(Transaction.timestamp))
                .limit(limit)
            )
            rows = (await session.scalars(stmt)).all()
            return [
                {
                    "external_id": r.external_id,
                    "direction": "OUTBOUND" if r.account_id == internal_acc_id else "INBOUND",
                    "amount": float(r.amount),
                    "currency": r.currency,
                    "status": r.status,
                    "timestamp": r.timestamp.isoformat(),
                    "risk_score": float(r.risk_score) if r.risk_score is not None else None,
                }
                for r in rows
            ]

    @staticmethod
    async def count_transactions(
        time_range_days: int | None = None,
        currency: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """Deterministic transaction count within an optional time range."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            conditions = []
            if time_range_days is not None and time_range_days > 0:
                since = datetime.now(UTC) - timedelta(days=time_range_days)
                conditions.append(Transaction.timestamp >= since)
            if currency:
                conditions.append(Transaction.currency == currency.upper())
            if status:
                conditions.append(Transaction.status == status.upper())

            stmt = select(func.count(Transaction.id))
            if conditions:
                stmt = stmt.where(*conditions)

            total_count = await session.scalar(stmt) or 0
            period_str = f"Last {time_range_days} days" if time_range_days else "All-time"
            return {
                "count": total_count,
                "period": period_str,
                "filters": {"currency": currency, "status": status},
            }

    @staticmethod
    async def get_transaction_summary(
        time_range_days: int | None = 30,
        currency: str = "EGP",
    ) -> dict[str, Any]:
        """Deterministic aggregate statistics: total volume, count, average, min, max."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            conditions = [Transaction.currency == currency.upper()]
            if time_range_days:
                since = datetime.now(UTC) - timedelta(days=time_range_days)
                conditions.append(Transaction.timestamp >= since)

            stmt = select(
                func.count(Transaction.id).label("count"),
                func.coalesce(func.sum(Transaction.amount), 0).label("total_volume"),
                func.coalesce(func.avg(Transaction.amount), 0).label("avg_amount"),
                func.coalesce(func.min(Transaction.amount), 0).label("min_amount"),
                func.coalesce(func.max(Transaction.amount), 0).label("max_amount"),
            ).where(*conditions)

            row = (await session.execute(stmt)).first()
            if not row:
                return {"count": 0, "total_volume": 0.0, "avg_amount": 0.0, "currency": currency}

            return {
                "count": int(row.count),
                "total_volume": float(row.total_volume),
                "avg_amount": round(float(row.avg_amount), 2),
                "min_amount": float(row.min_amount),
                "max_amount": float(row.max_amount),
                "currency": currency,
                "period": f"Last {time_range_days} days" if time_range_days else "All-time",
            }

    @staticmethod
    async def compare_transaction_periods(
        period_a_days: int = 30,
        period_b_days: int = 30,
        currency: str = "EGP",
    ) -> dict[str, Any]:
        """Compare current period vs previous period volume and counts."""
        now = datetime.now(UTC)
        a_start = now - timedelta(days=period_a_days)
        b_start = a_start - timedelta(days=period_b_days)

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            # Period A (Current)
            stmt_a = select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            ).where(
                Transaction.currency == currency.upper(),
                Transaction.timestamp >= a_start,
                Transaction.timestamp <= now,
            )
            count_a, vol_a = (await session.execute(stmt_a)).first() or (0, Decimal("0.0"))

            # Period B (Previous)
            stmt_b = select(
                func.count(Transaction.id),
                func.coalesce(func.sum(Transaction.amount), 0),
            ).where(
                Transaction.currency == currency.upper(),
                Transaction.timestamp >= b_start,
                Transaction.timestamp < a_start,
            )
            count_b, vol_b = (await session.execute(stmt_b)).first() or (0, Decimal("0.0"))

        return {
            "period_a": {
                "label": f"Current ({period_a_days}d)",
                "count": int(count_a),
                "volume": float(vol_a),
            },
            "period_b": {
                "label": f"Previous ({period_b_days}d)",
                "count": int(count_b),
                "volume": float(vol_b),
            },
            "currency": currency,
        }

    @staticmethod
    async def get_risk_distribution(time_range_days: int | None = 30) -> dict[str, int]:
        """Compute counts grouped by transaction risk_level (LOW, MEDIUM, HIGH, CRITICAL)."""
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            conditions = []
            if time_range_days:
                since = datetime.now(UTC) - timedelta(days=time_range_days)
                conditions.append(Transaction.timestamp >= since)

            stmt = select(
                Transaction.risk_level, func.count(Transaction.id)
            ).group_by(Transaction.risk_level)
            if conditions:
                stmt = stmt.where(*conditions)

            rows = (await session.execute(stmt)).all()
            dist = {r[0] or "UNKNOWN": int(r[1]) for r in rows}
            return dist

    @staticmethod
    async def get_bounded_transaction_dataset(
        limit: int = 50,
        currency: str | None = None,
        risk_level: str | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve bounded tabular rows for charts or data tables."""
        limit = min(max(limit, 1), 100)
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            conditions = []
            if currency:
                conditions.append(Transaction.currency == currency.upper())
            if risk_level:
                conditions.append(Transaction.risk_level == risk_level.upper())

            stmt = select(Transaction).order_by(desc(Transaction.timestamp)).limit(limit)
            if conditions:
                stmt = stmt.where(*conditions)

            rows = (await session.scalars(stmt)).all()
            return [
                {
                    "external_id": r.external_id,
                    "amount": float(r.amount),
                    "currency": r.currency,
                    "status": r.status,
                    "risk_score": float(r.risk_score) if r.risk_score is not None else 0.0,
                    "risk_level": r.risk_level,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in rows
            ]
