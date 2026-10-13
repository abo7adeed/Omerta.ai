import pytest
from decimal import Decimal
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Account, Customer, Transaction, Transfer, User
from infrastructure.database.session import get_engine
from domain.services.transfer_service import TransferService
from apps.investigator.account_workflow import run_transaction_investigation
from domain.investigation.schemas import TransactionInvestigationRequest
from domain.investigation.rule_registry import BANKING_RULES_REGISTRY


@pytest.mark.asyncio
async def test_high_value_transfer_held_and_investigation_5_line_report():
    """Verify that huge money transfer (>50,000 EGP) is held in the middle with token and produces 5-line report."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # 1. Setup Sender and Recipient
        ts = int(datetime.now(UTC).timestamp())
        sender_user = User(
            external_id=f"USR-{ts}-SND",
            email=f"sender_high_{ts}@omerta.ai",
            username=f"snd_high_{ts}",
            full_name="Tariq Mansour",
            hashed_password="hashed_pw_test",
            role="CUSTOMER",
        )
        recipient_user = User(
            external_id=f"USR-{ts}-RCV",
            email=f"recip_high_{ts}@omerta.ai",
            username=f"recip_high_{ts}",
            full_name="Laila Fathy",
            hashed_password="hashed_pw_test",
            role="CUSTOMER",
        )
        session.add_all([sender_user, recipient_user])
        await session.flush()

        sender_cust = Customer(
            external_id=f"CUST-SND-{ts}",
            user_id=sender_user.id,
            name="Tariq Mansour",
            email=sender_user.email,
            omerta_user_number=f"USR-HGH-{ts}",
            status="ACTIVE",
            transfer_status="ACTIVE",
            registration_date=datetime.now(UTC),
        )
        recip_cust = Customer(
            external_id=f"CUST-RCV-{ts}",
            user_id=recipient_user.id,
            name="Laila Fathy",
            email=recipient_user.email,
            omerta_user_number=f"USR-RCV-{ts}",
            status="ACTIVE",
            transfer_status="ACTIVE",
            registration_date=datetime.now(UTC),
        )
        session.add_all([sender_cust, recip_cust])
        await session.flush()

        sender_acc = Account(
            external_id=f"ACC-SND-{ts}",
            customer_id=sender_cust.id,
            customer_name="Tariq Mansour",
            account_type="CHECKING",
            country="EG",
            currency="EGP",
            balance=Decimal("200000.00"),
            status="ACTIVE",
        )
        recip_acc = Account(
            external_id=f"ACC-RCV-{ts}",
            customer_id=recip_cust.id,
            customer_name="Laila Fathy",
            account_type="CHECKING",
            country="EG",
            currency="EGP",
            balance=Decimal("5000.00"),
            status="ACTIVE",
        )
        session.add_all([sender_acc, recip_acc])
        await session.commit()

        # 2. Execute Huge Money Transfer (60,000 EGP)
        transfer_svc = TransferService(session)
        receipt = await transfer_svc.execute_transfer(
            sender_user_id=sender_user.id,
            sender_account_id=sender_acc.external_id,
            recipient_user_number=recip_cust.omerta_user_number,
            amount=Decimal("60000.00"),
            currency="EGP",
            note="Huge money payment for property acquisition",
            is_vpn=False,
        )

        # Invariant: Must NOT settle immediately, funds stay held in sender account!
        assert receipt["status"] == "PENDING_CUSTOMER_VERIFICATION"
        assert receipt["transaction_id"] is not None

        # Verify balances: Sender must NOT be debited, Recipient must NOT be credited
        refreshed_sender = await session.scalar(select(Account).where(Account.id == sender_acc.id))
        refreshed_recip = await session.scalar(select(Account).where(Account.id == recip_acc.id))
        assert refreshed_sender.balance == Decimal("200000.00")
        assert refreshed_recip.balance == Decimal("5000.00")

        # 3. Run Investigation Workflow for this Transaction
        req = TransactionInvestigationRequest(
            transaction_id=receipt["transaction_id"],
            time_range_days=30,
        )
        report = await run_transaction_investigation(req, caller_role="ADMINISTRATOR")

        # Verify Report structure: Exactly 5 sharp lines with real data!
        assert report.forensic_report_markdown is not None
        lines = [line.strip() for line in report.forensic_report_markdown.split("\n") if line.strip() and line.strip().startswith("•")]
        assert len(lines) == 5, f"Expected 5 forensic lines, got {len(lines)}: {report.forensic_report_markdown}"

        # Line 1: Transaction Details
        assert "1. Transaction Details" in lines[0]
        assert receipt["transaction_id"].replace("-", "") in lines[0].replace("\u2011", "").replace("-", "")
        assert "60,000.00" in lines[0]

        # Line 2: Rules & Velocity
        assert "2. Deterministic Banking Rules & Velocity" in lines[1]
        assert "High-Value Transfer Threshold Exceeded".replace("-", "") in lines[1].replace("\u2011", "").replace("-", "")

        # Line 3: LightGBM ML
        assert "3. LightGBM Machine Learning Model" in lines[2]

        # Line 4: Network & Graph
        assert "4. Network, Device & Graph Topology" in lines[3]

        # Line 5: Consensus & Directive
        assert "5. Risk Consensus & Action Directive" in lines[4]
