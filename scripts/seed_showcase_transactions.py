"""Showcase Data Seeder for Omerta.ai.

Creates realistic low-risk (legitimate) and high-risk (financial crime / AML) transactions
in the PostgreSQL ledger and projects them into Neo4j graph topology.

Low-Risk Showcase Cases:
- TXN-LEGIT-101: 1,250 EGP Routine Supermarket POS (Low ML score, 0 rules triggered, Routine Monitoring)
- TXN-LEGIT-102: 2,400 EGP Regular Domestic P2P Family Transfer (Clean device, verified history)
- TXN-LEGIT-103: 500 EGP Utility Bill Payment (Verified utility biller, clean ledger)

High-Risk Showcase Cases:
- TXN-RISK-501: 48,900 EGP Cash Structuring / Smurfing (FATF R.20 Alert, amounts just beneath 50k threshold)
- TXN-RISK-502: 35,000 EGP Multi-Account Hardware Syndicate (Neo4j Graph Alert, shared hardware fingerprint)
- TXN-RISK-503: 42,000 EGP Monotonic Amount Escalation & ATO (Testing micro-transfers followed by rapid drain)
"""

import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_engine
from infrastructure.database.models import (
    Account,
    Customer,
    Device,
    IPAddress,
    Transaction,
    AccountLedgerEntry,
    InvestigationCase,
)
from infrastructure.neo4j.projection import project_all
from apps.investigator.account_workflow import run_transaction_investigation
from domain.investigation.schemas import TransactionInvestigationRequest, InvestigationReason


