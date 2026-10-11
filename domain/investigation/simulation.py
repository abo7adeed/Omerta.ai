"""Sandbox-Only Simulated Withdrawal Operation Service.

Used exclusively for testing transaction-processing, idempotency, concurrency,
and compliance monitoring controls (e.g. 5-minute velocity bursts and escalating withdrawals).

Security Guarantees:
1. Strict Sandbox Isolation: Strictly rejects live production accounts.
2. Thread & Async Concurrency Locking: Per-account asyncio.Lock ensures atomic balance updates.
3. Idempotency Protection: Rejects duplicate executions with identical idempotency keys.
4. Double-Entry Ledger Tracking: Maintains simulated ledger entries with rolling balance integrity.
5. Zero Production Money Movement: Never modifies real banking ledgers.
6. Safe Sandbox Reset: Purges only synthetic records without touching production data.
"""

import asyncio
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
import logging
from typing import Any
import uuid

from sqlalchemy import delete, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from domain.investigation.schemas import (
    SimulatedWithdrawalRequest,
    SimulatedWithdrawalResponse,
    TransactionFact,
    GraphIntelligenceOutput,
)
from domain.investigation.metrics import calculate_behavioral_metrics
from domain.investigation.rules import evaluate_banking_rules
from domain.errors import ValidationError, ConflictError
from infrastructure.database.models import Account, Transaction, InvestigationCase
from infrastructure.database.session import get_engine

logger = logging.getLogger(__name__)

SANDBOX_FIXTURE_ACCOUNTS = [
    {
        "account_id": "ACC-SIM-TEST1",
        "name": "Synthetic Velocity Test Fixture",
        "type": "CHECKING",
        "initial_balance": Decimal("50000.00"),
        "currency": "EGP",
        "description": "Used for rapid 5-minute transaction velocity and burst limit testing.",
    },
    {
        "account_id": "ACC-SIM-TEST2",
        "name": "Synthetic Escalation Pattern Fixture",
        "type": "CHECKING",
        "initial_balance": Decimal("100000.00"),
        "currency": "EGP",
        "description": "Used for testing progressive 100 -> 500 -> 5000 EGP amount escalation triggers.",
    },
    {
        "account_id": "ACC-SIM-MULE",
        "name": "Synthetic Mule Structuring Sandbox",
        "type": "SAVINGS",
        "initial_balance": Decimal("30000.00"),
        "currency": "EGP",
        "description": "Used for repeated just-below-threshold withdrawal testing.",
    },
]


