"""Admin Control Center API Router for Omerta.ai.

Provides administrative controls, platform oversight, customer status management,
auditable ledger demo balance adjustments, review queue decisions, and configuration inspection.
Protected by role-based authorization (ADMINISTRATOR, FRAUD_ANALYST, SENIOR_INVESTIGATOR).
"""

import secrets
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.services.account_service import AccountService
from domain.services.customer_service import CustomerService
from domain.services.email_service import EmailService
from infrastructure.database.models import (
    Account,
    Alert,
    AuditEvent,
    Customer,
    IdentityVerification,
    InvestigationCase,
    RiskAssessment,
    SupportTicket,
    Transaction,
    Transfer,
    User,
)
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user, require_role

router = APIRouter(prefix="/admin", tags=["Admin Control Center"])

ADMIN_ROLES = ["ADMINISTRATOR", "FRAUD_ANALYST", "SENIOR_INVESTIGATOR", "AUDITOR"]


class UserStatusUpdateRequest(BaseModel):
    is_active: bool
    reason: str = Field(..., min_length=3, description="Mandatory audit reason for status change")


class BalanceAdjustmentRequest(BaseModel):
    adjustment_amount: Decimal = Field(..., description="Positive to credit, negative to debit")
    reason: str = Field(..., min_length=5, description="Mandatory compliance reason for demo adjustment")


class TransactionReviewDecision(BaseModel):
    disposition: str = Field(..., description="APPROVE | FLAG_INVESTIGATION | DISMISS")
    rationale: str = Field(..., min_length=5, description="Detailed review rationale")


@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Provide high-level operational overview for the admin control center."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Total and active customers
        total_cust = await session.scalar(select(func.count(Customer.id))) or 0
        active_cust = await session.scalar(select(func.count(Customer.id)).where(Customer.status == "ACTIVE")) or 0

        # Accounts
        total_accounts = await session.scalar(select(func.count(Account.id))) or 0

        # Transactions
        total_txns = await session.scalar(select(func.count(Transaction.id))) or 0
        total_volume = await session.scalar(select(func.sum(Transaction.amount))) or Decimal("0.00")

        # Review Queue (strictly risk_score > 40.00 or review_status == 'REQUIRES_REVIEW')
        review_count = await session.scalar(
            select(func.count(Transaction.id)).where(
                (Transaction.risk_score > Decimal("40.00")) | (Transaction.review_status == "REQUIRES_REVIEW")
            )
        ) or 0

        # Open investigations
        open_cases = await session.scalar(
            select(func.count(InvestigationCase.id)).where(InvestigationCase.status != "RESOLVED")
        ) or 0

        # Risk distribution
        low_risk = await session.scalar(select(func.count(Transaction.id)).where(Transaction.risk_score <= Decimal("20.00"))) or 0
        mod_risk = await session.scalar(select(func.count(Transaction.id)).where(Transaction.risk_score > Decimal("20.00"), Transaction.risk_score <= Decimal("40.00"))) or 0
        high_risk = await session.scalar(select(func.count(Transaction.id)).where(Transaction.risk_score > Decimal("40.00"), Transaction.risk_score <= Decimal("70.00"))) or 0
        crit_risk = await session.scalar(select(func.count(Transaction.id)).where(Transaction.risk_score > Decimal("70.00"))) or 0

        return {
            "summary": {
                "total_customers": total_cust,
                "active_customers": active_cust,
                "total_accounts": total_accounts,
                "total_transactions": total_txns,
                "total_demo_volume": float(total_volume),
                "transactions_requiring_review": review_count,
                "open_investigations": open_cases,
                "human_review_threshold": 40.0,
            },
            "risk_distribution": {
                "low": low_risk,
                "moderate": mod_risk,
                "high": high_risk,
                "critical": crit_risk,
            },
            "is_synthetic": True,
            "demo_notice": "Omerta.ai Admin Intelligence Platform — Simulated Demo Environment",
        }


@router.get("/users")
async def list_admin_users(
    search: str | None = None,
    customer_type: str | None = None,
    risk_level: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Search and manage registered customers and system users."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        return await cust_service.list_customers(
            search=search,
            customer_type=customer_type,
            risk_level=risk_level,
            page=page,
            page_size=page_size,
        )


@router.get("/users/{identifier}")
async def get_admin_user_detail(
    identifier: str,
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Retrieve complete 360-degree customer details for investigation."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust_service = CustomerService(session)
        res = await cust_service.get_customer_360(identifier)
        if not res:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
        return res


@router.post("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    body: UserStatusUpdateRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR"])),
) -> dict[str, Any]:
    """Suspend or reactivate a demo customer/user."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        user = await session.scalar(
            select(User).options(selectinload(User.customer)).where(User.external_id == user_id)
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        old_status = user.is_active
        user.is_active = body.is_active
        if user.customer:
            user.customer.status = "ACTIVE" if body.is_active else "SUSPENDED"

        audit_event = AuditEvent(
            event_id=f"EVT-ADM-{user.id}",
            event_type="USER_STATUS_MODIFIED",
            actor_type="ADMIN",
            actor_id=current_user.get("sub"),
            source="AdminService",
            metadata_={
                "user_id": user.external_id,
                "old_status": old_status,
                "new_status": body.is_active,
                "reason": body.reason,
            },
        )
        session.add(audit_event)
        await session.commit()

        return {
            "user_id": user.external_id,
            "is_active": user.is_active,
            "customer_status": user.customer.status if user.customer else None,
            "reason": body.reason,
        }


@router.get("/accounts")
async def list_admin_accounts(
    search: str | None = None,
    account_type: str | None = None,
    currency: str | None = None,
    risk_level: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """List and inspect bank accounts across the platform."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        acc_service = AccountService(session)
        return await acc_service.list_accounts(
            search=search,
            account_type=account_type,
            currency=currency,
            risk_level=risk_level,
            status=status,
            page=page,
            page_size=page_size,
        )


