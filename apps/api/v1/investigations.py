"""Investigation & Forensic Workbench Router for Omerta.ai.

Exposes endpoints for:
- Account forensic investigations (LangGraph multi-source pipeline)
- Transaction forensic investigations (LangGraph with pipeline tracing & preceding/subsequent context)
- Transaction investigation retrieval & verification
- Sandbox withdrawal simulation (isolated, atomic, concurrency-locked)
- Sandbox fixtures and safe sandbox reset
"""

from datetime import UTC, datetime
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from domain.investigation.schemas import (
    AccountInvestigationReport,
    AccountInvestigationRequest,
    SimulatedWithdrawalRequest,
    SimulatedWithdrawalResponse,
    TransactionInvestigationRequest,
)
from domain.errors import ValidationError
from domain.investigation.simulation import get_sandbox_withdrawal_service
from infrastructure.database.models import (
    InvestigationCase,
    Transaction,
    Account,
    Customer,
    User,
    AuditEvent,
)
from infrastructure.database.session import get_engine
from infrastructure.security.jwt_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/investigations", tags=["Forensic Investigations"])


@router.post(
    "/account",
    response_model=AccountInvestigationReport,
    summary="Run Account Forensic Investigation (LangGraph)",
    description="Executes the full multi-tier LangGraph forensic investigation across PostgreSQL, Neo4j, LightGBM, and banking rules.",
)
async def investigate_account_endpoint(
    body: AccountInvestigationRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AccountInvestigationReport:
    """Execute LangGraph account investigation workflow."""
    from apps.investigator.account_workflow import run_account_investigation

    role = current_user.get("role", "INVESTIGATOR")
    user_id = current_user.get("id") or current_user.get("sub")
    return await run_account_investigation(
        body,
        caller_role=role,
        caller_id=str(user_id) if user_id else None,
    )


@router.post(
    "/transaction",
    response_model=AccountInvestigationReport,
    summary="Run Transaction Forensic Investigation (LangGraph)",
    description="Executes a transaction-grounded LangGraph investigation workflow with 9 real execution stages and temporal preceding/subsequent context.",
)
async def investigate_transaction_endpoint(
    body: TransactionInvestigationRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> AccountInvestigationReport:
    """Execute LangGraph transaction investigation workflow."""
    from apps.investigator.account_workflow import get_active_run_for_txn, run_transaction_investigation

    # Check for active running investigation to prevent accidental duplicate runs
    existing_tracker = get_active_run_for_txn(body.transaction_id)
    if existing_tracker and existing_tracker.status == "RUNNING":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An investigation is already running for transaction '{body.transaction_id}'. Investigation ID: {existing_tracker.investigation_id}.",
        )

    role = current_user.get("role", "INVESTIGATOR")
    user_id = current_user.get("id") or current_user.get("sub")
    return await run_transaction_investigation(
        body,
        caller_role=role,
        caller_id=str(user_id) if user_id else None,
    )


@router.get(
    "/transaction/{transaction_id}/live",
    summary="Get Live Investigation Execution State & Stage Timings",
    description="Retrieve live monotonic stage timings, running specialist nodes, and execution snapshot for a transaction.",
)
async def get_transaction_investigation_live_endpoint(
    transaction_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve live execution snapshot with monotonic elapsed timings or persisted result."""
    from apps.investigator.account_workflow import get_active_run, get_active_run_for_txn

    # 1. Check in-memory active run tracker
    tracker = get_active_run_for_txn(transaction_id) or get_active_run(transaction_id)
    if tracker:
        return tracker.get_snapshot()

    # 2. Check if transaction exists and has a persisted InvestigationCase
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        txn = await session.scalar(
            select(Transaction).where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id == int(transaction_id) if transaction_id.isdigit() else False,
                )
            )
        )
        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction '{transaction_id}' not found.",
            )

        case = await session.scalar(
            select(InvestigationCase).where(
                or_(
                    InvestigationCase.transaction_id == txn.id,
                    InvestigationCase.external_id == f"INV-TXN-{txn.external_id}",
                )
            ).order_by(desc(InvestigationCase.id))
        )

        if case and case.report:
            stages = case.report.get("pipeline_stages", [])
            return {
                "investigation_id": case.external_id,
                "subject_id": txn.external_id,
                "is_transaction": True,
                "status": "COMPLETED",
                "started_at": case.created_at.isoformat() if case.created_at else None,
                "completed_at": case.updated_at.isoformat() if case.updated_at else None,
                "elapsed_ms": sum(float(s.get("duration_ms", 0)) for s in stages),
                "progress_percentage": 100.0,
                "active_stage_ids": [],
                "completed_count": len(stages),
                "total_stages": len(stages) or 9,
                "stages": stages,
                "final_report": case.report,
                "error_message": None,
            }

    # 3. Not started yet
    return {
        "investigation_id": f"INV-TXN-{transaction_id}",
        "subject_id": transaction_id,
        "is_transaction": True,
        "status": "NOT_STARTED",
        "started_at": None,
        "completed_at": None,
        "elapsed_ms": 0.0,
        "progress_percentage": 0.0,
        "active_stage_ids": [],
        "completed_count": 0,
        "total_stages": 9,
        "stages": [],
        "final_report": None,
        "error_message": None,
    }


@router.get(
    "/transaction/{transaction_id}",
    summary="Get Existing Transaction Investigation Report",
    description="Retrieve the persisted forensic investigation report and execution pipeline trace for a specific transaction.",
)
async def get_transaction_investigation_endpoint(
    transaction_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Retrieve persisted report for a transaction or return 404."""
    from apps.investigator.account_workflow import get_active_run_for_txn

    # If actively running, return current live snapshot
    tracker = get_active_run_for_txn(transaction_id)
    if tracker and tracker.status == "RUNNING":
        return tracker.get_snapshot()

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # 1. Check if transaction exists
        txn = await session.scalar(
            select(Transaction).where(
                or_(
                    Transaction.external_id == transaction_id,
                    Transaction.id == int(transaction_id) if transaction_id.isdigit() else False,
                )
            )
        )
        if not txn:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Transaction '{transaction_id}' not found.",
            )

        # 2. Check for persisted InvestigationCase
        case = await session.scalar(
            select(InvestigationCase).where(
                or_(
                    InvestigationCase.transaction_id == txn.id,
                    InvestigationCase.external_id == f"INV-TXN-{txn.external_id}",
                )
            ).order_by(desc(InvestigationCase.id))
        )

        if not case or not case.report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No forensic investigation report currently persisted for transaction '{transaction_id}'.",
            )

        return case.report


