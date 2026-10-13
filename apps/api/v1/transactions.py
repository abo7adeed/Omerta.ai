"""Transaction Management Router for Omerta.ai."""

from datetime import datetime
from decimal import Decimal
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.services.banking_transaction_service import BankingTransactionService
from domain.services.mock_risk_engine import MockRiskAssessmentEngine
from infrastructure.database.models import Account, Device, IPAddress, Transaction
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/transactions", tags=["Transactions"])


class CreateTransactionRequest(BaseModel):
    source_account_id: str
    recipient_account_id: str
    amount: float
    currency: str = "EGP"
    transaction_type: str = "TRANSFER"
    device_id: str | None = None
    ip_address: str | None = None
    metadata: dict[str, Any] | None = None


@router.get("")
async def list_transactions(
    search: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    min_amount: float | None = Query(default=None),
    max_amount: float | None = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_desc: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
) -> dict[str, Any]:
    """Search, filter, and paginate transactions with server-side controls."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        return await BankingTransactionService(session).list_transactions(
            search=search,
            currency=currency,
            transaction_type=transaction_type,
            risk_level=risk_level,
            review_status=review_status,
            min_amount=min_amount,
            max_amount=max_amount,
            sort_by=sort_by,
            sort_desc=sort_desc,
            page=page,
            page_size=page_size,
        )


@router.get("/export")
async def export_transactions_csv(
    search: str | None = Query(default=None),
    currency: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
) -> Response:
    """Export filtered transactions to CSV spreadsheet."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        csv_content = await BankingTransactionService(session).export_transactions_csv(
            search=search,
            currency=currency,
            risk_level=risk_level,
            review_status=review_status,
        )
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=omerta_transactions_export.csv"},
    )


@router.get("/{transaction_id}")
async def get_transaction_detail(transaction_id: str) -> dict[str, Any]:
    """Retrieve full 6-section transaction detail view."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        detail = await BankingTransactionService(session).get_transaction_detail(transaction_id)
        if not detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"error": "NOT_FOUND", "message": f"Transaction {transaction_id} does not exist"},
            )
        return detail


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(body: CreateTransactionRequest) -> dict[str, Any]:
    """Ingest a new transaction and trigger immediate risk assessment."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Resolve source account
        s_acc = await session.scalar(
            select(Account).where(
                (Account.external_id == body.source_account_id) | (Account.id == (int(body.source_account_id) if body.source_account_id.isdigit() else -1))
            )
        )
        if not s_acc:
            raise HTTPException(status_code=400, detail={"error": "INVALID_ACCOUNT", "message": "Source account not found"})

        r_acc = await session.scalar(
            select(Account).where(
                (Account.external_id == body.recipient_account_id) | (Account.id == (int(body.recipient_account_id) if body.recipient_account_id.isdigit() else -1))
            )
        )
        if not r_acc:
            raise HTTPException(status_code=400, detail={"error": "INVALID_ACCOUNT", "message": "Recipient account not found"})

        dev = None
        if body.device_id:
            dev = await session.scalar(select(Device).where(Device.external_id == body.device_id))

        ip = None
        if body.ip_address:
            ip = await session.scalar(select(IPAddress).where(IPAddress.address == body.ip_address))

        import uuid
        ext_id = f"TXN-{uuid.uuid4().hex[:8].upper()}"
        txn = Transaction(
            external_id=ext_id,
            account_id=s_acc.id,
            recipient_account_id=r_acc.id,
            amount=Decimal(str(body.amount)),
            currency=body.currency.upper(),
            transaction_type=body.transaction_type.upper(),
            status="COMPLETED",
            timestamp=datetime.now(),
            device_id=dev.id if dev else None,
            ip_address_id=ip.id if ip else None,
            is_new_device=(dev is None or dev.risk_level == "HIGH"),
            is_new_ip=(ip is None or ip.risk_level == "HIGH"),
            txn_metadata=body.metadata or {},
        )
        session.add(txn)
        await session.flush()

        # Run mock risk evaluation
        engine = MockRiskAssessmentEngine(session)
        assessment = await engine.evaluate_transaction(txn.id)
        await session.commit()

        return {
            "transaction_id": txn.external_id,
            "status": txn.status,
            "risk_score": float(assessment.risk_score),
            "risk_level": assessment.risk_level,
            "requires_human_review": assessment.requires_human_review,
        }