async def seed_showcase_data():
    engine = get_engine()
    now = datetime.now(timezone.utc)

    print("=== Seeding Omerta.ai Showcase Transactions (Low-Risk vs High-Risk) ===")

    async with AsyncSession(engine) as session:
        # 1. Ensure Devices exist
        devices_to_create = [
            ("DEV-CLEAN-01", "MOBILE", "LOW"),
            ("DEV-CLEAN-02", "DESKTOP", "LOW"),
            ("DEV-SYN-X99", "DESKTOP", "HIGH"),
            ("DEV-ATO-UNKNOWN", "MOBILE", "CRITICAL"),
        ]
        dev_map: dict[str, Device] = {}
        for ext_id, dtype, rlevel in devices_to_create:
            existing = await session.scalar(select(Device).where(Device.external_id == ext_id))
            if not existing:
                dev = Device(
                    external_id=ext_id,
                    device_type=dtype,
                    platform="Android" if dtype == "MOBILE" else "Windows",
                    pseudonym_hash=f"hash_{ext_id.lower()}",
                    risk_level=rlevel,
                    is_emulator=(rlevel == "CRITICAL"),
                    is_rooted=(rlevel == "CRITICAL"),
                    first_seen_at=now - timedelta(days=90),
                    last_seen_at=now,
                )
                session.add(dev)
                await session.flush()
                dev_map[ext_id] = dev
            else:
                dev_map[ext_id] = existing

        # 2. Ensure IP Addresses exist
        ips_to_create = [
            ("156.204.12.44", "EG", "LOW", False),
            ("198.51.100.23", "CH", "HIGH", True),
            ("202.0.113.77", "PA", "CRITICAL", True),
        ]
        ip_map: dict[str, IPAddress] = {}
        for addr, ccode, rlevel, is_vpn in ips_to_create:
            existing = await session.scalar(select(IPAddress).where(IPAddress.address == addr))
            if not existing:
                ip = IPAddress(
                    address=addr,
                    country=ccode,
                    risk_level=rlevel,
                    is_vpn=is_vpn,
                    is_datacenter=is_vpn,
                    first_seen_at=now - timedelta(days=90),
                    last_seen_at=now,
                )
                session.add(ip)
                await session.flush()
                ip_map[addr] = ip
            else:
                ip_map[addr] = existing

        # 3. Retrieve Accounts
        acc_0001 = await session.scalar(select(Account).where(Account.external_id == "ACC-0001"))
        acc_1001 = await session.scalar(select(Account).where(Account.external_id == "ACC-1001"))
        acc_2001 = await session.scalar(select(Account).where(Account.external_id == "ACC-2001"))
        acc_3001 = await session.scalar(select(Account).where(Account.external_id == "ACC-3001"))
        acc_4001 = await session.scalar(select(Account).where(Account.external_id == "ACC-4001"))
        acc_5001 = await session.scalar(select(Account).where(Account.external_id == "ACC-5001"))
        acc_6001 = await session.scalar(select(Account).where(Account.external_id == "ACC-6001"))
        acc_7001 = await session.scalar(select(Account).where(Account.external_id == "ACC-7001"))
        acc_8001 = await session.scalar(select(Account).where(Account.external_id == "ACC-8001"))
        acc_9001 = await session.scalar(select(Account).where(Account.external_id == "ACC-9001"))

        # 4. Helper function to insert transaction
        async def ensure_transaction(
            txn_id: str,
            account: Account,
            recipient: Account | None,
            amount: Decimal,
            ttype: str,
            status: str,
            risk_score: float,
            risk_level: str,
            timestamp: datetime,
            device_id: str,
            ip_addr: str,
            is_new_device: bool = False,
            is_new_ip: bool = False,
            description: str = "",
        ) -> Transaction:
            existing = await session.scalar(select(Transaction).where(Transaction.external_id == txn_id))
            dev = dev_map.get(device_id)
            ip = ip_map.get(ip_addr)
            if existing:
                existing.amount = amount
                existing.risk_score = Decimal(str(risk_score))
                existing.risk_level = risk_level
                existing.timestamp = timestamp
                existing.device_id = dev.id if dev else None
                existing.ip_address_id = ip.id if ip else None
                existing.is_new_device = is_new_device
                existing.is_new_ip = is_new_ip
                existing.txn_metadata = {"note": description}
                await session.flush()
                return existing

            txn = Transaction(
                external_id=txn_id,
                account_id=account.id,
                recipient_account_id=recipient.id if recipient else None,
                device_id=dev.id if dev else None,
                ip_address_id=ip.id if ip else None,
                amount=amount,
                currency=account.currency or "EGP",
                transaction_type=ttype,
                status=status,
                risk_score=Decimal(str(risk_score)),
                risk_level=risk_level,
                timestamp=timestamp,
                is_new_device=is_new_device,
                is_new_ip=is_new_ip,
                txn_metadata={"note": description},
            )
            session.add(txn)
            await session.flush()
            return txn

        print("Creating Low-Risk Retail Showcase Transactions...")
        # LOW-RISK 1: Routine Supermarket Grocery Checkout
        await ensure_transaction(
            txn_id="TXN-LEGIT-101",
            account=acc_0001,
            recipient=acc_3001,
            amount=Decimal("1250.00"),
            ttype="POS_PAYMENT",
            status="COMPLETED",
            risk_score=5.00,
            risk_level="LOW",
            timestamp=now - timedelta(hours=3),
            device_id="DEV-CLEAN-01",
            ip_addr="156.204.12.44",
            description="Routine POS Purchase - Metro Supermarket Cairo",
        )

        # LOW-RISK 2: Regular Domestic P2P Family Transfer
        await ensure_transaction(
            txn_id="TXN-LEGIT-102",
            account=acc_2001,
            recipient=acc_1001,
            amount=Decimal("2400.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=7.00,
            risk_level="LOW",
            timestamp=now - timedelta(hours=6),
            device_id="DEV-CLEAN-02",
            ip_addr="156.204.12.44",
            description="P2P Transfer - Routine family living expense support",
        )

        # LOW-RISK 3: Utility Bill Settlement
        await ensure_transaction(
            txn_id="TXN-LEGIT-103",
            account=acc_1001,
            recipient=acc_4001,
            amount=Decimal("500.00"),
            ttype="BILL_PAYMENT",
            status="COMPLETED",
            risk_score=4.00,
            risk_level="LOW",
            timestamp=now - timedelta(hours=12),
            device_id="DEV-CLEAN-01",
            ip_addr="156.204.12.44",
            description="Automated Utility Settlement - WE Egypt Telecom Fiber",
        )

        print("Creating High-Risk AML / Financial Crime Showcase Transactions...")
        # HIGH-RISK 1: Cash Structuring / Smurfing Pattern (FATF R.20)
        # Prior transaction 90 minutes earlier
        await ensure_transaction(
            txn_id="TXN-STR-PRECEDING",
            account=acc_8001,
            recipient=acc_9001,
            amount=Decimal("46500.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=85.00,
            risk_level="HIGH",
            timestamp=now - timedelta(minutes=90),
            device_id="DEV-SYN-X99",
            ip_addr="198.51.100.23",
            description="Structured outbound wire 1 of 2",
        )
        # Target transaction just under 50,000 statutory limit
        await ensure_transaction(
            txn_id="TXN-RISK-501",
            account=acc_8001,
            recipient=acc_9001,
            amount=Decimal("48900.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=92.00,
            risk_level="CRITICAL",
            timestamp=now - timedelta(minutes=15),
            device_id="DEV-SYN-X99",
            ip_addr="198.51.100.23",
            description="Potential Smurfing: Transfer of 48,900 EGP deliberately beneath 50k threshold",
        )

        # HIGH-RISK 2: Multi-Account Hardware Syndicate (Neo4j Graph Topology)
        # Link accounts 5001, 6001, 7001 to same device DEV-SYN-X99
        await ensure_transaction(
            txn_id="TXN-SYN-LINK-1",
            account=acc_5001,
            recipient=acc_9001,
            amount=Decimal("28000.00"),
            ttype="TRANSFER",
            status="COMPLETED",
            risk_score=80.00,
            risk_level="HIGH",
            timestamp=now - timedelta(hours=4),
            device_id="DEV-SYN-X99",
            ip_addr="198.51.100.23",
            description="Syndicate member transfer node A",
        )
        await ensure_transaction(
            txn_id="TXN-RISK-502",
            account=acc_6001,
            recipient=acc_9001,
            amount=Decimal("35000.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=95.00,
            risk_level="CRITICAL",
            timestamp=now - timedelta(minutes=45),
            device_id="DEV-SYN-X99",
            ip_addr="198.51.100.23",
            description="Syndicate Cluster Transfer - Shared hardware fingerprint across 3+ unrelated accounts",
        )

        # HIGH-RISK 3: Account Takeover (ATO) with Escalating Sequence
        # Sequence: 150 EGP micro-test -> 2,000 EGP test -> 42,000 EGP liquidation
        await ensure_transaction(
            txn_id="TXN-ATO-TEST-1",
            account=acc_7001,
            recipient=acc_9001,
            amount=Decimal("150.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=45.00,
            risk_level="MEDIUM",
            timestamp=now - timedelta(hours=3),
            device_id="DEV-ATO-UNKNOWN",
            ip_addr="202.0.113.77",
            is_new_device=True,
            is_new_ip=True,
            description="ATO Probe: Initial micro-testing transfer",
        )
        await ensure_transaction(
            txn_id="TXN-ATO-TEST-2",
            account=acc_7001,
            recipient=acc_9001,
            amount=Decimal("2000.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=65.00,
            risk_level="HIGH",
            timestamp=now - timedelta(hours=1, minutes=30),
            device_id="DEV-ATO-UNKNOWN",
            ip_addr="202.0.113.77",
            is_new_device=True,
            is_new_ip=True,
            description="ATO Probe: Secondary verification transfer",
        )
        await ensure_transaction(
            txn_id="TXN-RISK-503",
            account=acc_7001,
            recipient=acc_9001,
            amount=Decimal("42000.00"),
            ttype="CUSTOMER_TRANSFER",
            status="COMPLETED",
            risk_score=89.00,
            risk_level="CRITICAL",
            timestamp=now - timedelta(minutes=20),
            device_id="DEV-ATO-UNKNOWN",
            ip_addr="202.0.113.77",
            is_new_device=True,
            is_new_ip=True,
            description="Account Takeover Rapid Draining - Foreign proxy and untrusted emulator hardware",
        )

        await session.commit()
        print("[OK] Relational transactions committed to PostgreSQL successfully.")

    # 5. Project all transactions, devices, and accounts into Neo4j
    print("[*] Projecting entities and relationships into Neo4j Graph Database...")
    try:
        await project_all(engine)
        print("[OK] Neo4j projection completed successfully.")
    except Exception as exc:
        print(f"[WARN] Neo4j projection warning: {exc}")

    # 6. Pre-generate and persist forensic investigation dossiers for immediate viewing
    print("[*] Generating verified forensic investigation reports for showcase...")
    
    # Pre-investigate TXN-LEGIT-101 (Low Risk)
    print(" -> Investigating TXN-LEGIT-101 (Low Risk)...")
    req_low = TransactionInvestigationRequest(
        transaction_id="TXN-LEGIT-101",
        time_range_days=30,
        investigation_reason=InvestigationReason.ROUTINE_MONITORING,
        persist=True,
    )
    rep_low = await run_transaction_investigation(req_low)
    print(f"    Done: Combined Score = {rep_low.combined_risk_score:.1%}, Action = {rep_low.recommended_action}")

    # Pre-investigate TXN-RISK-501 (High Risk Structuring)
    print(" -> Investigating TXN-RISK-501 (High Risk Structuring)...")
    req_high = TransactionInvestigationRequest(
        transaction_id="TXN-RISK-501",
        time_range_days=30,
        investigation_reason=InvestigationReason.AMOUNT_ESCALATION,
        persist=True,
    )
    rep_high = await run_transaction_investigation(req_high)
    print(f"    Done: Combined Score = {rep_high.combined_risk_score:.1%}, Action = {rep_high.recommended_action}")

    print("\n=== SHOWCASE SEEDING COMPLETE ===")
    print("=" * 60)
    print("LOW-RISK (CLEAN) TRANSACTIONS TO TEST ON THE SITE:")
    print(" 1. TXN-LEGIT-101  (Pre-investigated: Routine 1,250 EGP POS purchase, score < 15%)")
    print(" 2. TXN-LEGIT-102  (Ready for Live Run: 2,400 EGP P2P Family Transfer, click Run Investigation)")
    print(" 3. TXN-LEGIT-103  (Ready for Live Run: 500 EGP Utility Bill Payment)")
    print("-" * 60)
    print("HIGH-RISK (SUSPICIOUS) TRANSACTIONS TO TEST ON THE SITE:")
    print(" 1. TXN-RISK-501   (Pre-investigated: 48,900 EGP Structuring under 50k limit, FATF Alert, score > 80%)")
    print(" 2. TXN-RISK-502   (Ready for Live Run: 35,000 EGP Hardware Syndicate Ring, Neo4j Topology Alert)")
    print(" 3. TXN-RISK-503   (Ready for Live Run: 42,000 EGP Account Takeover, Escalation Micro-tests)")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed_showcase_data())
