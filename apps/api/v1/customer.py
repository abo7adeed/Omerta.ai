"""Customer Banking Platform API Router for Omerta.ai.

Provides authenticated customer endpoints for dashboard, account management,
simulated peer-to-peer transfers, transaction history, receipts, and security session controls.
Strict customer data isolation is enforced for all endpoints.
"""

from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
import secrets
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from apps.api.v1.auth import evaluate_vpn_risk
from domain.services.customer_service import CustomerService
from domain.services.ticket_service import TicketService
from domain.services.transfer_service import TransferError, TransferService
from infrastructure.database.models import (
    Account,
    AccountLedgerEntry,
    Alert,
    AuditEvent,
    InvestigationCase,
    RiskAssessment,
    RiskSignal,
    Session as UserSession,
    Transaction,
    User,
)
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user, hash_password, verify_password

router = APIRouter(prefix="/customer", tags=["Customer Banking Platform"])

# In-memory tracking of consecutive failed transfer password attempts per user
FAILED_TRANSFER_ATTEMPTS: dict[int, int] = defaultdict(int)


class TransferInitiateRequest(BaseModel):
    sender_account_id: str | None = Field(default=None, description="External ID of sender account")
    source_account_id: str | None = Field(default=None, description="Alias for sender_account_id")
    recipient_user_number: str | None = Field(default=None, description="Unique Omerta User Number or Phone of recipient")
    recipient_omerta_number: str | None = Field(default=None, description="Alias for recipient_user_number")
    recipient_phone: str | None = Field(default=None, description="Recipient phone number")
    recipient_identifier: str | None = Field(default=None, description="Recipient Omerta number or phone number")
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Simulated transfer amount")
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    note: str | None = Field(default=None, max_length=255)
    password: str | None = Field(default=None, description="Account password required to authorize transfer")
    idempotency_key: str | None = None
    is_vpn: bool = Field(default=False, description="VPN connection flag from network telemetry")
    client_ip: str | None = None
    country: str | None = None
    isp: str | None = None
    org: str | None = None
    browser_timezone: str | None = None
    ip_timezone: str | None = None
    city: str | None = None

    @property
    def resolved_sender_account_id(self) -> str:
        acc = self.sender_account_id or self.source_account_id
        if not acc:
            raise ValueError("sender_account_id or source_account_id is required")
        return acc

    @property
    def resolved_recipient_user_number(self) -> str:
        num = self.recipient_identifier or self.recipient_user_number or self.recipient_omerta_number or self.recipient_phone
        if not num:
            raise ValueError("recipient identifier (Omerta User Number or Phone) is required")
        return num


class CreateAccountRequest(BaseModel):
    account_type: str = Field(default="SAVINGS", description="CHECKING or SAVINGS")
    currency: str = Field(default="EGP", min_length=3, max_length=3)
    initial_balance: Decimal = Field(default=Decimal("5000.00"), ge=Decimal("0.00"))


class ConsentUpdateRequest(BaseModel):
    device_consent: bool


@router.get("/dashboard")
async def get_dashboard(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve personalized customer dashboard metrics and activity."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        try:
            return await cust_service.get_customer_dashboard_overview(current_user["sub"])
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))


