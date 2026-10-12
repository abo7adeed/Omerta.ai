"""Transfer & Ledger Execution Service for Omerta.ai.

Enforces double-entry ledger integrity, atomic debit/credit balance updates,
concurrency locking, idempotency protection, recipient discovery by Omerta User Number,
and automatic mock risk evaluation (> 40.00 human review trigger).
"""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager
import re
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import secrets
from typing import Any
import uuid
import os

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models import (
    Account,
    AccountLedgerEntry,
    Alert,
    AuditEvent,
    Customer,
    Device,
    IPAddress,
    RiskAssessment,
    RiskSignal,
    Session,
    Transaction,
    Transfer,
    User,
    InvestigationCase,
    CaseDisposition,
    TransactionRestriction,
    SupportTicket,
    TransferRestoration,
)
from domain.investigation.history_agent import TransactionHistoryAgent
from domain.investigation.specialist_agents import (
    BankingRulesAgent,
    BehavioralAnalysisAgent,
    AccountTakeoverAgent,
    DeviceNetworkAgent,
    GraphIntelligenceAgent,
    MLRiskAgent,
    MerchantIntelligenceAgent,
    IdentitySecurityAgent,
    FinalDecisionAgent,
)
from domain.investigation.scoring import (
    TransactionDecision,
    RiskTier,
    AuthoritativeRiskAssessment,
)
from domain.services.email_service import EmailService


class TransferConcurrencyManager:
    """Thread-safe & async coroutine concurrency controller for banking transfers.

    Combines an asyncio.Semaphore to bound concurrent in-flight transfer workloads
    with per-account asyncio.Lock mutexes in strict alphanumeric order to eliminate
    race conditions and avoid AB-BA deadlocks.
    """

    def __init__(self, max_concurrent: int = 25):
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._account_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._admin_lock = asyncio.Lock()

    async def acquire_locks(self, sender_key: str, recipient_key: str) -> list[asyncio.Lock]:
        """Acquire ordered mutex locks and semaphore for transfer participant accounts."""
        async with self._admin_lock:
            # Sort keys to ensure deterministic lock acquisition order (prevents AB-BA deadlocks)
            keys = sorted([str(sender_key), str(recipient_key)])
            locks = [self._account_locks[k] for k in keys]

        await self._semaphore.acquire()
        for lock in locks:
            await lock.acquire()

        return locks

    def release_locks(self, locks: list[asyncio.Lock]) -> None:
        """Release per-account mutex locks in reverse order and free semaphore."""
        for lock in reversed(locks):
            if lock.locked():
                lock.release()
        self._semaphore.release()

    @asynccontextmanager
    async def transfer_lock(self, sender_key: str, recipient_key: str):
        """Async context manager wrapper around semaphore & mutex lock acquisition."""
        locks = await self.acquire_locks(sender_key, recipient_key)
        try:
            yield
        finally:
            self.release_locks(locks)


_GLOBAL_TRANSFER_CONCURRENCY = TransferConcurrencyManager()