class CustomerConfirmationPayload(BaseModel):
    action: str = "CONFIRM"  # CONFIRM | DENY
    token: str | None = None  # Single-use signed action token for email flow


@router.post("/{transaction_id}/customer-confirmation")
async def handle_transaction_customer_confirmation(
    transaction_id: str,
    payload: CustomerConfirmationPayload,
    current_user: dict[str, Any] | None = Depends(get_current_user_optional),
) -> dict[str, Any]:
    """Record customer confirmation (CONFIRM) or fraud denial (DENY) on a held transfer.
    
    Security:
    - If token is supplied: Validates single-use cryptographically signed token.
    - If no token: Enforces authenticated customer session and verifies transaction ownership.
    - Never accepts request solely by supplying transaction ID.
    """
    from domain.services.transfer_service import TransferService, TransferError
    from sqlalchemy.orm import selectinload
    from sqlalchemy import or_
    from infrastructure.database.models import Transfer, Customer

    if not current_user and not payload.token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "UNAUTHORIZED", "message": "Authentication required or valid single-use token must be provided."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn_stmt = (
            select(Transaction)
            .options(selectinload(Transaction.account).selectinload(Account.customer))
            .where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id.in_(
                        select(Transfer.transaction_id).where(Transfer.external_id == transaction_id)
                    ),
                )
            )
            .limit(1)
        )
        txn = await session.scalar(txn_stmt)
        if not txn:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Transaction {transaction_id} not found"})

        sender_cust = txn.account.customer if txn.account else None
        caller_user_id = None

        from domain.services.customer_service import CustomerService

        if current_user:
            cust_svc = CustomerService(session)
            caller_cust = await cust_svc.get_customer_by_user_id(current_user["sub"])
            caller_user_id = caller_cust.user_id if caller_cust else (int(current_user["sub"]) if str(current_user["sub"]).isdigit() else None)

            # Verify ownership if no signed token
            if not payload.token and (not sender_cust or sender_cust.user_id != caller_user_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "FORBIDDEN", "message": "You do not have permission to act on this transaction."},
                )

        transfer_svc = TransferService(session)
        try:
            return await transfer_svc.handle_customer_confirmation(
                transaction_external_id=txn.external_id,
                action=payload.action,
                customer_user_id=caller_user_id,
                token=payload.token,
            )
        except TransferError as terr:
            raise HTTPException(status_code=terr.status_code, detail={"error": terr.code, "message": terr.message})


@router.get("/{transaction_id}/history")
async def get_transaction_history_intel(
    transaction_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve rolling multi-window historical intelligence for the transaction's sender account.
    
    Security: Enforces authentication and IDOR protection (customer can only view own account; analysts allowed).
    """
    from domain.investigation.history_agent import TransactionHistoryAgent
    from domain.services.customer_service import CustomerService
    from sqlalchemy.orm import selectinload
    from infrastructure.database.models import Customer

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn = await session.scalar(
            select(Transaction)
            .options(selectinload(Transaction.account).selectinload(Account.customer))
            .where(Transaction.external_id == transaction_id)
            .limit(1)
        )
        if not txn:
            raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": f"Transaction {transaction_id} not found"})

        user_role = current_user.get("role", "CUSTOMER")
        is_staff = user_role in ["ADMINISTRATOR", "SUB_ADMINISTRATOR", "FRAUD_ANALYST", "INVESTIGATOR", "SENIOR_INVESTIGATOR", "AUDITOR"]

        if not is_staff:
            # Must own the transaction's account
            cust = txn.account.customer if txn.account else None
            cust_svc = CustomerService(session)
            caller_cust = await cust_svc.get_customer_by_user_id(current_user["sub"])
            caller_user_id = caller_cust.user_id if caller_cust else (int(current_user["sub"]) if str(current_user["sub"]).isdigit() else None)

            if not cust or cust.user_id != caller_user_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={"error": "FORBIDDEN", "message": "Access denied: you do not own this transaction's account history."},
                )

        agent = TransactionHistoryAgent(session)
        result = await agent.analyze(
            account_id=txn.account_id,
            current_amount=float(txn.amount),
            current_timestamp=txn.timestamp,
            recipient_account_id=txn.recipient_account_id,
            current_transaction_id=txn.id,
        )
        return result.model_dump()