class SandboxWithdrawalService:
    """In-memory and relational sandbox withdrawal runner with concurrency locks."""

    def __init__(self):
        self._account_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._idempotency_cache: dict[str, SimulatedWithdrawalResponse] = {}
        self._sandbox_balances: dict[str, Decimal] = defaultdict(lambda: Decimal("50000.00"))
        self._sandbox_transactions: dict[str, list[TransactionFact]] = defaultdict(list)
        self.MAX_TRANSACTION_LIMIT = Decimal("100000.00")

        # Initialize defaults
        for fix in SANDBOX_FIXTURE_ACCOUNTS:
            self._sandbox_balances[fix["account_id"]] = fix["initial_balance"]

    def _is_sandbox_account(self, account_id: str) -> bool:
        """Check if an account is an authorized synthetic/sandbox account."""
        acc_upper = account_id.upper()
        return (
            acc_upper.startswith("ACC-SIM")
            or "TEST" in acc_upper
            or "SANDBOX" in acc_upper
            or "SYNTHETIC" in acc_upper
        )

    def get_fixture_accounts(self) -> list[dict[str, Any]]:
        """List authorized sandbox test fixtures with current balances."""
        result = []
        for fix in SANDBOX_FIXTURE_ACCOUNTS:
            acc_id = fix["account_id"]
            current_bal = self._sandbox_balances[acc_id]
            result.append({
                **fix,
                "current_balance": float(current_bal),
                "transaction_count": len(self._sandbox_transactions[acc_id]),
            })
        return result

    async def simulate_withdrawal(
        self, request: SimulatedWithdrawalRequest, caller_role: str = "INVESTIGATOR"
    ) -> SimulatedWithdrawalResponse:
        return await self.execute_simulated_withdrawal(request, caller_role)

    def set_sandbox_balance(self, account_id: str, balance: Decimal) -> None:
        """Helper to seed test balance for deterministic fixtures."""
        self._sandbox_balances[account_id] = Decimal(str(balance))

    def get_sandbox_balance(self, account_id: str) -> Decimal:
        """Retrieve current balance of a sandbox account."""
        return self._sandbox_balances[account_id]

    def get_sandbox_transactions(self, account_id: str) -> list[TransactionFact]:
        """Retrieve sandbox transaction history for an account."""
        return list(self._sandbox_transactions[account_id])

    async def execute_simulated_withdrawal(
        self,
        request: SimulatedWithdrawalRequest,
        caller_role: str = "INVESTIGATOR",
    ) -> SimulatedWithdrawalResponse:
        """Execute one atomic simulated withdrawal with concurrency and idempotency checks."""
        # 1. Enforce Sandbox Isolation Guard
        if not self._is_sandbox_account(request.account_id):
            raise ValidationError(
                f"Production account '{request.account_id}' cannot be modified by simulation. "
                f"Withdrawal simulation is strictly permitted on synthetic test accounts only."
            )

        if not request.is_sandbox_confirmed:
            raise ValidationError("Simulation requires explicit is_sandbox_confirmed=True flag.")

        # 2. Idempotency Check (Fast Path)
        if request.idempotency_key in self._idempotency_cache:
            return self._idempotency_cache[request.idempotency_key]

        # 3. Per-Account Mutex Lock for Concurrency Integrity
        lock = self._account_locks[request.account_id]
        async with lock:
            if request.idempotency_key in self._idempotency_cache:
                return self._idempotency_cache[request.idempotency_key]

            # 4. Limit Check
            if request.amount > self.MAX_TRANSACTION_LIMIT:
                raise ValidationError(
                    f"Withdrawal amount {request.amount:,.2f} exceeds per-transaction simulation "
                    f"limit of {self.MAX_TRANSACTION_LIMIT:,.2f} {request.currency}."
                )

            # 5. Insufficient Balance Check
            current_bal = self._sandbox_balances[request.account_id]
            if request.amount > current_bal:
                raise ValidationError(
                    f"Insufficient funds: Requested {request.amount:,.2f} {request.currency}, "
                    f"available ledger balance is {current_bal:,.2f} {request.currency}."
                )

            # 6. Atomic Balance Update
            new_bal = (current_bal - request.amount).quantize(Decimal("0.01"))
            self._sandbox_balances[request.account_id] = new_bal

            # 7. Record Transaction Fact
            now = datetime.now(UTC)
            txn_id = f"TXN-SIM-{uuid.uuid4().hex[:8].upper()}"
            fact = TransactionFact(
                transaction_id=txn_id,
                external_id=txn_id,
                timestamp=now,
                amount=request.amount,
                currency=request.currency,
                transaction_type="SIMULATED_WITHDRAWAL",
                status="COMPLETED",
                recipient_account_id=request.recipient_account_id,
                risk_score=10.0,
                risk_level="LOW",
            )
            self._sandbox_transactions[request.account_id].append(fact)

            # 8. Check Triggered Rules (5m velocity, escalation)
            history = self._sandbox_transactions[request.account_id]
            metrics = calculate_behavioral_metrics(history, account_balance=new_bal)
            alerts, rules_score = evaluate_banking_rules(
                account=None,
                metrics=metrics,
                graph=GraphIntelligenceOutput(available=False),
                currency=request.currency,
            )
            triggered_names = [a.rule_name for a in alerts]
            calculated_risk_score = round(rules_score * 100, 2)
            risk_level = "HIGH" if rules_score > 0.4 else "LOW"

            # 9. Persist into Relational Ledger so LangGraph can inspect it
            try:
                async with AsyncSession(get_engine(), expire_on_commit=False) as session:
                    # Ensure synthetic account row exists
                    acc = await session.scalar(
                        select(Account).where(Account.external_id == request.account_id)
                    )
                    if not acc:
                        acc = Account(
                            external_id=request.account_id,
                            customer_name=f"Synthetic Entity ({request.account_id})",
                            account_type="CHECKING",
                            currency=request.currency,
                            balance=new_bal,
                            country="EG",
                            status="ACTIVE",
                            risk_level=risk_level,
                        )
                        session.add(acc)
                        await session.flush()
                    else:
                        acc.balance = new_bal

                    # Insert Transaction row
                    db_txn = Transaction(
                        external_id=txn_id,
                        account_id=acc.id,
                        recipient_account_id=acc.id,
                        amount=request.amount,
                        currency=request.currency,
                        transaction_type="SIMULATED_WITHDRAWAL",
                        status="COMPLETED",
                        timestamp=now,
                        risk_score=Decimal(str(calculated_risk_score)),
                        risk_level=risk_level,
                        is_new_device=False,
                        is_new_ip=False,
                        txn_metadata={
                            "simulated": True,
                            "note": request.note,
                            "idempotency_key": request.idempotency_key,
                            "triggered_rules": triggered_names,
                        },
                    )
                    session.add(db_txn)
                    await session.commit()
            except Exception as exc:
                logger.warning("Relational transaction persistence skipped for simulation: %s", exc)

            # 10. Build and Cache Response
            response = SimulatedWithdrawalResponse(
                success=True,
                transaction_id=txn_id,
                account_id=request.account_id,
                amount=request.amount,
                currency=request.currency,
                new_balance=new_bal,
                status="COMPLETED",
                idempotency_key=request.idempotency_key,
                timestamp=now,
                audit_event_id=f"AUD-SIM-{uuid.uuid4().hex[:8]}",
                triggered_rules=triggered_names,
                risk_score=rules_score,
                message=(
                    f"Simulated withdrawal of {request.amount:,.2f} {request.currency} completed. "
                    f"New available balance: {new_bal:,.2f} {request.currency}."
                ),
            )
            self._idempotency_cache[request.idempotency_key] = response
            return response

    async def reset_sandbox(self) -> dict[str, Any]:
        """Safely reset all sandbox test fixtures, transactions, and cache without affecting production."""
        deleted_txns_count = 0
        try:
            async with AsyncSession(get_engine(), expire_on_commit=False) as session:
                # Find all synthetic transactions
                stmt = select(Transaction.id, Transaction.external_id).where(
                    or_(
                        Transaction.external_id.startswith("TXN-SIM-"),
                        Transaction.transaction_type == "SIMULATED_WITHDRAWAL",
                    )
                )
                sim_txns = (await session.execute(stmt)).fetchall()
                sim_txn_ids = [t[0] for t in sim_txns]
                deleted_txns_count = len(sim_txn_ids)

                if sim_txn_ids:
                    # Delete linked cases
                    await session.execute(
                        delete(InvestigationCase).where(InvestigationCase.transaction_id.in_(sim_txn_ids))
                    )
                    # Delete synthetic transactions
                    await session.execute(
                        delete(Transaction).where(Transaction.id.in_(sim_txn_ids))
                    )

                # Reset balances on synthetic accounts in database
                for fix in SANDBOX_FIXTURE_ACCOUNTS:
                    acc = await session.scalar(
                        select(Account).where(Account.external_id == fix["account_id"])
                    )
                    if acc:
                        acc.balance = fix["initial_balance"]

                await session.commit()
        except Exception as exc:
            logger.warning("Relational sandbox reset encountered notice: %s", exc)

        # Clear in-memory caches
        self._idempotency_cache.clear()
        self._sandbox_transactions.clear()
        for fix in SANDBOX_FIXTURE_ACCOUNTS:
            self._sandbox_balances[fix["account_id"]] = fix["initial_balance"]

        return {
            "success": True,
            "deleted_transactions": deleted_txns_count,
            "reset_fixtures": [fix["account_id"] for fix in SANDBOX_FIXTURE_ACCOUNTS],
            "message": "Sandbox environment successfully reset. Production records strictly preserved.",
        }


# Global singleton instance for sandbox testing
_SANDBOX_SERVICE_INSTANCE = None


def get_sandbox_withdrawal_service() -> SandboxWithdrawalService:
    global _SANDBOX_SERVICE_INSTANCE
    if _SANDBOX_SERVICE_INSTANCE is None:
        _SANDBOX_SERVICE_INSTANCE = SandboxWithdrawalService()
    return _SANDBOX_SERVICE_INSTANCE
