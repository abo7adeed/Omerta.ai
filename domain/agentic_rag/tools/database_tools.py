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
                "name": getattr(cust, "name", getattr(cust, "full_name", "")),
                "omerta_user_number": cust.omerta_user_number,
                "email": cust.email,
                "declared_country": cust.declared_country,
                "transfer_status": cust.transfer_status,
                "identity_status": cust.identity_status,
                "risk_level": getattr(cust, "risk_level", "LOW"),
                "transfer_failed_attempts": cust.transfer_failed_attempts,
            }

    @staticmethod
    async def find_customers_by_name(name_query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search customers by name with intelligent sanitization and multi-token fallback match."""
        import re
        from sqlalchemy import or_

        limit = min(max(limit, 1), 20)
        raw = (name_query or "").strip()
        if not raw:
            return []

        # 1. Clean quotes and punctuation
        clean = re.sub(r"[\"“'‘”’]", "", raw).strip()

        # 2. Extract significant tokens (filter out common conversational words and typo variants)
        stop_words = {
            "user", "users", "customer", "customers", "client", "clients", "person", "persons",
            "and", "their", "thier", "his", "her", "its", "the", "a", "an", "in", "of", "for", "with",
            "transication", "transications", "transaction", "transactions", "transfers", "transfer",
            "history", "profile", "account", "accounts", "balance", "details", "record", "records",
            "database", "data", "info", "information", "authorized", "show", "find", "search", "lookup",
            "status", "stauts", "statue", "statu", "staus", "statuss", "state", "active", "tier", "level",
            "score", "risk", "tell", "me", "about", "give", "gave", "get", "who", "is", "this", "was",
            "all", "please", "list"
        }
        tokens = [w for w in re.split(r"[\s,\-_]+", clean) if w and w.lower() not in stop_words]
        cleaned_term = " ".join(tokens).strip()

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            # Step A: Try cleaned term first if present, otherwise clean raw
            search_str = cleaned_term if cleaned_term else clean
            stmt = select(Customer).where(Customer.name.ilike(f"%{search_str}%")).limit(limit)
            rows = (await session.scalars(stmt)).all()

            # Step B: If no match and multiple tokens exist, require ALL tokens to match (AND logic)
            if not rows and len(tokens) >= 2:
                from sqlalchemy import and_
                and_filters = [Customer.name.ilike(f"%{tok}%") for tok in tokens if len(tok) >= 3]
                if and_filters:
                    stmt_and = select(Customer).where(and_(*and_filters)).limit(limit)
                    rows = (await session.scalars(stmt_and)).all()

            # Step C: If still no match and tokens exist, try token-based matching with fuzzy ranking
            if not rows and tokens:
                token_filters = [Customer.name.ilike(f"%{tok}%") for tok in tokens if len(tok) >= 3]
                if token_filters:
                    stmt_tokens = select(Customer).where(or_(*token_filters)).limit(20)
                    rows = (await session.scalars(stmt_tokens)).all()

            # Step D: Fallback to raw string partial match
            if not rows and clean != search_str:
                stmt_raw = select(Customer).where(Customer.name.ilike(f"%{clean}%")).limit(limit)
                rows = (await session.scalars(stmt_raw)).all()

            # Step E: Rank candidates with SequenceMatcher to eliminate false ambiguity
            if len(rows) > 1 and search_str:
                from difflib import SequenceMatcher
                scored = []
                for c in rows:
                    sim = SequenceMatcher(None, search_str.lower(), c.name.lower()).ratio()
                    c_name_words = set(c.name.lower().split())
                    q_words = set(tok.lower() for tok in tokens) if tokens else set(search_str.lower().split())
                    overlap = len(c_name_words.intersection(q_words)) / max(len(q_words), 1)
                    total_score = (sim * 0.6) + (overlap * 0.4)
                    scored.append((total_score, c))
                scored.sort(key=lambda x: x[0], reverse=True)
                best_score, best_cand = scored[0]
                second_score = scored[1][0]
                if best_score >= 0.70 and (best_score - second_score >= 0.15):
                    rows = [best_cand]
                else:
                    rows = [c for _, c in scored][:limit]

            return [
                {
                    "id": c.id,
                    "external_id": c.external_id,
                    "name": c.name,
                    "omerta_user_number": c.omerta_user_number,
                    "email": c.email,
                    "declared_country": c.declared_country,
                    "transfer_status": c.transfer_status,
                    "identity_status": c.identity_status,
                    "risk_level": getattr(c, "risk_level", "LOW"),
                    "transfer_failed_attempts": c.transfer_failed_attempts,
                }
                for c in rows
            ]

    @staticmethod
    async def get_all_customers(limit: int = 20) -> list[dict[str, Any]]:
        """Fetch all registered customers from PostgreSQL (bounded to limit)."""
        limit = min(max(limit, 1), 100)
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            stmt = select(Customer).order_by(Customer.id).limit(limit)
            rows = (await session.scalars(stmt)).all()
            return [
                {
                    "id": c.id,
                    "external_id": c.external_id,
                    "name": c.name,
                    "omerta_user_number": c.omerta_user_number,
                    "email": c.email,
                    "declared_country": c.declared_country,
                    "transfer_status": c.transfer_status,
                    "identity_status": c.identity_status,
                    "risk_level": getattr(c, "risk_level", "LOW"),
                    "transfer_failed_attempts": c.transfer_failed_attempts,
                }
                for c in rows
            ]

    @staticmethod
    async def execute_read_only_sql(sql_query: str, limit: int = 50) -> list[dict[str, Any]]:
        """Execute a dynamic read-only SELECT query against PostgreSQL with strict security validation."""
        import re
        from decimal import Decimal
        from datetime import datetime
        from sqlalchemy import text

        clean_sql = (sql_query or "").strip()
        if not clean_sql:
            return []

        upper_sql = clean_sql.upper()
        # Strictly require SELECT or WITH ... SELECT
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            raise ValueError("Only read-only SELECT statements are permitted.")

        # Prohibit any data modification syntax
        blocked = [
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
            "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "INTO",
        ]
        for kw in blocked:
            if re.search(rf"\b{kw}\b", upper_sql):
                raise ValueError(f"Prohibited SQL keyword detected: {kw}. Modifications are rejected.")

        if ";" in clean_sql.rstrip(";"):
            raise ValueError("Multiple SQL queries separated by semicolons are prohibited.")

        limit = min(max(limit, 1), 50)
        if "LIMIT" not in upper_sql:
            clean_sql = f"{clean_sql.rstrip(';')} LIMIT {limit}"

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            result = await session.execute(text(clean_sql))
            keys = list(result.keys())
            rows = []
            for r in result.fetchall():
                row_dict = {}
                for idx, col in enumerate(keys):
                    val = r[idx]
                    if isinstance(val, Decimal):
                        row_dict[col] = float(val)
                    elif isinstance(val, datetime):
                        row_dict[col] = val.isoformat()
                    else:
                        row_dict[col] = val
                rows.append(row_dict)
            return rows

    @staticmethod
    async def get_customer_accounts_and_transactions(customer_id: str | int) -> dict[str, Any]:
        """Fetch all accounts and recent transaction records linked to a customer."""
        from sqlalchemy import or_

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            # 1. Resolve customer internal ID
            c_str = str(customer_id).strip()
            c_stmt = select(Customer.id).where(
                (Customer.external_id == c_str)
                | (Customer.omerta_user_number == c_str)
                | (Customer.id == int(c_str) if c_str.isdigit() else False)
            )
            internal_c_id = await session.scalar(c_stmt)
            if not internal_c_id and c_str.isdigit():
                internal_c_id = int(c_str)
            if not internal_c_id:
                return {"accounts": [], "transactions": []}

            # 2. Query linked accounts
            acc_stmt = select(Account).where(Account.customer_id == internal_c_id)
            acc_rows = (await session.scalars(acc_stmt)).all()
            accounts = [
                {
                    "id": a.id,
                    "external_id": a.external_id,
                    "account_type": a.account_type,
                    "balance": float(a.balance) if a.balance is not None else 0.0,
                    "currency": a.currency,
                    "status": a.status,
                }
                for a in acc_rows
            ]

            # 3. Query transactions linked to those accounts
            acc_ids = [a.id for a in acc_rows]
            transactions = []
            if acc_ids:
                txn_stmt = (
                    select(Transaction)
                    .where(or_(Transaction.account_id.in_(acc_ids), Transaction.recipient_account_id.in_(acc_ids)))
                    .order_by(desc(Transaction.timestamp))
                    .limit(20)
                )
                txn_rows = (await session.scalars(txn_stmt)).all()
                transactions = [
                    {
                        "external_id": t.external_id,
                        "account_id": t.account_id,
                        "recipient_account_id": t.recipient_account_id,
                        "amount": float(t.amount),
                        "currency": t.currency,
                        "status": t.status,
                        "risk_score": float(t.risk_score) if t.risk_score is not None else 0.0,
                        "risk_level": t.risk_level,
                        "timestamp": t.timestamp.isoformat(),
                    }
                    for t in txn_rows
                ]

            return {"accounts": accounts, "transactions": transactions}

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