@router.post(
    "/simulate-withdrawal",
    response_model=SimulatedWithdrawalResponse,
    summary="Simulate Sandbox Withdrawal Operation",
    description="Simulates an atomic withdrawal on synthetic test accounts to evaluate concurrency, idempotency, and velocity monitoring controls.",
)
async def simulate_withdrawal_endpoint(
    body: SimulatedWithdrawalRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> SimulatedWithdrawalResponse:
    """Execute sandbox simulated withdrawal."""
    service = get_sandbox_withdrawal_service()
    role = current_user.get("role", "INVESTIGATOR")
    try:
        return await service.execute_simulated_withdrawal(body, caller_role=role)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "SIMULATION_VALIDATION_ERROR", "message": str(exc)},
        )


@router.get(
    "/sandbox-fixtures",
    summary="Get Authorized Sandbox Fixtures",
    description="Returns authorized synthetic accounts available for simulation and their current simulated balances.",
)
async def get_sandbox_fixtures_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List available sandbox fixture accounts."""
    service = get_sandbox_withdrawal_service()
    return service.get_fixture_accounts()


@router.post(
    "/reset-sandbox",
    summary="Safely Reset Sandbox Test Data",
    description="Resets all synthetic test balances, purges synthetic test transactions, and clears idempotency caches without touching production data.",
)
async def reset_sandbox_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Safely reset sandbox environment."""
    service = get_sandbox_withdrawal_service()
    return await service.reset_sandbox()