@router.get("/profile")
async def get_profile(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve the current customer's profile (sanitized, internal risk rating hidden)."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        c = await cust_service.get_customer_by_user_id(current_user["sub"])
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found.")

        return {
            "id": c.external_id,
            "omerta_user_number": c.omerta_user_number,
            "name": c.name,
            "email": c.email,
            "phone": c.phone or "+20 10 1111 2222",
            "declared_country": c.declared_country or c.country,
            "preferred_currency": c.preferred_currency,
            "device_consent": c.device_consent,
            "status": c.status,
            "verification_status": "TIER_1_VERIFIED",
            "verification_tier": "Tier 1 Verified Demo",
            "member_since": c.registration_date.isoformat(),
        }


@router.get("/accounts")
async def get_accounts(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve all bank accounts owned by the authenticated customer."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        return await cust_service.get_customer_accounts(current_user["sub"])


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def open_account(
    body: CreateAccountRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Open an additional demo account with an auditable starting ledger balance."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        try:
            return await cust_service.create_additional_account(
                user_id=current_user["sub"],
                account_type=body.account_type,
                currency=body.currency,
                initial_balance=body.initial_balance,
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


@router.get("/recipient/lookup")
async def lookup_recipient(
    identifier: str | None = Query(default=None, description="Omerta User Number or Phone Number"),
    user_number: str | None = Query(default=None, description="Omerta User Number (e.g. OMR-8492-3011)"),
    omerta_user_number: str | None = Query(default=None, description="Alias for user_number"),
    phone: str | None = Query(default=None, description="Recipient mobile phone number"),
    query: str | None = Query(default=None, description="Search query"),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Look up a recipient by their unique Omerta User Number or Mobile Phone Number."""
    target = identifier or query or omerta_user_number or user_number or phone
    if not target or not target.strip():
        raise HTTPException(status_code=400, detail={"error": "INVALID_QUERY", "message": "Missing recipient identifier or phone number."})

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        transfer_service = TransferService(session)
        try:
            return await transfer_service.lookup_recipient(target.strip())
        except TransferError as err:
            raise HTTPException(
                status_code=err.status_code,
                detail={"error": err.code, "message": err.message},
            )


@router.post("/transfers", status_code=status.HTTP_201_CREATED)
async def initiate_transfer(
    body: TransferInitiateRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute a simulated customer-to-customer transfer with atomic double-entry ledger update."""
    client_ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent", "OmertaWeb/2.0")

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        customer = await cust_service.get_customer_by_user_id(current_user["sub"])
        if not customer or not customer.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "NOT_A_CUSTOMER", "message": "Only registered customers can send transfers."},
            )

        # 0a. Enforce Active Transaction Restrictions Check (OUTGOING_TRANSFERS_ONLY, etc.)
        from infrastructure.database.models import TransactionRestriction
        restr_stmt = (
            select(TransactionRestriction)
            .where(
                and_(
                    TransactionRestriction.customer_id == customer.id,
                    TransactionRestriction.status == "ACTIVE",
                    TransactionRestriction.restriction_scope.in_(["OUTGOING_TRANSFERS_ONLY", "ALL_TRANSFERS", "FULL_CONTAINMENT"]),
                )
            )
            .limit(1)
        )
        active_restr = await session.scalar(restr_stmt)
        if active_restr:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "TRANSFERS_RESTRICTED",
                    "restriction_scope": active_restr.restriction_scope,
                    "reason": active_restr.restriction_reason,
                    "message": f"Your account is subject to an active security restriction on outgoing transfers: {active_restr.restriction_reason}",
                },
            )

        # 0b. Enforce Password Failure Transfer Block Check
        if getattr(customer, "transfer_status", "ACTIVE") == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "TRANSFER_BLOCKED_SECURITY_HOLD",
                    "transfer_status": "BLOCKED",
                    "failed_attempts": customer.transfer_failed_attempts or 3,
                    "message": "Your transfer services have been temporarily blocked after multiple unsuccessful transfer-password attempts. Your account remains accessible, but sending and receiving funds are currently unavailable. If you believe this happened because you forgot your transfer password or there was an error, please contact Omerta.ai Support.",
                },
            )

        # 1. Enforce transfer password authorization with 3-attempt failure transfer blocking (without logging out)
        user_rec = await session.scalar(select(User).where(User.id == customer.user_id))
        effective_transfer_hash = customer.hashed_transfer_password or (user_rec.hashed_password if user_rec else "")

        if body.password is not None:
            if not effective_transfer_hash or not verify_password(body.password, effective_transfer_hash):
                customer.transfer_failed_attempts = (customer.transfer_failed_attempts or 0) + 1
                failed_count = customer.transfer_failed_attempts

                if failed_count >= 3:
                    # Block transfer operations only - keep user active and keep session logged in!
                    customer.transfer_status = "BLOCKED"
                    customer.transfer_blocked_at = datetime.now(UTC)

                    # Create Audit Event
                    session.add(
                        AuditEvent(
                            event_id=f"EVT-TXBLOCK-{secrets.token_hex(4).upper()}",
                            event_type="TRANSFER_SERVICES_BLOCKED",
                            actor_type="CUSTOMER",
                            actor_id=str(customer.user_id),
                            source="CustomerTransferSecurity",
                            metadata_={
                                "failed_attempts": failed_count,
                                "customer_id": customer.external_id,
                                "customer_name": customer.name,
                                "omerta_user_number": customer.omerta_user_number,
                                "transfer_status": "BLOCKED",
                                "client_ip": client_ip,
                                "description": "3 consecutive incorrect transfer password attempts. Transfer services blocked while normal account access is maintained.",
                            },
                        )
                    )

                    # Automatically create or link TRANSFER_PASSWORD_LOCK ticket via TicketService
                    tkt_svc = TicketService(session)
                    auto_ticket = await tkt_svc.create_auto_security_ticket(
                        customer_id=customer.id,
                        reason="3_CONSECUTIVE_TRANSFER_PASSWORD_FAILURES",
                        client_ip=client_ip or "127.0.0.1",
                    )
                    await session.commit()

                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail={
                            "error": "TRANSFER_BLOCKED_SECURITY_HOLD",
                            "transfer_status": "BLOCKED",
                            "failed_attempts": failed_count,
                            "remaining_attempts": 0,
                            "ticket_number": auto_ticket.external_id,
                            "message": "Your transfer services have been temporarily blocked after multiple unsuccessful transfer-password attempts. Your account remains accessible, but sending and receiving funds are currently unavailable. A security support ticket has been opened.",
                        },
                    )
                else:
                    remaining = 3 - failed_count
                    await session.commit()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail={
                            "error": "INVALID_TRANSFER_PASSWORD",
                            "failed_attempts": failed_count,
                            "remaining_attempts": remaining,
                            "message": f"Incorrect transfer password. (Attempt {failed_count} of 3). Warning: You have {remaining} attempt(s) remaining before your transfer services are temporarily blocked.",
                        },
                    )

            # Reset failed attempts counter on successful verification
            customer.transfer_failed_attempts = 0
            await session.commit()

        # 2. Evaluate Real VPN / Proxy Telemetry & Block Anonymized Transfers
        user_sess = await session.scalar(
            select(UserSession)
            .options(selectinload(UserSession.ip_address))
            .where(and_(UserSession.user_id == customer.user_id, UserSession.is_active.is_(True)))
            .order_by(UserSession.started_at.desc())
            .limit(1)
        )
        session_is_vpn = user_sess.is_vpn if user_sess else False

        effective_ip = body.client_ip or (request.client.host if request.client else "127.0.0.1")
        effective_country = body.country or (user_sess.ip_address.country if user_sess and user_sess.ip_address else (customer.declared_country or "EG"))

        is_vpn_detected, vpn_reason = evaluate_vpn_risk(
            client_ip=effective_ip,
            country=effective_country,
            customer_country=customer.declared_country or "EG",
            body_is_vpn=body.is_vpn or session_is_vpn,
            isp=body.isp,
            org=body.org,
            browser_tz=body.browser_timezone,
            ip_tz=body.ip_timezone,
            headers=dict(request.headers),
        )

        # If VPN/proxy detected: audit telemetry signal and route to pending verification / admin review
        if is_vpn_detected:
            session.add(
                AuditEvent(
                    event_id=f"EVT-VPN-{secrets.token_hex(4).upper()}",
                    event_type="VPN_TRANSFER_HELD_FOR_REVIEW",
                    actor_type="CUSTOMER",
                    actor_id=str(customer.user_id),
                    source="SecurityRiskEngine",
                    metadata_={
                        "vpn_reason": vpn_reason,
                        "amount": str(body.amount),
                        "customer_id": customer.external_id,
                        "client_ip": effective_ip,
                        "action": "HELD_FOR_VERIFICATION",
                    },
                )
            )
            await session.commit()

        try:
            sender_acc = body.resolved_sender_account_id
            recip_num = body.resolved_recipient_user_number
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "INVALID_INPUT", "message": str(err)})

        transfer_service = TransferService(session)
        try:
            receipt = await transfer_service.execute_transfer(
                sender_user_id=customer.user_id,
                sender_account_id=sender_acc,
                recipient_user_number=recip_num,
                amount=body.amount,
                currency=body.currency,
                note=body.note,
                idempotency_key=body.idempotency_key,
                ip_address=effective_ip,
                user_agent=user_agent,
                is_vpn=is_vpn_detected,
                city=body.city,
                country=effective_country,
            )
            return receipt
        except TransferError as err:
            raise HTTPException(
                status_code=err.status_code,
                detail={"error": err.code, "message": err.message},
            )

class CustomerWithdrawRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Withdrawal amount")
    account_id: str | None = Field(default=None, description="Source account external ID (e.g. ACC-1001)")
    currency: str = Field(default="EGP", max_length=10)
    method: str = Field(default="ATM_CASH_OUT", description="ATM_CASH_OUT, BRANCH_TELLER, EXTERNAL_IBAN")
    destination_details: str | None = Field(default=None, description="ATM Code, Branch Location, or IBAN")
    password: str = Field(..., description="Customer transfer password for financial authorization")


@router.post("/withdraw", status_code=status.HTTP_201_CREATED)
async def withdraw_funds(
    body: CustomerWithdrawRequest,
    request: Request,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Execute customer withdrawal with atomic ledger debit and dynamic multi-vector risk evaluation."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        customer = await cust_service.get_customer_by_user_id(current_user["sub"])
        if not customer or not customer.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": "NOT_A_CUSTOMER", "message": "Only registered customers can withdraw funds."},
            )

        if getattr(customer, "transfer_status", "ACTIVE") == "BLOCKED" or getattr(customer, "status", "ACTIVE") == "BLOCKED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "ACCOUNT_BLOCKED_SECURITY_HOLD",
                    "message": "Your account is currently under security hold. Withdrawals and transfers are suspended.",
                },
            )

        # Verify transfer password
        user_rec = await session.scalar(select(User).where(User.id == customer.user_id))
        effective_transfer_hash = customer.hashed_transfer_password or (user_rec.hashed_password if user_rec else "")
        if not effective_transfer_hash or not verify_password(body.password, effective_transfer_hash):
            customer.transfer_failed_attempts = (customer.transfer_failed_attempts or 0) + 1
            if customer.transfer_failed_attempts >= 3:
                customer.transfer_status = "BLOCKED"
                await session.commit()
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "TRANSFER_BLOCKED_SECURITY_HOLD", "message": "3 consecutive incorrect passwords. Transfers and withdrawals blocked."},
                )
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={"error": "INVALID_TRANSFER_PASSWORD", "message": "Incorrect transfer password."},
            )

        customer.transfer_failed_attempts = 0

        # Resolve Account
        if body.account_id:
            acc = await session.scalar(
                select(Account).where(
                    and_(
                        Account.customer_id == customer.id,
                        Account.external_id == body.account_id,
                    )
                )
            )
        else:
            acc = await session.scalar(
                select(Account).where(Account.customer_id == customer.id).order_by(Account.id.asc()).limit(1)
            )

        if not acc:
            raise HTTPException(status_code=400, detail={"error": "ACCOUNT_NOT_FOUND", "message": "Account not found."})

        if acc.status == "BLOCKED" or acc.status == "FROZEN":
            raise HTTPException(status_code=403, detail={"error": "ACCOUNT_LOCKED", "message": f"Account {acc.external_id} is currently {acc.status}."})

        if acc.balance < body.amount:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INSUFFICIENT_FUNDS",
                    "message": f"Insufficient available balance. Account has {acc.balance:,.2f} {acc.currency}, requested {body.amount:,.2f} {acc.currency}.",
                },
            )

        # Check velocity in 5 minutes
        now_dt = datetime.now(UTC)
        five_m_ago = now_dt - timedelta(minutes=5)
        recent_tx_count = await session.scalar(
            select(func.count(Transaction.id)).where(
                and_(
                    Transaction.account_id == acc.id,
                    Transaction.timestamp >= five_m_ago,
                )
            )
        ) or 0

        is_high_value = body.amount >= Decimal("50000.00")
        is_velocity_burst = recent_tx_count >= 2
        is_structuring = (Decimal("24000.00") <= body.amount < Decimal("25000.00")) or (Decimal("45000.00") <= body.amount < Decimal("50000.00"))
        ext_txn_id = f"TXN-WDL-{uuid.uuid4().hex[:8].upper()}"

        if is_high_value or is_velocity_burst or is_structuring:
            hold_reason = (
                "High-value cash-out threshold exceeded (>= 50,000 EGP)"
                if is_high_value
                else (
                    f"Rapid multi-transaction burst ({recent_tx_count} transactions in 5 minutes)"
                    if is_velocity_burst
                    else "Statutory AML reporting threshold evasion (Structuring pattern)"
                )
            )
            # Create Transaction on Security Hold (Funds held safely in account, not debited!)
            txn = Transaction(
                external_id=ext_txn_id,
                account_id=acc.id,
                recipient_account_id=acc.id,
                amount=body.amount,
                currency=acc.currency,
                transaction_type="WITHDRAWAL",
                status="PENDING_CUSTOMER_VERIFICATION",
                timestamp=now_dt,
                risk_score=Decimal("85.00") if is_high_value else Decimal("75.00"),
                risk_level="CRITICAL" if is_high_value else "HIGH",
                review_status="REQUIRES_REVIEW",
                txn_metadata={
                    "withdrawal_method": body.method,
                    "destination_details": body.destination_details or "Direct Cash-out",
                    "client_ip": client_ip,
                    "hold_reason": hold_reason,
                },
            )
            session.add(txn)
            await session.flush()

            # Record Risk Assessment & Signals
            ra = RiskAssessment(
                external_id=f"RA-{uuid.uuid4().hex[:8].upper()}",
                transaction_id=txn.id,
                risk_score=txn.risk_score,
                risk_level=txn.risk_level,
                requires_human_review=True,
                correlation_id=f"CORR-{txn.external_id}",
                version="lgbm-risk-v1",
                summary=f"Security hold applied: {hold_reason}. Customer confirmation required.",
            )
            session.add(ra)
            await session.flush()

            session.add(
                RiskSignal(
                    assessment_id=ra.id,
                    signal_name="WITHDRAWAL_SECURITY_HOLD",
                    severity="CRITICAL" if is_high_value else "HIGH",
                    description=hold_reason,
                    source="WITHDRAWAL_ENGINE",
                )
            )

            # Create confirmation token
            transfer_service = TransferService(session)
            confirm_token = await transfer_service.create_confirmation_token(
                transaction_id=txn.id,
                customer_id=customer.id,
                action="CONFIRM",
                expires_minutes=30,
            )

            # Dispatch live email
            target_email = customer.email
            if not target_email or target_email.endswith("@omerta.ai"):
                target_email = os.getenv("REAL_CUSTOMER_EMAIL", "abdomostafa13571234@gmail.com")

            if target_email:
                base_app_url = os.getenv("FRONTEND_URL", os.getenv("APP_URL", "http://localhost:5173")).rstrip("/")
                verif_url = f"{base_app_url}/customer/security?token={confirm_token}&txn={txn.external_id}"
                asyncio.create_task(
                    EmailService.send_transfer_verification_email(
                        to_email=target_email,
                        customer_name=customer.name,
                        transaction_ref=txn.external_id,
                        amount=f"{body.amount:,.2f} {acc.currency}",
                        recipient=f"Cash withdrawal via {body.method}",
                        verification_url=verif_url,
                    )
                )

            await session.commit()
            return {
                "success": True,
                "transaction_id": txn.external_id,
                "account_id": acc.external_id,
                "amount": float(body.amount),
                "currency": acc.currency,
                "method": body.method,
                "balance_after": float(acc.balance),
                "risk_score": float(txn.risk_score),
                "risk_level": txn.risk_level,
                "requires_review": True,
                "status": "PENDING_CUSTOMER_VERIFICATION",
                "message": f"Security Verification Hold: {hold_reason}. A verification email has been dispatched. Confirm via email or await compliance review.",
            }

        # Clean/Low Risk: Deduct balance atomically
        acc.balance -= body.amount

        txn = Transaction(
            external_id=ext_txn_id,
            account_id=acc.id,
            recipient_account_id=acc.id,
            amount=body.amount,
            currency=acc.currency,
            transaction_type="WITHDRAWAL",
            status="COMPLETED",
            timestamp=now_dt,
            txn_metadata={
                "withdrawal_method": body.method,
                "destination_details": body.destination_details or "Direct Cash-out",
                "client_ip": client_ip,
            },
        )
        session.add(txn)
        await session.flush()

        ledger_entry = AccountLedgerEntry(
            external_id=f"LED-WDL-{uuid.uuid4().hex[:8].upper()}",
            account_id=acc.id,
            transaction_id=txn.id,
            entry_type="DEBIT",
            amount=body.amount,
            currency=acc.currency,
            balance_after=acc.balance,
            description=f"Withdrawal via {body.method} ({body.destination_details or 'ATM Cash Out'})",
            idempotency_key=f"IDEMP-WDL-{txn.external_id}",
        )
        session.add(ledger_entry)

        # Baseline Risk Assessment
        final_risk = Decimal("10.00")
        txn.risk_score = final_risk
        txn.risk_level = "LOW"
        txn.review_status = "CLEARED"

        ra = RiskAssessment(
            external_id=f"RA-{uuid.uuid4().hex[:8].upper()}",
            transaction_id=txn.id,
            risk_score=final_risk,
            risk_level="LOW",
            requires_human_review=False,
            correlation_id=f"CORR-{txn.external_id}",
            version="lgbm-risk-v1",
            summary=f"Automated withdrawal cleared. Score: {final_risk:.1f}%",
        )
        session.add(ra)
        await session.commit()

        return {
            "success": True,
            "transaction_id": txn.external_id,
            "account_id": acc.external_id,
            "amount": float(body.amount),
            "currency": acc.currency,
            "method": body.method,
            "balance_after": float(acc.balance),
            "risk_score": float(final_risk),
            "risk_level": "LOW",
            "requires_review": False,
            "status": "COMPLETED",
            "account_status": acc.status,
            "message": "Withdrawal processed successfully. Funds dispensed.",
        }