class TransferError(Exception):
    """Base exception for transfer failures."""

    def __init__(self, message: str, code: str = "TRANSFER_ERROR", status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class TransferService:
    """Orchestrates secure customer-to-customer simulated transfers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def _resolve_customer_by_identifier(self, identifier: str) -> Customer | None:
        """Resolve a customer by Omerta User Number or Registered Phone Number."""
        clean = identifier.strip()
        if not clean:
            return None
        clean_upper = clean.upper()
        # Clean digits from phone string
        digits_only = re.sub(r"[^\d+]", "", clean)
        pure_digits = re.sub(r"\D", "", clean)

        conditions = [
            Customer.omerta_user_number == clean_upper,
            Customer.accounts.any(Account.external_id == clean_upper),
        ]
        if digits_only:
            conditions.append(Customer.phone == digits_only)
            conditions.append(Customer.phone == clean)
        if pure_digits and len(pure_digits) >= 6:
            # Match suffix / international variation
            conditions.append(and_(Customer.phone != "", Customer.phone.ilike(f"%{pure_digits[-9:]}%")))

        stmt = (
            select(Customer)
            .options(selectinload(Customer.accounts))
            .where(or_(*conditions))
            .limit(1)
        )
        return await self.session.scalar(stmt)

    async def lookup_recipient(self, identifier: str) -> dict[str, Any]:
        """Look up a recipient by unique Omerta User Number or Mobile Phone Number.

        Returns only customer-safe confirmation metadata (masked display name,
        valid user number, masked phone, available currencies). Does not leak private profile,
        email, balance, or transaction history.
        """
        customer = await self._resolve_customer_by_identifier(identifier)
        if not customer:
            raise TransferError(
                f"No registered customer found with identifier '{identifier}'. Please check the Omerta User # or Phone Number.",
                code="RECIPIENT_NOT_FOUND",
                status_code=404,
            )

        if customer.status != "ACTIVE":
            raise TransferError(
                "Recipient account is not active for transfers.",
                code="RECIPIENT_INACTIVE",
                status_code=400,
            )

        # Mask name for privacy (e.g., "Amira El-Sayed" -> "Amira E.")
        parts = customer.name.split()
        if len(parts) > 1:
            masked_name = f"{parts[0]} {parts[1][0]}."
        else:
            masked_name = customer.name

        # Mask phone number (e.g., "+201033334444" -> "+20 10 •••• 4444")
        masked_phone = None
        if customer.phone:
            p = customer.phone
            if len(p) >= 8:
                masked_phone = f"{p[:5]} •••• {p[-4:]}"
            else:
                masked_phone = f"•••• {p[-4:]}"

        supported_currencies = [acc.currency for acc in customer.accounts if acc.status == "ACTIVE"]
        if not supported_currencies:
            supported_currencies = [customer.preferred_currency or "EGP"]

        return {
            "found": True,
            "omerta_user_number": customer.omerta_user_number,
            "phone_masked": masked_phone,
            "display_name": masked_name,
            "recipient_name": masked_name,
            "name": masked_name,
            "country": customer.declared_country or customer.country,
            "supported_currencies": list(set(supported_currencies)),
            "preferred_currency": customer.preferred_currency or "EGP",
        }

    async def execute_transfer(
        self,
        *,
        sender_user_id: int,
        sender_account_id: int | str,
        recipient_user_number: str,
        amount: Decimal,
        currency: str,
        note: str | None = None,
        idempotency_key: str | None = None,
        ip_address: str | None = "192.168.1.100",
        user_agent: str | None = "OmertaWeb/2.0",
        is_vpn: bool = False,
        city: str | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        """Atomically execute a transfer from sender to recipient with Python Semaphore & Mutex lock synchronization."""
        if amount <= Decimal("0.00"):
            raise TransferError("Transfer amount must be strictly positive.", code="INVALID_AMOUNT")

        if not idempotency_key:
            idempotency_key = f"IDEMP-{uuid.uuid4().hex[:16]}"

        async with _GLOBAL_TRANSFER_CONCURRENCY.transfer_lock(str(sender_account_id), str(recipient_user_number)):
            return await self._execute_transfer_internal(
                sender_user_id=sender_user_id,
                sender_account_id=sender_account_id,
                recipient_user_number=recipient_user_number,
                amount=amount,
                currency=currency,
                note=note,
                idempotency_key=idempotency_key,
                ip_address=ip_address,
                user_agent=user_agent,
                is_vpn=is_vpn,
                city=city,
                country=country,
            )

    async def _execute_transfer_internal(
        self,
        *,
        sender_user_id: int,
        sender_account_id: int | str,
        recipient_user_number: str,
        amount: Decimal,
        currency: str,
        note: str | None = None,
        idempotency_key: str | None = None,
        ip_address: str | None = "192.168.1.100",
        user_agent: str | None = "OmertaWeb/2.0",
        is_vpn: bool = False,
        city: str | None = None,
        country: str | None = None,
    ) -> dict[str, Any]:
        # 1. Check idempotency
        existing_transfer = await self.session.scalar(
            select(Transfer).where(Transfer.idempotency_key == idempotency_key).limit(1)
        )
        if existing_transfer:
            return await self.get_transfer_receipt(existing_transfer.external_id)

        # 2. Fetch sender customer & user
        sender_stmt = (
            select(Customer)
            .options(selectinload(Customer.accounts))
            .where(Customer.user_id == sender_user_id)
            .limit(1)
        )
        sender_customer = await self.session.scalar(sender_stmt)
        if not sender_customer:
            raise TransferError("Sender profile not found.", code="SENDER_NOT_FOUND", status_code=404)

        if sender_customer.status != "ACTIVE":
            raise TransferError("Your customer profile is currently inactive or suspended.", code="SENDER_INACTIVE")

        # 2a. Check for server-enforced active transfer restrictions
        restr_stmt = (
            select(TransactionRestriction)
            .where(
                and_(
                    TransactionRestriction.customer_id == sender_customer.id,
                    TransactionRestriction.status == "ACTIVE",
                    TransactionRestriction.restriction_scope.in_(["OUTGOING_TRANSFERS_ONLY", "ALL_TRANSFERS", "FULL_CONTAINMENT"]),
                )
            )
            .limit(1)
        )
        active_restr = await self.session.scalar(restr_stmt)
        if active_restr:
            raise TransferError(
                f"Your account is subject to an active security restriction on outgoing transfers: {active_restr.restriction_reason}",
                code="TRANSFERS_RESTRICTED",
                status_code=403,
            )

        # 3. Resolve sender account with row lock
        if isinstance(sender_account_id, int):
            sender_acc_stmt = (
                select(Account)
                .where(and_(Account.id == sender_account_id, Account.customer_id == sender_customer.id))
                .with_for_update()
            )
        else:
            sender_acc_stmt = (
                select(Account)
                .where(and_(Account.external_id == sender_account_id, Account.customer_id == sender_customer.id))
                .with_for_update()
            )
        sender_account = await self.session.scalar(sender_acc_stmt)
        if not sender_account:
            raise TransferError("Source account not found or does not belong to you.", code="ACCOUNT_NOT_OWNED", status_code=403)

        if sender_account.status != "ACTIVE":
            raise TransferError("Selected source account is not active.", code="ACCOUNT_INACTIVE")

        if sender_account.currency.upper() != currency.upper():
            raise TransferError(
                f"Source account currency ({sender_account.currency}) does not match transfer currency ({currency}).",
                code="CURRENCY_MISMATCH",
            )

        # 4. Resolve recipient customer (supports Omerta User Number or Mobile Phone Number)
        recipient_customer = await self._resolve_customer_by_identifier(recipient_user_number)
        if not recipient_customer:
            raise TransferError(
                f"Recipient identifier '{recipient_user_number}' not found. Please verify the Omerta User Number or Phone Number.",
                code="RECIPIENT_NOT_FOUND",
                status_code=404,
            )

        if recipient_customer.id == sender_customer.id:
            raise TransferError("Cannot transfer funds to your own customer account.", code="SELF_TRANSFER_DISALLOWED")

        if recipient_customer.status != "ACTIVE":
            raise TransferError("Recipient customer profile is not active.", code="RECIPIENT_INACTIVE")

        # 5. Resolve matching recipient account with row lock
        recipient_acc_stmt = (
            select(Account)
            .where(
                and_(
                    Account.customer_id == recipient_customer.id,
                    Account.currency == currency.upper(),
                    Account.status == "ACTIVE",
                )
            )
            .order_by(Account.id.asc())
            .with_for_update()
            .limit(1)
        )
        recipient_account = await self.session.scalar(recipient_acc_stmt)
        if not recipient_account:
            raise TransferError(
                f"Recipient does not have an active account matching currency '{currency}'.",
                code="RECIPIENT_CURRENCY_UNSUPPORTED",
            )

        # 6. Check sender balance
        if sender_account.balance < amount:
            raise TransferError(
                f"Insufficient available demo balance. Required: {amount:,.2f} {currency}, Available: {sender_account.balance:,.2f} {currency}",
                code="INSUFFICIENT_FUNDS",
                status_code=400,
            )

        # 7. Create uncommitted Transaction & Transfer in ASSESSING state (DO NOT deduct balances yet!)
        now = datetime.now(UTC)
        transfer_ref = f"TRF-{secrets.token_hex(4).upper()}-{now.strftime('%M%S')}"
        txn_ref = f"TXN-SIM-{secrets.token_hex(4).upper()}"

        txn = Transaction(
            external_id=txn_ref,
            account_id=sender_account.id,
            recipient_account_id=recipient_account.id,
            amount=amount,
            currency=currency.upper(),
            transaction_type="CUSTOMER_TRANSFER",
            status="ASSESSING",
            timestamp=now,
            is_new_device=False,
            is_new_ip=False,
            txn_metadata={"note": note, "transfer_ref": transfer_ref, "is_vpn": is_vpn},
        )
        self.session.add(txn)
        await self.session.flush()

        transfer = Transfer(
            external_id=transfer_ref,
            idempotency_key=idempotency_key,
            sender_customer_id=sender_customer.id,
            sender_account_id=sender_account.id,
            recipient_customer_id=recipient_customer.id,
            recipient_account_id=recipient_account.id,
            amount=amount,
            currency=currency.upper(),
            note=note,
            status="PENDING_REVIEW",
            transaction_id=txn.id,
        )
        self.session.add(transfer)
        await self.session.flush()

        # 8. Execute Specialist Investigative Agents
        # A. Historical Intelligence
        hist_agent = TransactionHistoryAgent(self.session)
        history_result = await hist_agent.analyze(
            account_id=sender_account.id,
            current_amount=float(amount),
            current_timestamp=now,
            recipient_account_id=recipient_account.id,
            current_transaction_id=txn.id,
        )

        # B. Banking Rules Agent
        rules_result = BankingRulesAgent.evaluate(
            history_metrics=history_result.raw_metrics,
            vpn_detected=is_vpn,
            is_new_device=False,
            shared_device_count=0,
            failed_attempts=sender_customer.transfer_failed_attempts,
            has_active_restriction=False,
        )

        # C. Behavioral Analysis Agent
        behavior_result = BehavioralAnalysisAgent.evaluate(
            history_metrics=history_result.raw_metrics,
            hour_utc=now.hour,
        )

        # D. Account Takeover Agent
        ato_result = AccountTakeoverAgent.evaluate(
            recent_password_change=sender_customer.require_transfer_password_change,
            recent_failed_logins=sender_customer.transfer_failed_attempts,
            recent_device_added=False,
            new_beneficiary_added=history_result.raw_metrics.get("is_first_transaction_with_beneficiary", False),
        )

        # E. Device and Network Agent
        device_result = DeviceNetworkAgent.evaluate(
            is_new_device=False,
            is_vpn=is_vpn,
            ip_risk_score=65.0 if is_vpn else 5.0,
            provider_available=True,
            country=country or (sender_customer.declared_country or "EG"),
        )

        # F. Graph Intelligence Agent
        graph_result = GraphIntelligenceAgent.evaluate(
            shared_devices_count=0,
            connected_accounts_count=1,
            graph_available=True,
        )

        # G. ML Risk Agent
        ml_prob = min(0.95, (float(amount) / 60000.0) * 0.4 + (0.35 if is_vpn else 0.05))
        ml_result = MLRiskAgent.evaluate(
            model_risk_probability=ml_prob,
            model_loaded=True,
            top_features={"amount": float(amount), "is_vpn": 1.0 if is_vpn else 0.0},
        )

        # H. Merchant Intelligence Agent (P2P = Not Applicable)
        merchant_result = MerchantIntelligenceAgent.evaluate(is_merchant_tx=False)

        # I. Identity & Security Agent
        identity_result = IdentitySecurityAgent.evaluate(
            identity_status=sender_customer.identity_status,
            transfer_status=sender_customer.transfer_status,
            has_active_restriction=False,
        )

        # J. Authoritative Final Decision Agent
        agent_suite = {
            "rules": rules_result,
            "ml": ml_result,
            "history": history_result,
            "behavior": behavior_result,
            "ato": ato_result,
            "device": device_result,
            "graph": graph_result,
            "merchant": merchant_result,
        }

        final_decision_result = FinalDecisionAgent.evaluate(
            agent_results=agent_suite,
            hard_restrictions_active=False,
            vpn_detected=is_vpn,
            is_merchant_tx=False,
            customer_confirmed=None,
        )
        assessment = AuthoritativeRiskAssessment(**final_decision_result.raw_metrics)

        # 9. Record Risk Assessment and Signals
        txn.risk_score = Decimal(str(assessment.final_score))
        txn.risk_level = assessment.risk_tier.value
        txn.review_status = "REQUIRES_REVIEW" if assessment.requires_human_review else "NOT_REQUIRED"

        risk_assessment = RiskAssessment(
            external_id=f"RA-{secrets.token_hex(4).upper()}",
            transaction_id=txn.id,
            risk_score=Decimal(str(assessment.final_score)),
            risk_level=assessment.risk_tier.value,
            requires_human_review=assessment.requires_human_review,
            correlation_id=f"CORR-{txn.external_id}",
            summary=f"Authoritative formula ({assessment.formula_version}): Final score {assessment.final_score:.1f}/100 ({assessment.risk_tier.value}). Decision: {assessment.decision.value}.",
        )
        self.session.add(risk_assessment)
        await self.session.flush()

        for step in assessment.calculation:
            if step.raw_score is not None and step.raw_score > 0:
                self.session.add(
                    RiskSignal(
                        assessment_id=risk_assessment.id,
                        signal_name=f"{step.component.upper()}_SIGNAL",
                        severity="HIGH" if step.raw_score >= 60 else "MEDIUM" if step.raw_score >= 30 else "LOW",
                        description=step.notes,
                        source=f"Specialist:{step.component}",
                    )
                )

        # 10. Execute State Machine Decisions
        if assessment.decision == TransactionDecision.ALLOW:
            # Low Risk: Atomically execute double-entry ledger debit & credit now!
            sender_account.balance = Decimal(str(sender_account.balance)) - amount
            recipient_account.balance = Decimal(str(recipient_account.balance)) + amount

            debit_ledger_ref = f"LED-DB-{secrets.token_hex(4).upper()}"
            credit_ledger_ref = f"LED-CR-{secrets.token_hex(4).upper()}"

            debit_entry = AccountLedgerEntry(
                external_id=debit_ledger_ref,
                account_id=sender_account.id,
                transfer_id=transfer.id,
                transaction_id=txn.id,
                entry_type="DEBIT",
                amount=amount,
                currency=currency.upper(),
                balance_after=sender_account.balance,
                description=f"Simulated Transfer to {recipient_customer.name} ({recipient_customer.omerta_user_number})",
                idempotency_key=f"{idempotency_key}-DEBIT",
            )
            credit_entry = AccountLedgerEntry(
                external_id=credit_ledger_ref,
                account_id=recipient_account.id,
                transfer_id=transfer.id,
                transaction_id=txn.id,
                entry_type="CREDIT",
                amount=amount,
                currency=currency.upper(),
                balance_after=recipient_account.balance,
                description=f"Simulated Transfer from {sender_customer.name} ({sender_customer.omerta_user_number})",
                idempotency_key=f"{idempotency_key}-CREDIT",
            )
            self.session.add_all([debit_entry, credit_entry])

            txn.status = "COMPLETED"
            transfer.status = "COMPLETED"
            txn.review_status = "NOT_REQUIRED"

            audit_event = AuditEvent(
                event_id=f"EVT-{secrets.token_hex(6).upper()}",
                event_type="TRANSFER_EXECUTED",
                actor_type="CUSTOMER",
                actor_id=str(sender_user_id),
                source="TransferService",
                transaction_id=txn.external_id,
                metadata_={
                    "transfer_ref": transfer_ref,
                    "amount": str(amount),
                    "currency": currency,
                    "risk_score": float(assessment.final_score),
                    "decision": "ALLOW",
                },
            )
            self.session.add(audit_event)

        elif assessment.decision == TransactionDecision.PENDING_CUSTOMER_VERIFICATION:
            # Transfer Held: Funds stay in sender account!
            txn.status = "PENDING_CUSTOMER_VERIFICATION"
            transfer.status = "PENDING_CUSTOMER_VERIFICATION"
            txn.review_status = "REQUIRES_REVIEW"

            alert = Alert(
                external_id=f"ALT-{secrets.token_hex(4).upper()}",
                transaction_id=txn.id,
                alert_type="VPN_CUSTOMER_VERIFICATION_REQUIRED",
                risk_score=Decimal(str(assessment.final_score)),
                risk_level=assessment.risk_tier.value,
                status="OPEN",
            )
            self.session.add(alert)
            await self.session.flush()

            case = InvestigationCase(
                external_id=f"CASE-{txn.external_id}",
                alert_id=alert.id,
                transaction_id=txn.id,
                title=f"Customer Verification Hold: Transfer {txn.external_id}",
                severity=assessment.risk_tier.value,
                status="PENDING_CUSTOMER_VERIFICATION",
                assigned_to="Automated Verification Dispatcher",
                report={
                    "investigation_id": f"INV-{txn.external_id}",
                    "transaction_id": txn.external_id,
                    "account_id": sender_account.external_id,
                    "executive_summary": "Transaction placed on security hold pending customer identity confirmation. Funds not debited.",
                    "combined_risk_score": float(assessment.final_score) / 100.0,
                    "recommended_action": "REQUEST_CUSTOMER_INFO",
                    "recommended_action_justification": "; ".join(assessment.hold_reasons),
                    "generated_at": now.isoformat(),
                },
            )
            self.session.add(case)

            # Send Email Notification
            target_email = sender_customer.email
            if not target_email or target_email.endswith("@omerta.ai"):
                target_email = os.getenv("REAL_CUSTOMER_EMAIL", "abdomostafa13571234@gmail.com")

            if target_email:
                verif_url = "http://localhost:5173/customer/security"
                try:
                    asyncio.create_task(
                        EmailService.send_transfer_verification_email(
                            to_email=target_email,
                            customer_name=sender_customer.name,
                            transaction_ref=txn.external_id,
                            amount=float(amount),
                            currency=currency,
                            recipient_masked=recipient_customer.name,
                            verification_url=verif_url,
                            reason="; ".join(assessment.hold_reasons),
                        )
                    )
                except Exception as mail_err:
                    logger.warning(f"Verification email dispatch failed: {mail_err}")

        elif assessment.decision in (TransactionDecision.PENDING_REVIEW, TransactionDecision.HOLD):
            # High Risk Hold: Funds stay in sender account!
            txn.status = "PENDING_REVIEW"
            transfer.status = "PENDING_REVIEW"
            txn.review_status = "REQUIRES_REVIEW"

            alert = Alert(
                external_id=f"ALT-{secrets.token_hex(4).upper()}",
                transaction_id=txn.id,
                alert_type="HIGH_RISK_TRANSFER_REVIEW",
                risk_score=Decimal(str(assessment.final_score)),
                risk_level=assessment.risk_tier.value,
                status="OPEN",
            )
            self.session.add(alert)
            await self.session.flush()

            case = InvestigationCase(
                external_id=f"CASE-{txn.external_id}",
                alert_id=alert.id,
                transaction_id=txn.id,
                title=f"Forensic Investigation: High-Risk Transfer {txn.external_id}",
                severity=assessment.risk_tier.value,
                status="UNDER_INVESTIGATION",
                assigned_to="Compliance Review Queue",
                report={
                    "investigation_id": f"INV-{txn.external_id}",
                    "transaction_id": txn.external_id,
                    "account_id": sender_account.external_id,
                    "executive_summary": f"Elevated risk score ({assessment.final_score:.1f}/100). Funds held pending compliance officer investigation.",
                    "combined_risk_score": float(assessment.final_score) / 100.0,
                    "recommended_action": "HUMAN_REVIEW",
                    "recommended_action_justification": "; ".join(assessment.hold_reasons),
                    "generated_at": now.isoformat(),
                },
            )
            self.session.add(case)

        elif assessment.decision == TransactionDecision.REJECT:
            txn.status = "REJECTED"
            transfer.status = "REJECTED"
            txn.review_status = "REJECTED"

        await self.session.commit()
        return await self.get_transfer_receipt(transfer_ref)

    async def handle_customer_confirmation(
        self,
        transaction_external_id: str,
        action: str,
        customer_user_id: int,
    ) -> dict[str, Any]:
        """Process customer confirmation response (CONFIRM or DENY)."""
        txn_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.account).selectinload(Account.customer),
                selectinload(Transaction.recipient_account).selectinload(Account.customer),
            )
            .where(Transaction.external_id == transaction_external_id)
            .limit(1)
        )
        txn = await self.session.scalar(txn_stmt)
        if not txn:
            raise TransferError("Transaction not found.", code="TXN_NOT_FOUND", status_code=404)

        sender_customer = txn.account.customer
        if sender_customer.user_id != customer_user_id:
            raise TransferError("Unauthorized: transaction does not belong to you.", code="UNAUTHORIZED", status_code=403)

        transfer_stmt = select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        transfer = await self.session.scalar(transfer_stmt)
        if not transfer:
            raise TransferError("Transfer record not found.", code="TRANSFER_NOT_FOUND", status_code=404)

        if txn.status not in ("PENDING_CUSTOMER_VERIFICATION", "PENDING_REVIEW"):
            return {
                "success": False,
                "message": f"Transaction is already in status '{txn.status}'. No confirmation action needed.",
                "status": txn.status,
            }

        now = datetime.now(UTC)

        if action.upper() == "CONFIRM":
            # Record audit event
            self.session.add(
                AuditEvent(
                    event_id=f"EVT-CONFIRMED-{secrets.token_hex(4).upper()}",
                    event_type="CUSTOMER_TRANSACTION_CONFIRMED",
                    actor_type="CUSTOMER",
                    actor_id=str(customer_user_id),
                    source="CustomerSecurityPortal",
                    transaction_id=txn.external_id,
                    metadata_={"response": "CONFIRM", "timestamp": now.isoformat()},
                )
            )

            # Re-evaluate policy: if VPN was detected or risk score elevated -> must transition to PENDING_REVIEW (cannot bypass admin review)
            has_vpn_alert = await self.session.scalar(
                select(Alert).where(and_(Alert.transaction_id == txn.id, Alert.alert_type == "VPN_CUSTOMER_VERIFICATION_REQUIRED")).limit(1)
            ) is not None
            is_vpn_txn = bool(txn.txn_metadata and txn.txn_metadata.get("is_vpn"))
            risk_score = float(txn.risk_score) if txn.risk_score is not None else 0.0

            if not has_vpn_alert and not is_vpn_txn and risk_score < 40.0:
                # Low risk without VPN: execute ledger debit & credit now!
                sender_acc = txn.account
                recip_acc = txn.recipient_account

                if sender_acc.balance < txn.amount:
                    raise TransferError("Insufficient balance to execute transfer upon release.", code="INSUFFICIENT_FUNDS")

                sender_acc.balance = Decimal(str(sender_acc.balance)) - txn.amount
                recip_acc.balance = Decimal(str(recip_acc.balance)) + txn.amount

                debit_ledger_ref = f"LED-DB-{secrets.token_hex(4).upper()}"
                credit_ledger_ref = f"LED-CR-{secrets.token_hex(4).upper()}"

                self.session.add_all([
                    AccountLedgerEntry(
                        external_id=debit_ledger_ref,
                        account_id=sender_acc.id,
                        transfer_id=transfer.id,
                        transaction_id=txn.id,
                        entry_type="DEBIT",
                        amount=txn.amount,
                        currency=txn.currency,
                        balance_after=sender_acc.balance,
                        description=f"Transfer verified by customer to {recip_acc.customer.name}",
                        idempotency_key=f"{transfer.idempotency_key}-CONFIRMED-DEBIT",
                    ),
                    AccountLedgerEntry(
                        external_id=credit_ledger_ref,
                        account_id=recip_acc.id,
                        transfer_id=transfer.id,
                        transaction_id=txn.id,
                        entry_type="CREDIT",
                        amount=txn.amount,
                        currency=txn.currency,
                        balance_after=recip_acc.balance,
                        description=f"Transfer verified by customer from {sender_acc.customer.name}",
                        idempotency_key=f"{transfer.idempotency_key}-CONFIRMED-CREDIT",
                    ),
                ])

                txn.status = "COMPLETED"
                transfer.status = "COMPLETED"
                txn.review_status = "COMPLETED"

                # Update case if exists
                case_stmt = select(InvestigationCase).where(InvestigationCase.transaction_id == txn.id).limit(1)
                case = await self.session.scalar(case_stmt)
                if case:
                    case.status = "RESOLVED"

                await self.session.commit()
                return {
                    "success": True,
                    "action": "CONFIRMED_AND_EXECUTED",
                    "customer_action": "CONFIRM",
                    "status": "COMPLETED",
                    "message": "Transaction verified and executed successfully.",
                }
            else:
                # High risk / VPN detected remains held awaiting admin review
                txn.status = "PENDING_REVIEW"
                transfer.status = "PENDING_REVIEW"
                await self.session.commit()
                return {
                    "success": True,
                    "action": "CONFIRMED_AWAITING_ADMIN",
                    "customer_action": "CONFIRM",
                    "status": "PENDING_REVIEW",
                    "message": "Confirmation recorded. Transfer remains held in compliance review queue due to high risk score.",
                }

        elif action.upper() == "DENY":
            # 1. Reject transaction
            txn.status = "REJECTED"
            transfer.status = "REJECTED"
            txn.review_status = "DISMISSED"

            # 2. Apply server-enforced restriction on outgoing transfers
            restr_id = f"REST-{secrets.token_hex(4).upper()}"
            restriction = TransactionRestriction(
                restriction_id=restr_id,
                customer_id=sender_customer.id,
                account_id=txn.account_id,
                trigger_transaction_id=txn.external_id,
                restriction_reason=f"Customer reported unauthorized transaction attempt: {txn.external_id}",
                restriction_scope="OUTGOING_TRANSFERS_ONLY",
                status="ACTIVE",
                created_by="CUSTOMER_DENIAL_AUTOMATION",
            )
            self.session.add(restriction)
            sender_customer.transfer_status = "BLOCKED"
            sender_customer.transfer_blocked_at = now

            # 3. Create Security Support Ticket
            tkt_ref = f"TICK-{secrets.token_hex(4).upper()}"
            ticket = SupportTicket(
                external_id=tkt_ref,
                customer_id=sender_customer.id,
                account_id=txn.account_id,
                ticket_type="FRAUD_CUSTOMER_DENIAL",
                category="SECURITY",
                priority="CRITICAL",
                status="OPEN",
                subject=f"Unauthorized Transaction Reported: {txn.external_id}",
                description=f"Customer denied initiating transfer {txn.external_id} of {txn.amount} {txn.currency}. Outgoing transfer restriction applied automatically.",
                opened_by="SYSTEM_SECURITY",
                related_transaction_id=txn.id,
                related_account_id=txn.account_id,
            )
            self.session.add(ticket)

            # 4. Record Audit Event
            self.session.add(
                AuditEvent(
                    event_id=f"EVT-DENIED-{secrets.token_hex(4).upper()}",
                    event_type="CUSTOMER_TRANSACTION_DENIED",
                    actor_type="CUSTOMER",
                    actor_id=str(customer_user_id),
                    source="CustomerSecurityPortal",
                    transaction_id=txn.external_id,
                    metadata_={
                        "response": "DENIED",
                        "restriction_id": restr_id,
                        "ticket_id": tkt_ref,
                    },
                )
            )

            await self.session.commit()
            return {
                "success": True,
                "action": "DENIED_AND_RESTRICTED",
                "customer_action": "DENY",
                "status": "CANCELLED",
                "restriction_applied": "OUTGOING_TRANSFERS_ONLY",
                "security_ticket_created": True,
                "ticket_id": tkt_ref,
                "restriction_id": restr_id,
                "message": "Transfer cancelled. Outgoing transfer restriction placed on your account to safeguard funds. Security ticket created.",
            }

        else:
            raise TransferError("Invalid confirmation action. Must be 'CONFIRM' or 'DENY'.", code="INVALID_ACTION")

    async def admin_approve_transfer(
        self,
        transaction_external_id: str,
        admin_user_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """Admin compliance override: approve and execute a held transfer."""
        txn_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.account).selectinload(Account.customer),
                selectinload(Transaction.recipient_account).selectinload(Account.customer),
            )
            .where(Transaction.external_id == transaction_external_id)
            .limit(1)
        )
        txn = await self.session.scalar(txn_stmt)
        if not txn:
            raise TransferError("Transaction not found.", code="TXN_NOT_FOUND", status_code=404)

        if txn.status not in ("PENDING_REVIEW", "PENDING_CUSTOMER_VERIFICATION"):
            raise TransferError(f"Cannot approve transaction with status '{txn.status}'. Must be in held state.", code="INVALID_STATE")

        # Check if customer has active restrictions prohibiting transfers
        sender_customer = txn.account.customer
        restr_stmt = (
            select(TransactionRestriction)
            .where(
                and_(
                    TransactionRestriction.customer_id == sender_customer.id,
                    TransactionRestriction.status == "ACTIVE",
                    TransactionRestriction.restriction_scope.in_(["OUTGOING_TRANSFERS_ONLY", "ALL_TRANSFERS", "FULL_CONTAINMENT"]),
                )
            )
            .limit(1)
        )
        active_restr = await self.session.scalar(restr_stmt)
        if active_restr:
            raise TransferError(
                f"Cannot process transfer: account has an active security restriction ({active_restr.restriction_reason}). Restore privileges first.",
                code="RESTRICTION_ACTIVE",
                status_code=400,
            )

        transfer_stmt = select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        transfer = await self.session.scalar(transfer_stmt)
        if not transfer:
            raise TransferError("Transfer record not found.", code="TRANSFER_NOT_FOUND", status_code=404)

        sender_acc = await self.session.scalar(
            select(Account).where(Account.id == txn.account_id).with_for_update()
        )
        recip_acc = await self.session.scalar(
            select(Account).where(Account.id == txn.recipient_account_id).with_for_update()
        )
        if not sender_acc or not recip_acc:
            raise TransferError("Accounts not found.", code="ACCOUNT_NOT_FOUND", status_code=404)

        if sender_acc.balance < txn.amount:
            raise TransferError("Source account balance is insufficient for settlement.", code="INSUFFICIENT_FUNDS")

        # Execute ledger balance posting
        sender_acc.balance = Decimal(str(sender_acc.balance)) - txn.amount
        recip_acc.balance = Decimal(str(recip_acc.balance)) + txn.amount
        self.session.add_all([sender_acc, recip_acc])

        debit_ledger_ref = f"LED-DB-{secrets.token_hex(4).upper()}"
        credit_ledger_ref = f"LED-CR-{secrets.token_hex(4).upper()}"

        self.session.add_all([
            AccountLedgerEntry(
                external_id=debit_ledger_ref,
                account_id=sender_acc.id,
                transfer_id=transfer.id,
                transaction_id=txn.id,
                entry_type="DEBIT",
                amount=txn.amount,
                currency=txn.currency,
                balance_after=sender_acc.balance,
                description=f"Admin approved transfer to {recip_acc.customer.name}",
                idempotency_key=f"{transfer.idempotency_key}-ADMIN-DEBIT",
            ),
            AccountLedgerEntry(
                external_id=credit_ledger_ref,
                account_id=recip_acc.id,
                transfer_id=transfer.id,
                transaction_id=txn.id,
                entry_type="CREDIT",
                amount=txn.amount,
                currency=txn.currency,
                balance_after=recip_acc.balance,
                description=f"Admin approved transfer from {sender_acc.customer.name}",
                idempotency_key=f"{transfer.idempotency_key}-ADMIN-CREDIT",
            ),
        ])

        txn.status = "COMPLETED"
        transfer.status = "COMPLETED"
        txn.review_status = "COMPLETED"

        # Update case & audit
        now = datetime.now(UTC)
        case_stmt = select(InvestigationCase).where(InvestigationCase.transaction_id == txn.id).limit(1)
        case = await self.session.scalar(case_stmt)
        if case:
            case.status = "RESOLVED"
            self.session.add(
                CaseDisposition(
                    case_id=case.id,
                    analyst_id=str(admin_user_id),
                    disposition="LEGITIMATE_ACTIVITY",
                    rationale=reason or "Approved by authorized compliance administrator.",
                    recorded_at=now,
                )
            )

        self.session.add(
            AuditEvent(
                event_id=f"EVT-ADMIN-APP-{secrets.token_hex(4).upper()}",
                event_type="ADMIN_TRANSACTION_APPROVED",
                actor_type="ADMIN",
                actor_id=str(admin_user_id),
                source="TransferService",
                transaction_id=txn.external_id,
                metadata_={"reason": reason, "approved_at": now.isoformat()},
            )
        )

        txn_ext_id = txn.external_id
        await self.session.commit()
        return {
            "success": True,
            "status": "COMPLETED",
            "message": f"Transaction {txn_ext_id} approved and posted to double-entry ledger.",
        }

    async def admin_reject_transfer(
        self,
        transaction_external_id: str,
        admin_user_id: int,
        reason: str,
    ) -> dict[str, Any]:
        """Admin compliance rejection of a held transfer."""
        txn_stmt = select(Transaction).where(Transaction.external_id == transaction_external_id).limit(1)
        txn = await self.session.scalar(txn_stmt)
        if not txn:
            raise TransferError("Transaction not found.", code="TXN_NOT_FOUND", status_code=404)

        transfer_stmt = select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        transfer = await self.session.scalar(transfer_stmt)
        if not transfer:
            raise TransferError("Transfer record not found.", code="TRANSFER_NOT_FOUND", status_code=404)

        txn.status = "REJECTED"
        transfer.status = "REJECTED"
        txn.review_status = "DISMISSED"

        now = datetime.now(UTC)
        case_stmt = select(InvestigationCase).where(InvestigationCase.transaction_id == txn.id).limit(1)
        case = await self.session.scalar(case_stmt)
        if case:
            case.status = "CLOSED"
            self.session.add(
                CaseDisposition(
                    case_id=case.id,
                    analyst_id=str(admin_user_id),
                    disposition="SUSPICIOUS_FURTHER_INVESTIGATION",
                    rationale=reason or "Rejected by compliance administrator.",
                    recorded_at=now,
                )
            )

        self.session.add(
            AuditEvent(
                event_id=f"EVT-ADMIN-REJ-{secrets.token_hex(4).upper()}",
                event_type="ADMIN_TRANSACTION_REJECTED",
                actor_type="ADMIN",
                actor_id=str(admin_user_id),
                source="TransferService",
                transaction_id=txn.external_id,
                metadata_={"reason": reason, "rejected_at": now.isoformat()},
            )
        )

        txn_ext_id = txn.external_id
        await self.session.commit()
        return {
            "success": True,
            "status": "REJECTED",
            "message": f"Transaction {txn_ext_id} rejected.",
        }

    async def restore_customer_transfer_privileges(
        self,
        customer_id: int,
        admin_user_id: int,
        reason: str,
        ticket_id: int | None = None,
    ) -> dict[str, Any]:
        """Admin operation to release transfer restrictions and restore privileges."""
        cust_stmt = select(Customer).where(Customer.id == customer_id).limit(1)
        customer = await self.session.scalar(cust_stmt)
        if not customer:
            raise TransferError("Customer not found.", code="CUST_NOT_FOUND", status_code=404)

        now = datetime.now(UTC)

        # Release active restrictions
        restr_stmt = (
            select(TransactionRestriction)
            .where(
                and_(
                    TransactionRestriction.customer_id == customer_id,
                    TransactionRestriction.status == "ACTIVE",
                )
            )
        )
        active_restrs = (await self.session.scalars(restr_stmt)).all()
        released_count = 0
        for restr in active_restrs:
            restr.status = "RELEASED"
            restr.released_at = now
            restr.released_by = str(admin_user_id)
            restr.release_reason = reason
            released_count += 1

        customer.transfer_status = "ACTIVE"
        customer.transfer_unblocked_at = now
        customer.transfer_failed_attempts = 0

        # Record TransferRestoration audit record
        restoration_num = (await self.session.scalar(
            select(func.count(TransferRestoration.id)).where(TransferRestoration.customer_id == customer_id)
        ) or 0) + 1

        self.session.add(
            TransferRestoration(
                external_id=f"RES-{secrets.token_hex(4).upper()}",
                customer_id=customer_id,
                ticket_id=ticket_id,
                actor_id=str(admin_user_id),
                actor_name="Compliance Administrator",
                actor_role="ADMINISTRATOR",
                restoration_number=restoration_num,
                previous_state="BLOCKED",
                new_state="ACTIVE",
                reason=reason,
            )
        )

        # Resolve ticket if provided
        if ticket_id:
            ticket = await self.session.scalar(select(SupportTicket).where(SupportTicket.id == ticket_id))
            if ticket:
                ticket.status = "RESOLVED"
                ticket.restoration_approved = True
                ticket.restoration_approved_by = str(admin_user_id)
                ticket.restoration_approved_at = now
                ticket.resolution_reason = reason

        cust_ext_id = customer.external_id
        cust_name = customer.name
        await self.session.commit()
        return {
            "success": True,
            "privileges_restored": True,
            "restrictions_released": released_count,
            "customer_id": cust_ext_id,
            "transfer_status": "ACTIVE",
            "released_restrictions_count": released_count,
            "message": f"Transfer privileges restored for customer {cust_name}.",
        }

    async def get_transfer_receipt(self, transfer_ref: str) -> dict[str, Any]:
        """Fetch receipt for a completed transfer."""
        stmt = (
            select(Transfer)
            .options(
                selectinload(Transfer.sender_customer),
                selectinload(Transfer.recipient_customer),
                selectinload(Transfer.sender_account),
                selectinload(Transfer.recipient_account),
                selectinload(Transfer.transaction),
            )
            .where(Transfer.external_id == transfer_ref)
            .limit(1)
        )
        transfer = await self.session.scalar(stmt)
        if not transfer:
            raise TransferError("Transfer record not found.", code="TRANSFER_NOT_FOUND", status_code=404)

        return {
            "transfer_id": transfer.external_id,
            "transaction_id": transfer.transaction.external_id if transfer.transaction else None,
            "transaction_reference": transfer.transaction.external_id if transfer.transaction else None,
            "status": transfer.status,
            "hold_reason": "VPN Detected - Requires Customer Confirmation" if transfer.status == "PENDING_CUSTOMER_VERIFICATION" else None,
            "amount": float(transfer.amount),
            "currency": transfer.currency,
            "formatted_amount": f"{transfer.amount:,.2f} {transfer.currency}",
            "note": transfer.note,
            "created_at": transfer.created_at.isoformat(),
            "risk_score": float(transfer.transaction.risk_score) if transfer.transaction and transfer.transaction.risk_score is not None else 0.0,
            "risk_level": transfer.transaction.risk_level if transfer.transaction and transfer.transaction.risk_level else "LOW",
            "review_status": transfer.transaction.review_status if transfer.transaction and transfer.transaction.review_status else "NOT_REQUIRED",
            "sender": {
                "name": transfer.sender_customer.name,
                "omerta_user_number": transfer.sender_customer.omerta_user_number,
                "account_id": transfer.sender_account.external_id,
            },
            "recipient": {
                "name": transfer.recipient_customer.name,
                "omerta_user_number": transfer.recipient_customer.omerta_user_number,
                "account_id": transfer.recipient_account.external_id,
            },
            "fee": "0.00 DEMO",
            "is_demo": True,
            "disclaimer": "This is a simulated demo transfer for testing and compliance training purposes.",
            "security_hold": transfer.transaction.review_status == "REQUIRES_REVIEW" if transfer.transaction else False,
            "account_status": transfer.sender_account.status if transfer.sender_account else "ACTIVE",
            "support_phone": "+20 2 19876",
            "support_email": "compliance@omerta.ai",
        }

    async def list_customer_transfers(
        self,
        *,
        user_id: int,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List all transfers involving the authenticated customer."""
        customer = await self.session.scalar(
            select(Customer).where(Customer.user_id == user_id).limit(1)
        )
        if not customer:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 1}

        query = (
            select(Transfer)
            .options(
                selectinload(Transfer.sender_customer),
                selectinload(Transfer.recipient_customer),
                selectinload(Transfer.sender_account),
                selectinload(Transfer.recipient_account),
                selectinload(Transfer.transaction),
            )
            .where(
                or_(
                    Transfer.sender_customer_id == customer.id,
                    Transfer.recipient_customer_id == customer.id,
                )
            )
            .order_by(Transfer.id.desc())
        )

        count_q = select(func.count(Transfer.id)).where(
            or_(
                Transfer.sender_customer_id == customer.id,
                Transfer.recipient_customer_id == customer.id,
            )
        )
        total = await self.session.scalar(count_q) or 0

        offset = (max(1, page) - 1) * page_size
        rows = (await self.session.scalars(query.offset(offset).limit(page_size))).all()

        items = []
        for t in rows:
            is_sender = t.sender_customer_id == customer.id
            txn_ref = t.transaction.external_id if t.transaction else t.external_id
            items.append({
                "transfer_id": t.external_id,
                "transaction_id": txn_ref,
                "external_id": txn_ref,
                "id": txn_ref,
                "direction": "OUTGOING" if is_sender else "INCOMING",
                "counterparty_name": t.recipient_customer.name if is_sender else t.sender_customer.name,
                "counterparty_user_number": t.recipient_customer.omerta_user_number if is_sender else t.sender_customer.omerta_user_number,
                "amount": float(t.amount),
                "currency": t.currency,
                "note": t.note,
                "status": t.status,
                "created_at": t.created_at.isoformat(),
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
        }