@router.post(
    "/accounts/{account_id}/unblock",
    summary="Human-in-the-Loop Unblock Account",
    description="Authorized compliance action to unblock an account and restore user login and transaction privileges.",
)
async def unblock_account_endpoint(
    account_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Restore account and user status to ACTIVE."""
    role = current_user.get("role", "INVESTIGATOR")
    authorized = role in [
        "ADMINISTRATOR",
        "ADMIN",
        "INVESTIGATOR",
        "SENIOR_INVESTIGATOR",
        "FRAUD_ANALYST",
        "COMPLIANCE_OFFICER",
    ]
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized. Only compliance investigators or administrators can unblock accounts.",
        )

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        acc = await session.scalar(
            select(Account)
            .options(selectinload(Account.customer).selectinload(Customer.user))
            .where(
                or_(
                    Account.external_id == account_id,
                    Account.id == int(account_id) if account_id.isdigit() else False,
                )
            )
        )
        if not acc:
            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

        acc.status = "ACTIVE"
        cust_name = acc.customer_name
        if acc.customer:
            acc.customer.status = "ACTIVE"
            acc.customer.transfer_status = "ACTIVE"
            acc.customer.transfer_failed_attempts = 0
            acc.customer.transfer_unblocked_at = datetime.now(UTC)
            cust_name = acc.customer.name
            if acc.customer.user:
                acc.customer.user.is_active = True

        session.add(
            AuditEvent(
                event_id=f"EVT-UNBLOCK-{acc.external_id}-{int(datetime.now(UTC).timestamp())}",
                event_type="ACCOUNT_UNBLOCKED_BY_INVESTIGATOR",
                actor_type=role,
                actor_id=str(current_user.get("sub", "ANALYST")),
                source="InvestigationWorkbench",
                metadata_={
                    "account_id": acc.external_id,
                    "customer_name": cust_name,
                    "action": "RESTORE_ACCESS",
                    "status": "ACTIVE",
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "message": f"Account {acc.external_id} ({cust_name}) successfully unblocked. User login and transfer privileges restored.",
            "account_id": acc.external_id,
            "account_status": "ACTIVE",
            "customer_status": "ACTIVE",
        }


@router.post(
    "/accounts/{account_id}/block",
    summary="Human-in-the-Loop Block Account",
    description="Authorized compliance action to place an account under containment hold, suspending transactions and login.",
)
async def block_account_endpoint(
    account_id: str,
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Place account and user status under security hold (BLOCKED)."""
    role = current_user.get("role", "INVESTIGATOR")
    authorized = role in [
        "ADMINISTRATOR",
        "ADMIN",
        "INVESTIGATOR",
        "SENIOR_INVESTIGATOR",
        "FRAUD_ANALYST",
        "COMPLIANCE_OFFICER",
    ]
    if not authorized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Unauthorized. Only compliance investigators or administrators can block accounts.",
        )

    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        acc = await session.scalar(
            select(Account)
            .options(selectinload(Account.customer).selectinload(Customer.user))
            .where(
                or_(
                    Account.external_id == account_id,
                    Account.id == int(account_id) if account_id.isdigit() else False,
                )
            )
        )
        if not acc:
            raise HTTPException(status_code=404, detail=f"Account '{account_id}' not found.")

        acc.status = "BLOCKED"
        cust_name = acc.customer_name
        if acc.customer:
            acc.customer.status = "BLOCKED"
            acc.customer.transfer_status = "BLOCKED"
            acc.customer.transfer_blocked_at = datetime.now(UTC)
            cust_name = acc.customer.name
            if acc.customer.user:
                acc.customer.user.is_active = False

        session.add(
            AuditEvent(
                event_id=f"EVT-BLOCK-{acc.external_id}-{int(datetime.now(UTC).timestamp())}",
                event_type="ACCOUNT_BLOCKED_BY_INVESTIGATOR",
                actor_type=role,
                actor_id=str(current_user.get("sub", "ANALYST")),
                source="InvestigationWorkbench",
                metadata_={
                    "account_id": acc.external_id,
                    "customer_name": cust_name,
                    "action": "CONTAINMENT_BLOCK",
                    "status": "BLOCKED",
                },
            )
        )
        await session.commit()

        return {
            "success": True,
            "message": f"Account {acc.external_id} ({cust_name}) placed under compliance containment hold.",
            "account_id": acc.external_id,
            "account_status": "BLOCKED",
            "customer_status": "BLOCKED",
        }