@router.post("/accounts/{account_id}/adjustment")
async def apply_account_adjustment(
    account_id: str,
    body: BalanceAdjustmentRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR"])),
) -> dict[str, Any]:
    """Apply an authorized demo balance adjustment through an immutable double-entry ledger record."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        acc_service = AccountService(session)
        try:
            return await acc_service.apply_admin_balance_adjustment(
                account_identifier=account_id,
                adjustment_amount=body.adjustment_amount,
                reason=body.reason,
                admin_actor_id=current_user.get("sub", "ADMIN"),
            )
        except ValueError as err:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(err))


class AdminTransactionActionRequest(BaseModel):
    rationale: str = Field(default="Analyst verified identity and transaction legitimacy. Hold released.", min_length=1)


@router.post("/transactions/{transaction_id}/approve")
async def approve_held_transaction(
    transaction_id: str,
    body: AdminTransactionActionRequest | None = None,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SENIOR_INVESTIGATOR", "FRAUD_ANALYST"])),
) -> dict[str, Any]:
    """Approve a held transaction, release funds and atomically settle in the double-entry ledger."""
    rationale = body.rationale if body and body.rationale else "Analyst approved and released funds."
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Match transaction by external ID or integer ID
        is_num = str(transaction_id).isdigit()
        txn_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.account),
                selectinload(Transaction.recipient_account),
            )
            .where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id.in_(
                        select(Transfer.transaction_id).where(Transfer.external_id == transaction_id)
                    ) if not is_num else False,
                    Transaction.id == int(transaction_id) if is_num else False,
                )
            )
            .limit(1)
        )
        txn = await session.scalar(txn_stmt)
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

        transfer = await session.scalar(
            select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        )

        if txn.status == "COMPLETED":
            return {
                "success": True,
                "transaction_id": txn.external_id,
                "status": "COMPLETED",
                "message": "Transaction is already completed and settled.",
            }

        # Settle funds if this is a transfer and accounts are available
        from domain.services.transfer_service import TransferService, TransferError
        transfer_svc = TransferService(session)

        if transfer and txn.account_id and txn.recipient_account_id:
            try:
                await transfer_svc._execute_atomic_settlement(
                    transaction_id=txn.id,
                    transfer_id=transfer.id,
                    source_account_id=txn.account_id,
                    recipient_account_id=txn.recipient_account_id,
                    amount=txn.amount,
                    currency=txn.currency,
                    idempotency_prefix=f"{transfer.idempotency_key or 'ADMIN'}-APPV",
                    description_prefix=f"Compliance Approved: Transfer to {txn.recipient_account.customer_name if txn.recipient_account else 'Recipient'}",
                )
            except TransferError as err:
                if err.code != "ALREADY_SETTLED":
                    raise HTTPException(status_code=err.status_code, detail={"error": err.code, "message": err.message})
        elif txn.transaction_type == "WITHDRAWAL" and txn.account_id:
            src_acc = await session.scalar(select(Account).where(Account.id == txn.account_id).with_for_update())
            if src_acc:
                if src_acc.balance < txn.amount:
                    raise HTTPException(status_code=400, detail={"error": "INSUFFICIENT_FUNDS", "message": "Source account balance insufficient."})
                src_acc.balance -= txn.amount
                debit_entry = AccountLedgerEntry(
                    external_id=f"LED-WDL-{secrets.token_hex(4).upper()}",
                    account_id=src_acc.id,
                    transaction_id=txn.id,
                    entry_type="DEBIT",
                    amount=txn.amount,
                    currency=txn.currency,
                    balance_after=src_acc.balance,
                    description=f"Compliance Approved Withdrawal ({txn.external_id})",
                    idempotency_key=f"IDEMP-WDL-ADM-{txn.external_id}",
                )
                session.add(debit_entry)

        txn.status = "COMPLETED"
        if transfer:
            transfer.status = "COMPLETED"
        txn.review_status = "COMPLETED"

        # Resolve any associated InvestigationCase
        case = await session.scalar(
            select(InvestigationCase).where(InvestigationCase.transaction_id == txn.id).limit(1)
        )
        if case:
            case.status = "RESOLVED"

        # Resolve alerts
        alerts = (await session.scalars(select(Alert).where(Alert.transaction_id == txn.id))).all()
        for al in alerts:
            al.status = "RESOLVED"

        # Audit event
        session.add(
            AuditEvent(
                event_id=f"EVT-ADM-APPV-{secrets.token_hex(4).upper()}",
                event_type="TRANSACTION_APPROVED_BY_ADMIN",
                actor_type="ADMIN",
                actor_id=str(current_user.get("sub", "ADMIN")),
                source="AdminService",
                transaction_id=txn.external_id,
                metadata_={
                    "transaction_id": txn.external_id,
                    "action": "APPROVE",
                    "rationale": rationale,
                    "previous_status": txn.status,
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "transaction_id": txn.external_id,
            "status": "COMPLETED",
            "review_status": "COMPLETED",
            "message": "Transaction approved and double-entry ledger settlement executed successfully.",
        }


@router.post("/transactions/{transaction_id}/reject")
async def reject_held_transaction(
    transaction_id: str,
    body: AdminTransactionActionRequest | None = None,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SENIOR_INVESTIGATOR", "FRAUD_ANALYST"])),
) -> dict[str, Any]:
    """Reject a held transaction and cancel fund movement."""
    rationale = body.rationale if body and body.rationale else "Transfer rejected due to confirmed fraud or unauthorized activity."
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        is_num = str(transaction_id).isdigit()
        txn_stmt = (
            select(Transaction)
            .where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id.in_(
                        select(Transfer.transaction_id).where(Transfer.external_id == transaction_id)
                    ) if not is_num else False,
                    Transaction.id == int(transaction_id) if is_num else False,
                )
            )
            .limit(1)
        )
        txn = await session.scalar(txn_stmt)
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

        transfer = await session.scalar(
            select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        )

        txn.status = "REJECTED"
        if transfer:
            transfer.status = "REJECTED"
        txn.review_status = "REJECTED"

        case = await session.scalar(
            select(InvestigationCase).where(InvestigationCase.transaction_id == txn.id).limit(1)
        )
        if case:
            case.status = "RESOLVED"

        alerts = (await session.scalars(select(Alert).where(Alert.transaction_id == txn.id))).all()
        for al in alerts:
            al.status = "DISMISSED"

        session.add(
            AuditEvent(
                event_id=f"EVT-ADM-REJ-{secrets.token_hex(4).upper()}",
                event_type="TRANSACTION_REJECTED_BY_ADMIN",
                actor_type="ADMIN",
                actor_id=str(current_user.get("sub", "ADMIN")),
                source="AdminService",
                transaction_id=txn.external_id,
                metadata_={
                    "transaction_id": txn.external_id,
                    "action": "REJECT",
                    "rationale": rationale,
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "transaction_id": txn.external_id,
            "status": "REJECTED",
            "review_status": "REJECTED",
            "message": "Transaction rejected and cancelled successfully.",
        }


@router.post("/transactions/{transaction_id}/review")
async def record_transaction_review(
    transaction_id: str,
    body: TransactionReviewDecision,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "SENIOR_INVESTIGATOR", "FRAUD_ANALYST"])),
) -> dict[str, Any]:
    """Record an analyst review decision for a flagged transaction."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        is_num = str(transaction_id).isdigit()
        txn_stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.account),
                selectinload(Transaction.recipient_account),
            )
            .where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id.in_(
                        select(Transfer.transaction_id).where(Transfer.external_id == transaction_id)
                    ) if not is_num else False,
                    Transaction.id == int(transaction_id) if is_num else False,
                )
            )
            .limit(1)
        )
        txn = await session.scalar(txn_stmt)
        if not txn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")

        transfer = await session.scalar(
            select(Transfer).where(Transfer.transaction_id == txn.id).limit(1)
        )

        old_status = txn.review_status
        if body.disposition == "APPROVE":
            # Settle if held
            if transfer and txn.status != "COMPLETED" and txn.account_id and txn.recipient_account_id:
                from domain.services.transfer_service import TransferService, TransferError
                transfer_svc = TransferService(session)
                try:
                    await transfer_svc._execute_atomic_settlement(
                        transaction_id=txn.id,
                        transfer_id=transfer.id,
                        source_account_id=txn.account_id,
                        recipient_account_id=txn.recipient_account_id,
                        amount=txn.amount,
                        currency=txn.currency,
                        idempotency_prefix=f"{transfer.idempotency_key or 'ADMIN'}-REV",
                        description_prefix=f"Analyst Approved: Transfer to {txn.recipient_account.customer_name if txn.recipient_account else 'Recipient'}",
                    )
                except TransferError as err:
                    if err.code != "ALREADY_SETTLED":
                        raise HTTPException(status_code=err.status_code, detail={"error": err.code, "message": err.message})

            txn.status = "COMPLETED"
            if transfer:
                transfer.status = "COMPLETED"
            txn.review_status = "COMPLETED"
        elif body.disposition in ("DISMISS", "REJECT"):
            txn.status = "REJECTED"
            if transfer:
                transfer.status = "REJECTED"
            txn.review_status = "DISMISSED"
        else:
            txn.review_status = "IN_REVIEW"

        audit_event = AuditEvent(
            event_id=f"EVT-REV-{secrets.token_hex(4).upper()}",
            event_type="TRANSACTION_REVIEW_DECISION",
            actor_type="ANALYST",
            actor_id=str(current_user.get("sub", "ADMIN")),
            source="AdminService",
            transaction_id=txn.external_id,
            metadata_={
                "transaction_id": txn.external_id,
                "disposition": body.disposition,
                "rationale": body.rationale,
                "old_review_status": old_status,
                "new_review_status": txn.review_status,
                "transaction_status": txn.status,
            },
        )
        session.add(audit_event)
        await session.commit()

        return {
            "transaction_id": txn.external_id,
            "disposition": body.disposition,
            "rationale": body.rationale,
            "review_status": txn.review_status,
            "status": txn.status,
        }


class CreateStaffRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., min_length=5, max_length=120)
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)
    role: str = Field(default="SUB_ADMINISTRATOR")
    privileges: list[str] = Field(default_factory=list)


ROLE_DEFAULT_PRIVILEGES: dict[str, list[str]] = {
    "ADMINISTRATOR": ["manage_users", "review_flagged_transactions", "adjust_balances", "view_audit_logs", "export_reports", "manage_staff"],
    "SUB_ADMINISTRATOR": ["manage_users", "review_flagged_transactions", "view_audit_logs", "export_reports"],
    "FRAUD_ANALYST": ["review_flagged_transactions", "view_audit_logs", "export_reports"],
    "SENIOR_INVESTIGATOR": ["manage_users", "review_flagged_transactions", "view_audit_logs", "export_reports"],
    "AUDITOR": ["view_audit_logs", "export_reports"],
}


@router.get("/staff")
async def list_staff_users(
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> list[dict[str, Any]]:
    """List all administrative, sub-admin, and compliance staff users with assigned privileges."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        stmt = (
            select(User)
            .where(User.role != "CUSTOMER")
            .order_by(User.id.asc())
        )
        users = (await session.scalars(stmt)).all()

        staff_list = []
        for u in users:
            privileges = ROLE_DEFAULT_PRIVILEGES.get(u.role, ["view_audit_logs"])
            is_super_admin = (u.username == "admin" or u.email == "admin@omerta.ai" or u.id == 1)
            staff_list.append({
                "id": u.external_id,
                "user_id": u.id,
                "full_name": u.full_name,
                "email": u.email,
                "username": u.username,
                "role": u.role,
                "is_active": u.is_active,
                "is_super_admin": is_super_admin,
                "can_delete": not is_super_admin,
                "privileges": privileges,
                "created_at": u.created_at.isoformat() if u.created_at else None,
            })
        return staff_list


@router.post("/staff", status_code=status.HTTP_201_CREATED)
async def create_staff_user(
    body: CreateStaffRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR"])),
) -> dict[str, Any]:
    """Create a new administrator, investigator, fraud analyst, or compliance auditor (customers prohibited)."""
    from infrastructure.security.jwt_auth import hash_password
    import secrets

    clean_email = body.email.strip().lower()
    clean_username = body.username.strip().lower()
    target_role = body.role.upper().strip()

    ALLOWED_STAFF_ROLES = [
        "ADMINISTRATOR",
        "SUB_ADMINISTRATOR",
        "FRAUD_ANALYST",
        "SENIOR_INVESTIGATOR",
        "INVESTIGATOR",
        "AUDITOR",
        "COMPLIANCE_AUDITOR",
    ]

    # Explicitly prohibit creating CUSTOMER accounts from admin staff provisioning
    if target_role == "CUSTOMER" or target_role not in ALLOWED_STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_STAFF_ROLE",
                "message": "Staff management portal cannot create Customer accounts. Customers must be onboarded through the customer registration flow.",
            },
        )

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Check collision
        existing = await session.scalar(
            select(User).where((User.email == clean_email) | (User.username == clean_username)).limit(1)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "USER_EXISTS", "message": "A staff user with this email or username already exists."},
            )

        new_user = User(
            external_id=f"USR-{secrets.token_hex(4).upper()}",
            username=clean_username,
            email=clean_email,
            hashed_password=hash_password(body.password),
            full_name=body.full_name.strip(),
            role=target_role,
            is_active=True,
        )
        session.add(new_user)
        await session.flush()

        assigned_privileges = body.privileges if body.privileges else ROLE_DEFAULT_PRIVILEGES.get(target_role, ["view_audit_logs"])

        # Audit event
        audit_event = AuditEvent(
            event_id=f"EVT-STAFF-{new_user.id}",
            event_type="STAFF_ACCOUNT_CREATED",
            actor_type="ADMINISTRATOR",
            actor_id=str(current_user.get("sub", "ADMIN")),
            source="AdminService",
            metadata_={
                "created_staff_id": new_user.external_id,
                "full_name": new_user.full_name,
                "role": new_user.role,
                "privileges": assigned_privileges,
                "creator_admin": current_user.get("username"),
            },
        )
        session.add(audit_event)
        await session.commit()

        return {
            "id": new_user.external_id,
            "full_name": new_user.full_name,
            "email": new_user.email,
            "username": new_user.username,
            "role": new_user.role,
            "is_active": new_user.is_active,
            "privileges": assigned_privileges,
            "message": f"Successfully created {new_user.role} account for {new_user.full_name}.",
        }


@router.delete("/staff/{user_id}")
async def delete_staff_user(
    user_id: str,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR"])),
) -> dict[str, Any]:
    """Delete or revoke a staff/admin account with permanent protection for the Root Super Administrator."""
    from infrastructure.database.models import Session as UserSession
    import secrets

    clean_id = user_id.strip()
    is_target_super_admin_alias = clean_id.lower() in ("admin", "admin@omerta.ai", "dr. sarah al-rashid")

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        target_filters = [
            User.external_id == clean_id,
            User.username == clean_id.lower(),
            User.email == clean_id.lower(),
        ]
        if clean_id.isdigit():
            target_filters.append(User.id == int(clean_id))
        if is_target_super_admin_alias:
            target_filters.extend([
                User.username == "admin",
                User.username == "admin@omerta.ai",
                User.email == "admin@omerta.ai",
                User.id == 1,
            ])

        target = await session.scalar(select(User).where(or_(*target_filters)).limit(1))
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff user not found.")

        # 1. Super Admin Permanent Protection
        is_super_admin = (
            target.username in ("admin", "admin@omerta.ai")
            or target.email == "admin@omerta.ai"
            or target.id == 1
            or is_target_super_admin_alias
        )
        if is_super_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "SUPER_ADMIN_PROTECTED",
                    "message": "Super Administrator 'admin' is permanently protected and cannot be deleted, suspended, or revoked by any other administrator.",
                },
            )

        # 2. Self-deletion prevention
        if target.external_id == current_user.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "SELF_DELETION_PROHIBITED",
                    "message": "Administrators cannot delete their own active account session.",
                },
            )

        # Invalidate active sessions
        active_sessions = (
            await session.scalars(
                select(UserSession).where(UserSession.user_id == target.id, UserSession.is_active == True)
            )
        ).all()
        for sess in active_sessions:
            sess.is_active = False

        target.is_active = False
        staff_name = target.full_name
        staff_role = target.role

        # Audit event
        session.add(
            AuditEvent(
                event_id=f"EVT-STAFF-DEL-{secrets.token_hex(4).upper()}",
                event_type="STAFF_ACCOUNT_REVOKED",
                actor_type="ADMINISTRATOR",
                actor_id=str(current_user.get("sub", "ADMIN")),
                source="AdminStaffManagement",
                metadata_={
                    "revoked_staff_id": target.external_id,
                    "staff_name": staff_name,
                    "role": staff_role,
                    "deleted_by": current_user.get("username"),
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "id": target.external_id,
            "full_name": staff_name,
            "message": f"Staff account for {staff_name} ({staff_role}) has been successfully revoked and deactivated.",
        }


# ============================================================================
# PROBLEM CUSTOMER & RISK QUEUE MANAGEMENT
# ============================================================================

class CustomerRiskResolutionRequest(BaseModel):
    reason: str = Field(default="Identity verified via phone/email verification. Account risk cleared.", min_length=3)
    reset_risk_to: str = Field(default="LOW", description="LOW | MODERATE")


class CustomerNotifyRequest(BaseModel):
    channel: str = Field(default="EMAIL", description="EMAIL | SMS | PHONE_CALL")
    subject: str = Field(default="Omerta.ai Account Security Notice")
    message: str = Field(..., min_length=5)


@router.get("/problem-customers")
async def list_problem_customers(
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> list[dict[str, Any]]:
    """List high-risk, locked, or flagged customers requiring administrative review and direct communication."""
    from apps.api.v1.customer import FAILED_TRANSFER_ATTEMPTS

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        stmt = (
            select(Customer)
            .options(selectinload(Customer.user), selectinload(Customer.accounts))
            .join(User, Customer.user_id == User.id, isouter=True)
            .where(
                (Customer.risk_level.in_(["HIGH", "CRITICAL"]))
                | (Customer.status.in_(["SUSPENDED", "LOCKED"]))
                | (User.is_active.is_(False))
                | (Customer.transfer_status == "BLOCKED")
                | (Customer.transfer_failed_attempts >= 3)
                | (Customer.identity_status.in_(["PENDING_REVIEW", "PENDING", "REJECTED"]))
            )
            .order_by(Customer.updated_at.desc())
        )
        customers = (await session.scalars(stmt)).all()

        results = []
        for c in customers:
            user = c.user
            failed_attempts = FAILED_TRANSFER_ATTEMPTS.get(user.id, 0) if user else 0
            if getattr(c, "transfer_failed_attempts", 0) > failed_attempts:
                failed_attempts = c.transfer_failed_attempts

            # Find latest support ticket if any
            ticket_stmt = (
                select(SupportTicket)
                .options(selectinload(SupportTicket.identity_verifications))
                .where(SupportTicket.customer_id == c.id)
                .order_by(SupportTicket.updated_at.desc())
                .limit(1)
            )
            latest_ticket = await session.scalar(ticket_stmt)

            # Find recent security audit events
            recent_evts_stmt = (
                select(AuditEvent)
                .where(
                    (AuditEvent.actor_id == str(c.user_id))
                    | (AuditEvent.metadata_["customer_id"].astext == c.external_id)
                )
                .order_by(AuditEvent.created_at.desc())
                .limit(5)
            )
            evts = (await session.scalars(recent_evts_stmt)).all()

            evt_list = [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "source": e.source,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "metadata": e.metadata_,
                }
                for e in evts
            ]

            total_balance = sum(
                float(acc.balance)
                for acc in (c.accounts or [])
            )

            is_transfer_blocked = (c.transfer_status == "BLOCKED") or (failed_attempts >= 3)

            # Determine lock/flag primary reason based on real security telemetry
            if is_transfer_blocked:
                primary_reason = "Transfer Password Blocked (3 Failed Attempts) — Requires Identity Verification"
            elif c.identity_status == "PENDING_REVIEW":
                primary_reason = "National ID Document Uploaded — Pending Compliance Review"
            elif failed_attempts >= 3 or (user and not user.is_active and any(e.event_type == "EXCESSIVE_PASSWORD_FAILURES" for e in evts)):
                primary_reason = "Locked: 3 Failed Password Attempts (Account Inactivated)"
            elif any(e.event_type == "IMPOSSIBLE_TRAVEL_VELOCITY" for e in evts):
                primary_reason = "Flagged: Impossible Travel Velocity Anomaly"
            elif any(e.event_type == "VPN_TRANSFER_BLOCKED" for e in evts):
                primary_reason = "Flagged: Outbound Transfer Blocked on VPN/Proxy Tunnel"
            elif any(e.event_type == "EXCESSIVE_PASSWORD_FAILURES" for e in evts):
                primary_reason = "Locked: Excessive Password Failures"
            elif c.status in ("SUSPENDED", "LOCKED") or (user and not user.is_active):
                primary_reason = "Account Inactivated & Suspended"
            elif c.risk_level == "CRITICAL":
                primary_reason = "Critical Risk Anomaly Flagged"
            else:
                primary_reason = "Elevated Risk Rating"

            has_uploaded_id = False
            if latest_ticket and latest_ticket.identity_verifications:
                has_uploaded_id = any(bool(v.document_front_url) for v in latest_ticket.identity_verifications)

            results.append({
                "customer_id": c.external_id,
                "user_id": user.external_id if user else None,
                "name": c.name,
                "omerta_user_number": c.omerta_user_number,
                "email": c.email or (user.email if user else "customer@omerta.ai"),
                "phone": c.phone or "+20 10 1111 2222",
                "country": c.declared_country or "EG",
                "risk_level": c.risk_level,
                "status": c.status,
                "primary_reason": primary_reason,
                "customer_issue": latest_ticket.subject if latest_ticket else primary_reason,
                "transfer_status": getattr(c, "transfer_status", "ACTIVE"),
                "transfer_blocked": is_transfer_blocked,
                "failed_password_attempts": failed_attempts,
                "identity_status": getattr(c, "identity_status", "NOT_VERIFIED"),
                "national_id_number": getattr(c, "national_id_number", None),
                "ticket_number": latest_ticket.external_id if latest_ticket else None,
                "ticket_id": latest_ticket.id if latest_ticket else None,
                "ticket_subject": latest_ticket.subject if latest_ticket else None,
                "ticket_issue_type": latest_ticket.issue_type if latest_ticket else None,
                "ticket_status": latest_ticket.status if latest_ticket else None,
                "has_uploaded_id": has_uploaded_id,
                "is_user_active": user.is_active if user else False,
                "total_balance_egp": total_balance,
                "recent_audit_events": evt_list,
                "actions_available": ["SUPPORT_CHAT", "CALL_CUSTOMER", "SEND_EMAIL", "RESOLVE_RISK", "AGENTIC_REPORT", "VIEW_PROFILE"],
            })

        return results


@router.post("/problem-customers/{customer_id}/resolve-risk")
async def resolve_customer_risk(
    customer_id: str,
    body: CustomerRiskResolutionRequest,
    current_user: dict[str, Any] = Depends(require_role(["ADMINISTRATOR", "FRAUD_ANALYST", "SENIOR_INVESTIGATOR"])),
) -> dict[str, Any]:
    """Manually resolve customer risk, reset password failure counter, and restore active banking privileges."""
    from apps.api.v1.customer import FAILED_TRANSFER_ATTEMPTS
    import secrets

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust = await session.scalar(
            select(Customer)
            .options(selectinload(Customer.user))
            .where((Customer.external_id == customer_id) | (Customer.omerta_user_number == customer_id))
        )
        if not cust:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

        old_risk = cust.risk_level
        old_status = cust.status

        # Reset customer and user status
        cust.risk_level = body.reset_risk_to.upper()
        cust.status = "ACTIVE"
        if cust.user:
            cust.user.is_active = True
            FAILED_TRANSFER_ATTEMPTS[cust.user.id] = 0

        # Create formal AuditEvent
        session.add(
            AuditEvent(
                event_id=f"EVT-RESOLVE-{secrets.token_hex(4).upper()}",
                event_type="CUSTOMER_RISK_MANUALLY_RESOLVED",
                actor_type="ADMINISTRATOR" if current_user.get("role") == "ADMINISTRATOR" else "FRAUD_ANALYST",
                actor_id=str(current_user.get("sub")),
                source="AdminProblemCustomerCenter",
                metadata_={
                    "customer_id": cust.external_id,
                    "customer_name": cust.name,
                    "omerta_user_number": cust.omerta_user_number,
                    "old_risk_level": old_risk,
                    "new_risk_level": cust.risk_level,
                    "old_status": old_status,
                    "new_status": cust.status,
                    "resolution_reason": body.reason,
                    "resolver_user": current_user.get("username"),
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "customer_id": cust.external_id,
            "name": cust.name,
            "risk_level": cust.risk_level,
            "status": cust.status,
            "message": f"Customer risk successfully resolved. Account has been restored to {cust.risk_level} risk and re-activated.",
        }


@router.post("/problem-customers/{customer_id}/notify")
async def notify_customer(
    customer_id: str,
    body: CustomerNotifyRequest,
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Send security notification or direct communication (Email/SMS) to problem customer."""
    import secrets

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust = await session.scalar(
            select(Customer)
            .options(selectinload(Customer.user))
            .where((Customer.external_id == customer_id) | (Customer.omerta_user_number == customer_id))
        )
        if not cust:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

        recipient_contact = cust.user.email if body.channel == "EMAIL" and cust.user else (cust.phone or "+20 10 1111 2222")

        # Dispatch real email if channel is EMAIL
        delivery_res = None
        if body.channel.upper() == "EMAIL" and recipient_contact and "@" in recipient_contact:
            delivery_res = await EmailService.send_security_notice_email(
                to_email=recipient_contact,
                customer_name=cust.name,
                subject=body.subject,
                message=body.message,
            )

        # Record notification in audit log
        session.add(
            AuditEvent(
                event_id=f"EVT-NOTIFY-{secrets.token_hex(4).upper()}",
                event_type="CUSTOMER_SECURITY_NOTICE_DISPATCHED",
                actor_type="ADMIN_STAFF",
                actor_id=str(current_user.get("sub")),
                source="AdminCommunicationHub",
                metadata_={
                    "customer_id": cust.external_id,
                    "customer_name": cust.name,
                    "channel": body.channel,
                    "sender": "abdomostafa13571234@gmail.com",
                    "recipient": recipient_contact,
                    "subject": body.subject,
                    "message_preview": body.message[:100],
                    "delivery_status": delivery_res.to_dict() if delivery_res else None,
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "customer_id": cust.external_id,
            "recipient": recipient_contact,
            "sender": "abdomostafa13571234@gmail.com",
            "channel": body.channel,
            "message": f"Security communication dispatched from abdomostafa13571234@gmail.com to {cust.name} ({recipient_contact}).",
        }


@router.get("/problem-customers/{customer_id}/agentic-summary")
async def get_problem_customer_agentic_summary(
    customer_id: str,
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Autonomous Agentic Forensic Summary for high-risk problem customer investigation."""
    from apps.api.v1.customer import FAILED_TRANSFER_ATTEMPTS

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        cust = await session.scalar(
            select(Customer)
            .options(selectinload(Customer.user), selectinload(Customer.accounts))
            .where((Customer.external_id == customer_id) | (Customer.omerta_user_number == customer_id))
        )
        if not cust:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")

        user = cust.user
        failed_attempts = FAILED_TRANSFER_ATTEMPTS.get(user.id, 0) if user else 0

        recent_evts_stmt = (
            select(AuditEvent)
            .where(
                (AuditEvent.actor_id == str(cust.user_id))
                | (AuditEvent.metadata_["customer_id"].astext == cust.external_id)
            )
            .order_by(AuditEvent.created_at.desc())
            .limit(10)
        )
        evts = (await session.scalars(recent_evts_stmt)).all()

        total_balance = sum(float(acc.balance) for acc in (cust.accounts or []))

        # Synthesize Multi-Agent Forensic Findings
        findings = []
        if failed_attempts >= 3 or any(e.event_type == "EXCESSIVE_PASSWORD_FAILURES" for e in evts):
            findings.append({
                "category": "AUTHENTICATION_INTEGRITY",
                "severity": "CRITICAL",
                "finding": "3 consecutive incorrect password attempts detected during transfer confirmation.",
                "action_required": "Direct Phone Identity Verification or Out-of-Band Password Reset.",
            })
        if any(e.event_type == "IMPOSSIBLE_TRAVEL_VELOCITY" for e in evts):
            findings.append({
                "category": "GEOGRAPHIC_VELOCITY",
                "severity": "CRITICAL",
                "finding": "Impossible travel speed / rapid domestic city jump observed within minutes.",
                "action_required": "Verify current physical location and device ownership.",
            })
        if any(e.event_type == "VPN_TRANSFER_BLOCKED" for e in evts):
            findings.append({
                "category": "NETWORK_TELEMETRY",
                "severity": "HIGH",
                "finding": "Outbound transfer initiated via commercial VPN / proxy anonymization tunnel.",
                "action_required": "Instruct customer to disable VPN before executing transfers.",
            })
        if not findings:
            findings.append({
                "category": "BEHAVIORAL_ANOMALY",
                "severity": "MEDIUM",
                "finding": f"Customer risk elevated to {cust.risk_level} based on transaction patterns.",
                "action_required": "Routine compliance review.",
            })

        return {
            "customer_id": cust.external_id,
            "omerta_user_number": cust.omerta_user_number,
            "name": cust.name,
            "email": cust.email or (user.email if user else "customer@omerta.ai"),
            "phone": cust.phone or "+20 10 1111 2222",
            "risk_level": cust.risk_level,
            "status": cust.status,
            "is_user_active": user.is_active if user else False,
            "failed_password_attempts": failed_attempts,
            "total_balance_egp": total_balance,
            "forensic_findings": findings,
            "agentic_agents": [
                {"agent": "IdentityVerificationAgent", "verdict": "FLAGGED" if (failed_attempts >= 3 or not user.is_active) else "VERIFIED"},
                {"agent": "NetworkTelemetryAgent", "verdict": "VPN_RESTRICTED" if any(e.event_type == "VPN_TRANSFER_BLOCKED" for e in evts) else "DIRECT_IP"},
                {"agent": "GeographicVelocityAgent", "verdict": "ANOMALOUS_VELOCITY" if any(e.event_type == "IMPOSSIBLE_TRAVEL_VELOCITY" for e in evts) else "NORMAL_DOMESTIC"},
                {"agent": "ComplianceResolutionAgent", "verdict": "ACTION_REQUIRED" if cust.status == "SUSPENDED" else "MONITORING"},
            ],
            "recommended_resolution": "Call customer on verified phone number, confirm identity, then use 'Resolve & Unlock' to reactivate banking.",
        }


# ============================================================================
# MASTER FRAUD WORKFLOW ADMIN ENDPOINTS
# ============================================================================

class AdminApproveRejectRequest(BaseModel):
    reason: str | None = None
    rationale: str | None = None

    @property
    def final_reason(self) -> str:
        return self.rationale or self.reason or "Compliance review completed and approved."


class AdminPrivilegeRestorationRequest(BaseModel):
    reason: str = Field(default="Customer account recovery completed and identity verified.", min_length=5)
    ticket_id: int | None = None




@router.post("/customers/{customer_id}/restore-transaction-privileges")
async def admin_restore_transaction_privileges(
    customer_id: str,
    body: AdminPrivilegeRestorationRequest = AdminPrivilegeRestorationRequest(),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Release server-enforced transaction restrictions and restore transfer privileges."""
    from domain.services.transfer_service import TransferService, TransferError

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Resolve customer by external_id or integer PK
        cust = await session.scalar(
            select(Customer).where(
                (Customer.external_id == customer_id)
                | (Customer.omerta_user_number == customer_id)
                | (Customer.id == (int(customer_id) if customer_id.isdigit() else -1))
            ).limit(1)
        )
        if not cust:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Customer {customer_id} not found"})

        transfer_svc = TransferService(session)
        admin_sub = str(current_user.get("sub", ""))
        admin_user_id = int(admin_sub) if admin_sub.isdigit() else 1
        try:
            return await transfer_svc.restore_customer_transfer_privileges(
                customer_id=cust.id,
                admin_user_id=admin_user_id,
                reason=body.reason,
                ticket_id=body.ticket_id,
            )
        except TransferError as terr:
            raise HTTPException(status_code=terr.status_code, detail={"error": terr.code, "message": terr.message})


@router.get("/security-tickets")
async def list_admin_security_tickets(
    status_filter: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """List security and account takeover incident tickets for compliance triage."""
    from infrastructure.database.models import SupportTicket

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        stmt = select(SupportTicket).options(selectinload(SupportTicket.customer)).order_by(SupportTicket.created_at.desc())
        if status_filter:
            stmt = stmt.where(SupportTicket.status == status_filter.upper())
        if priority:
            stmt = stmt.where(SupportTicket.priority == priority.upper())

        tickets = (await session.scalars(stmt)).all()
        return {
            "total": len(tickets),
            "tickets": [
                {
                    "id": t.id,
                    "external_id": t.external_id,
                    "ticket_type": t.ticket_type,
                    "priority": t.priority,
                    "status": t.status,
                    "subject": t.subject,
                    "customer_name": t.customer.name if t.customer else "Unknown",
                    "customer_number": t.customer.omerta_user_number if t.customer else "N/A",
                    "related_transaction_id": t.related_transaction_id,
                    "created_at": t.created_at.isoformat(),
                    "resolution_reason": t.resolution_reason,
                }
                for t in tickets
            ],
        }


@router.post("/security-tickets/{ticket_id}/resolve")
async def admin_resolve_security_ticket(
    ticket_id: str,
    body: AdminPrivilegeRestorationRequest = AdminPrivilegeRestorationRequest(),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Resolve an open security ticket."""
    from infrastructure.database.models import SupportTicket
    from datetime import UTC, datetime

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        ticket = await session.scalar(
            select(SupportTicket).where(
                (SupportTicket.external_id == ticket_id)
                | (SupportTicket.id == (int(ticket_id) if ticket_id.isdigit() else -1))
            ).limit(1)
        )
        if not ticket:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Security ticket {ticket_id} not found"})

        admin_sub = str(current_user.get("sub", ""))
        admin_user_id = int(admin_sub) if admin_sub.isdigit() else 1
        ticket.status = "RESOLVED"
        ticket.resolved_at = datetime.now(UTC)
        ticket.resolution_reason = body.reason
        ticket.assigned_user_id = admin_user_id

        await session.commit()
        return {"success": True, "ticket_id": ticket.external_id, "status": "RESOLVED"}


# ============================================================================
# AGENTIC AI WORKFLOW & SAR GENERATOR (COMING SOON PREVIEW)
# ============================================================================

@router.post("/agentic/generate-sar-report")
async def preview_agentic_sar_report(
    case_or_txn_id: str = Query(..., description="Target Case or Transaction External ID"),
    current_user: dict[str, Any] = Depends(require_role(ADMIN_ROLES)),
) -> dict[str, Any]:
    """Agentic AI SAR Workflow Generator — Preview of Autonomous Multi-Agent AML Pipeline."""
    return {
        "status": "COMING_SOON",
        "feature": "Agentic AI SAR Autonomous Report Drafter",
        "target_id": case_or_txn_id,
        "agents": [
            {"agent": "TopologyInspectorAgent", "role": "Analyzes Neo4j cyclic money flows and entity rings", "status": "Ready in Phase 3"},
            {"agent": "AnomalyClassifierAgent", "role": "Evaluates velocity spikes, VPN hops, and Mule patterns", "status": "Ready in Phase 3"},
            {"agent": "FinCEN_NarrativeAgent", "role": "Drafts formal SAR narrative complying with FinCEN guidelines", "status": "Ready in Phase 3"},
            {"agent": "RegTechComplianceAgent", "role": "Cross-references Central Bank regulations and typologies", "status": "Ready in Phase 3"},
        ],
        "preview_narrative": (
            "AUTOMATED DRAFT (COMING SOON): Multiple high-velocity transfers were initiated following rapid IP geolocation shifts. "
            "Graph topology revealed closed 3-hop cyclic fund disbursement matching structuring (smurfing) typologies."
        ),
        "message": "✨ Agentic AI SAR Report Generation will be fully autonomous in the upcoming phase.",
    }