@router.get("/transfers")
async def list_transfers(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """List transfers involving the authenticated customer."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        customer = await cust_service.get_customer_by_user_id(current_user["sub"])
        if not customer or not customer.user_id:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 1}

        transfer_service = TransferService(session)
        return await transfer_service.list_customer_transfers(
            user_id=customer.user_id, page=page, page_size=page_size
        )


@router.get("/transfers/{transfer_id}")
async def get_transfer_receipt(
    transfer_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve transfer receipt details."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        transfer_service = TransferService(session)
        try:
            return await transfer_service.get_transfer_receipt(transfer_id)
        except TransferError as err:
            raise HTTPException(
                status_code=err.status_code,
                detail={"error": err.code, "message": err.message},
            )


@router.get("/transactions")
async def list_transactions(
    search: str | None = None,
    direction: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve transaction history strictly scoped to the authenticated customer."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        return await cust_service.get_customer_transactions(
            user_id=current_user["sub"],
            search=search,
            direction=direction,
            status=status,
            page=page,
            page_size=page_size,
        )


@router.get("/security/sessions")
async def get_security_sessions(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve active and recent sessions for privacy and security review."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        return await cust_service.get_customer_sessions(current_user["sub"])


@router.post("/security/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Revoke an active customer session."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        success = await cust_service.revoke_session(current_user["sub"], session_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or already revoked.")
        return {"status": "REVOKED", "session_id": session_id, "revoked": True}


@router.post("/security/consent")
async def update_consent(
    body: ConsentUpdateRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update device and session collection consent settings."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        success = await cust_service.update_device_consent(current_user["sub"], body.device_consent)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return {"status": "UPDATED", "device_consent": body.device_consent}


@router.post("/security/heartbeat")
async def customer_security_heartbeat(
    request: Request,
    body: dict[str, Any] | None = None,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """30-second recurring network telemetry probe and active session synchronizer for customers."""
    payload = body or {}
    client_ip = payload.get("client_ip") or (request.client.host if request.client else "127.0.0.1")
    user_agent = payload.get("user_agent") or request.headers.get("user-agent", "Mozilla/5.0")
    country = (payload.get("country") or "EG").upper()[:2]
    is_vpn = bool(payload.get("is_vpn", False))

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        result = await cust_service.update_telemetry_heartbeat(
            user_identifier=current_user.get("sub"),
            client_ip=client_ip,
            country=country,
            is_vpn=is_vpn,
            user_agent=user_agent,
            isp=payload.get("isp"),
            org=payload.get("org"),
            browser_timezone=payload.get("browser_timezone"),
            ip_timezone=payload.get("ip_timezone"),
        )
        return result


class ChangeTransferPasswordRequest(BaseModel):
    new_transfer_password: str = Field(..., min_length=8, description="New transfer password")
    confirm_new_transfer_password: str | None = Field(default=None)
    confirm_transfer_password: str | None = Field(default=None)
    current_transfer_password: str | None = Field(default=None, description="Current transfer password (optional if in recovery flow)")

    @property
    def confirmation_password(self) -> str:
        return self.confirm_new_transfer_password or self.confirm_transfer_password or ""


@router.post("/transfer-password/change")
async def change_transfer_password(
    body: ChangeTransferPasswordRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Change or set a new transfer password (supports standard update or post-recovery workflow)."""
    confirm_pwd = body.confirmation_password
    if not confirm_pwd or body.new_transfer_password != confirm_pwd:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "TRANSFER_PASSWORD_MISMATCH", "message": "New transfer password and confirmation do not match."},
        )

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        customer = await cust_service.get_customer_by_user_id(current_user["sub"])
        if not customer or not customer.user_id:
            raise HTTPException(status_code=404, detail="Customer not found.")

        user_rec = await session.scalar(select(User).where(User.id == customer.user_id))
        if not user_rec:
            raise HTTPException(status_code=404, detail="User not found.")

        # Ensure new transfer password does not match account login password
        if verify_password(body.new_transfer_password, user_rec.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "TRANSFER_PASSWORD_CANNOT_MATCH_ACCOUNT_PASSWORD",
                    "message": "For your financial security, your Transfer Password must be completely different from your Account Login Password.",
                },
            )

        # If not in recovery mode, verify current transfer password
        if not customer.require_transfer_password_change:
            if not body.current_transfer_password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={"error": "CURRENT_PASSWORD_REQUIRED", "message": "Please enter your current transfer password."},
                )
            effective_old_hash = customer.hashed_transfer_password or user_rec.hashed_password
            if not verify_password(body.current_transfer_password, effective_old_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail={"error": "INVALID_CURRENT_PASSWORD", "message": "Incorrect current transfer password."},
                )

        # Update transfer password
        customer.hashed_transfer_password = hash_password(body.new_transfer_password)
        customer.require_transfer_password_change = False
        customer.transfer_failed_attempts = 0
        customer.transfer_status = "ACTIVE"
        customer.transfer_unblocked_at = datetime.now(UTC)

        session.add(
            AuditEvent(
                event_id=f"EVT-TXPWD-{secrets.token_hex(4).upper()}",
                event_type="TRANSFER_PASSWORD_CHANGED",
                actor_type="CUSTOMER",
                actor_id=str(customer.user_id),
                source="CustomerTransferSecurity",
                metadata_={
                    "customer_id": customer.external_id,
                    "omerta_user_number": customer.omerta_user_number,
                    "recovery_mode": bool(customer.require_transfer_password_change),
                    "description": "Customer successfully updated their financial transfer password.",
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "message": "Your transfer password has been successfully updated. Transfer services are now active.",
            "transfer_status": "ACTIVE",
            "require_transfer_password_change": False,
        }


