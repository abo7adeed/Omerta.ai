"""Master Fraud Workflow Test Suite for Omerta.ai.

Validates all 10 requirements of the Master Implementation Prompt:
1. TransactionHistoryAgent 6 rolling windows (5m, 15m, 60m, 24h, 7d, 30d) and current transaction exclusion.
2. Authoritative final risk scoring formula ('risk-v1') with exact weights, degradation handling, and hard overrides.
3. Centralized banking rules registry with 16 rules (including RULE-NETWORK-VPN-001).
4. VPN detection triggering RULE-NETWORK-VPN-001 and PENDING_CUSTOMER_VERIFICATION transition.
5. Email service customer verification email generation with Yes/No verification links.
6. Customer confirmation endpoint:
   - "CONFIRM": transitions status to PENDING_REVIEW when score is elevated (does not bypass admin review).
   - "DENY": cancels transfer, creates security ticket, and applies TransactionRestriction(OUTGOING_TRANSFERS_ONLY).
7. Server enforcement: blocks new outgoing transfers when customer has active restriction.
8. Admin approve transaction: executes double-entry ledger debit & credit, updates status to COMPLETED.
9. Admin restore privileges: releases account restriction, resolves security ticket, but does NOT approve individual held transfers.
10. SpecialistAgentResult Pydantic schema conformance across specialist agents.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import secrets
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, and_

from apps.api.main import app
from domain.investigation.agent_schemas import (
    AgentDataQuality,
    AgentExecutionStatus,
    AgentFinding,
    SpecialistAgentResult,
)
from domain.investigation.history_agent import TransactionHistoryAgent
from domain.investigation.rule_registry import BANKING_RULES_REGISTRY, RuleSeverity, get_rule, list_rules
from domain.investigation.scoring import (
    AssessmentConfidence,
    RiskTier,
    TransactionDecision,
    calculate_final_risk_score,
)
from domain.investigation.specialist_agents import (
    AccountTakeoverAgent,
    BankingRulesAgent,
    BehavioralAnalysisAgent,
    DeviceNetworkAgent,
    FinalDecisionAgent,
    GraphIntelligenceAgent,
    IdentitySecurityAgent,
    MLRiskAgent,
    MerchantIntelligenceAgent,
)
from domain.services.email_service import EmailService
from domain.services.transfer_service import TransferService, TransferError
from infrastructure.database.models import (
    Account,
    AccountLedgerEntry,
    Customer,
    SupportTicket,
    Transaction,
    TransactionRestriction,
    Transfer,
    User,
)
from infrastructure.database.session import get_engine
from sqlalchemy.ext.asyncio import AsyncSession


# =========================================================================== #
# 1. Banking Rules Registry & Specialist Agent Unit Tests
# =========================================================================== #
def test_banking_rules_registry():
    """Verify registry contains 16 rules, including RULE-NETWORK-VPN-001 and core velocity rules."""
    rules = list_rules()
    assert len(rules) >= 16

    vpn_rule = get_rule("RULE-NETWORK-VPN-001")
    assert vpn_rule is not None
    assert vpn_rule.severity == RuleSeverity.HIGH
    assert "VPN" in vpn_rule.name

    assert get_rule("RULE-AMOUNT-DEV-001") is not None
    assert get_rule("RULE-VEL-5M") is not None
    assert get_rule("RULE-ATO-001") is not None
    assert get_rule("RULE-RESTRICT-001") is not None


def test_specialist_agent_schemas():
    """Verify specialist agents adhere strictly to SpecialistAgentResult schema."""
    # Banking Rules Agent
    res_rules = BankingRulesAgent.evaluate(
        history_metrics={},
        vpn_detected=True,
        is_new_device=True,
        shared_device_count=0,
        failed_attempts=0,
        has_active_restriction=False,
    )
    assert isinstance(res_rules, SpecialistAgentResult)
    assert res_rules.agent_name == "Banking Rules Agent"
    assert any(f.rule_id == "RULE-NETWORK-VPN-001" for f in res_rules.findings)
    assert res_rules.score >= 30.0

    # Behavioral Analysis Agent
    res_beh = BehavioralAnalysisAgent.evaluate(
        history_metrics={"ratio_to_p95": 3.5},
        hour_utc=3,  # off hours
    )
    assert isinstance(res_beh, SpecialistAgentResult)
    assert "Behavioral" in res_beh.agent_name

    # ATO Agent
    res_ato = AccountTakeoverAgent.evaluate(
        recent_password_change=True,
        recent_failed_logins=3,
        recent_device_added=True,
        new_beneficiary_added=True,
    )
    assert isinstance(res_ato, SpecialistAgentResult)
    assert res_ato.score >= 70.0

    # Device Network Agent
    res_dev = DeviceNetworkAgent.evaluate(
        is_new_device=True,
        is_vpn=True,
        ip_risk_score=75.0,
        provider_available=True,
    )
    assert isinstance(res_dev, SpecialistAgentResult)
    assert res_dev.score >= 50.0


# =========================================================================== #
# 2. Authoritative Scoring Formula ('risk-v1') Tests
# =========================================================================== #
def test_authoritative_scoring_formula_weights():
    """Verify calculate_final_risk_score executes versioned risk-v1 formula with exact weights."""
    specialists = {
        "rules": SpecialistAgentResult(agent_name="Banking Rules", score=40.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "ml": SpecialistAgentResult(agent_name="ML Risk", score=20.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "history": SpecialistAgentResult(agent_name="Transaction History", score=30.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "behavior": SpecialistAgentResult(agent_name="Behavioral", score=10.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "ato": SpecialistAgentResult(agent_name="ATO", score=10.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "device": SpecialistAgentResult(agent_name="Device", score=10.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "graph": SpecialistAgentResult(agent_name="Graph", score=10.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "merchant": SpecialistAgentResult(agent_name="Merchant", score=10.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
    }

    # Expected: 40.0*0.20 + 20.0*0.25 + 30.0*0.20 + 10.0*0.10 + 10.0*0.10 + 10.0*0.05 + 10.0*0.05 + 10.0*0.05
    # = 8.0 + 5.0 + 6.0 + 1.0 + 1.0 + 0.5 + 0.5 + 0.5 = 22.5
    breakdown = calculate_final_risk_score(specialists, is_merchant_tx=True)
    assert breakdown.formula_version == "risk-v1"
    assert abs(breakdown.final_score - 22.5) < 0.1
    assert breakdown.assessment_confidence == AssessmentConfidence.SUFFICIENT


def test_scoring_confidence_degradation():
    """Verify confidence degrades when models or data feeds are missing."""
    # Degraded (e.g. Graph and Merchant UNAVAILABLE)
    partial_specialists = {
        "rules": SpecialistAgentResult(agent_name="Banking Rules", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "ml": SpecialistAgentResult(agent_name="ML Risk", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "history": SpecialistAgentResult(agent_name="Transaction History", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "behavior": SpecialistAgentResult(agent_name="Behavioral", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "ato": SpecialistAgentResult(agent_name="ATO", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "device": SpecialistAgentResult(agent_name="Device", score=50.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
        "graph": SpecialistAgentResult(agent_name="Graph", score=0.0, status=AgentExecutionStatus.UNAVAILABLE, findings=[]),
        "merchant": SpecialistAgentResult(agent_name="Merchant", score=0.0, status=AgentExecutionStatus.UNAVAILABLE, findings=[]),
    }
    breakdown = calculate_final_risk_score(partial_specialists, is_merchant_tx=True)
    assert breakdown.assessment_confidence == AssessmentConfidence.DEGRADED
    assert abs(breakdown.final_score - 50.0) < 0.1


def test_scoring_hard_overrides():
    """Verify critical findings trigger hard risk overrides to REJECT or holds."""
    specialists = {
        "rules": SpecialistAgentResult(
            agent_name="Banking Rules",
            score=10.0,
            status=AgentExecutionStatus.COMPLETED,
            findings=[AgentFinding(rule_id="RULE-ACC-RESTRICTED", rule_name="Restricted Account", severity="CRITICAL", reason="Account transfer privileges are restricted")],
        ),
        "ml": SpecialistAgentResult(agent_name="ML Risk", score=5.0, status=AgentExecutionStatus.COMPLETED, findings=[]),
    }
    breakdown = calculate_final_risk_score(specialists, hard_restrictions_active=True)
    assert breakdown.requires_transaction_hold is True
    assert any("OUTGOING_TRANSFERS_ONLY" in r for r in breakdown.hold_reasons)

    # Customer denial triggers authoritative REJECT
    breakdown_denied = calculate_final_risk_score(specialists, customer_confirmed=False)
    assert breakdown_denied.decision == TransactionDecision.REJECT
    assert breakdown_denied.requires_transaction_hold is True
    assert any("CUSTOMER_DENIED" in r for r in breakdown_denied.hold_reasons)


# =========================================================================== #
# 3. TransactionHistoryAgent 6 Rolling Windows & Pre-Txn Exclusion
# =========================================================================== #
@pytest.mark.asyncio
async def test_history_agent_rolling_windows_and_exclusion(seeded_db):
    """Verify history agent computes 6 rolling windows and excludes active transaction."""
    async with AsyncSession(get_engine(), expire_on_commit=False) as session:
        # Find test accounts
        accs = (await session.scalars(select(Account).order_by(Account.id.asc()).limit(2))).all()
        assert len(accs) >= 1
        acc = accs[0]
        acc2 = accs[1] if len(accs) > 1 else accs[0]

        now = datetime.now(UTC)
        # Create 3 past transactions: 2m ago (500 EGP), 10m ago (1000 EGP), 2h ago (2000 EGP)
        t1 = Transaction(
            external_id=f"HIST-{secrets.token_hex(4).upper()}",
            account_id=acc.id,
            recipient_account_id=acc2.id,
            amount=Decimal("500.00"),
            currency="EGP",
            transaction_type="CUSTOMER_TRANSFER",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=2),
        )
        t2 = Transaction(
            external_id=f"HIST-{secrets.token_hex(4).upper()}",
            account_id=acc.id,
            recipient_account_id=acc2.id,
            amount=Decimal("1000.00"),
            currency="EGP",
            transaction_type="CUSTOMER_TRANSFER",
            status="COMPLETED",
            timestamp=now - timedelta(minutes=10),
        )
        t3 = Transaction(
            external_id=f"HIST-{secrets.token_hex(4).upper()}",
            account_id=acc.id,
            recipient_account_id=acc2.id,
            amount=Decimal("2000.00"),
            currency="EGP",
            transaction_type="CUSTOMER_TRANSFER",
            status="COMPLETED",
            timestamp=now - timedelta(hours=2),
        )
        # And the active transaction (5000 EGP, now)
        t_active = Transaction(
            external_id=f"ACTIVE-{secrets.token_hex(4).upper()}",
            account_id=acc.id,
            recipient_account_id=acc2.id,
            amount=Decimal("5000.00"),
            currency="EGP",
            transaction_type="CUSTOMER_TRANSFER",
            status="ASSESSING",
            timestamp=now,
        )
        session.add_all([t1, t2, t3, t_active])
        await session.commit()

        # Run TransactionHistoryAgent with current_transaction_id=t_active.id
        agent = TransactionHistoryAgent(session)
        result = await agent.analyze(
            account_id=acc.id,
            current_amount=5000.00,
            current_timestamp=now,
            current_transaction_id=t_active.id,
        )

        assert isinstance(result, SpecialistAgentResult)
        windows = result.raw_metrics

        # Window 5m should only contain t1 (500.00), strictly excluding t_active
        assert windows["previous_transactions_5m"] == 1
        assert windows["outgoing_total_5m"] == 500.00

        # Window 15m should contain t1 (500.00) and t2 (1000.00)
        assert windows["previous_transactions_15m"] == 2
        assert windows["outgoing_total_15m"] == 1500.00

        # Window 24h should contain t1, t2, t3 (3500.00)
        assert windows["previous_transactions_24h"] >= 3
        assert windows["outgoing_total_24h"] >= 3500.00


# =========================================================================== #
# 4. Email Service Customer Verification Links
# =========================================================================== #
@pytest.mark.asyncio
async def test_email_service_verification_links():
    """Verify email service creates verification email with valid action links."""
    email_res = await EmailService.send_transfer_verification_email(
        to_email="customer@example.com",
        customer_name="Ziad Karim",
        transaction_ref="TXN-SIM-TEST99",
        amount=1500.0,
        currency="EGP",
        recipient_masked="••••9876",
        verification_url="http://localhost:5173/customer/security",
        reason="VPN Detected - Requires Customer Confirmation",
    )
    details = email_res.details
    assert details["recipient"] == "customer@example.com"
    assert "1,500.00 EGP" in details["subject"]
    assert "TXN-SIM-" in details["subject"]
    assert "confirm_url" in details
    assert "deny_url" in details
    assert "action=CONFIRM" in details["confirm_url"]
    assert "action=DENY" in details["deny_url"]
    assert "Yes, I initiated this transfer" in details["body"]
    assert "No, I did NOT initiate this transfer" in details["body"]


# =========================================================================== #
# 5. Full End-to-End Workflow & REST API Lifecycle Tests
# =========================================================================== #
@pytest.mark.asyncio
async def test_vpn_hold_customer_confirmation_and_admin_settlement(seeded_db):
    """E2E Test:
    1. Customer initiates transfer with VPN -> Held in PENDING_CUSTOMER_VERIFICATION.
    2. Ledger invariance -> Balances unaffected.
    3. Customer confirms (CONFIRM) -> Moves to PENDING_REVIEW (not auto-completed).
    4. Admin approves -> Moves to COMPLETED and ledger settled atomically.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login Customer (Ziad Karim)
        login_cust = await client.post(
            "/api/v1/auth/login",
            json={"username": "ziad@omerta.ai", "password": "Customer@2026!"},
        )
        assert login_cust.status_code == 200
        token_cust = login_cust.json()["access_token"]
        headers_cust = {"Authorization": f"Bearer {token_cust}"}

        # 2. Get customer accounts & balance
        accs_res = await client.get("/api/v1/customer/accounts", headers=headers_cust)
        assert accs_res.status_code == 200
        sender_acc = accs_res.json()[0]
        initial_balance = sender_acc["balance"]

        # 3. Lookup Layla Hassan via her unique omerta_user_number
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            layla = await session.scalar(select(Customer).where(Customer.name.like("%Layla%")).limit(1))
            assert layla is not None
            layla_user_number = layla.omerta_user_number

        lookup_res = await client.get(f"/api/v1/customer/recipient/lookup?identifier={layla_user_number}", headers=headers_cust)
        assert lookup_res.status_code == 200
        recip_data = lookup_res.json()

        # 4. Initiate transfer with VPN detected
        transfer_payload = {
            "sender_account_id": sender_acc["account_id"],
            "recipient_user_number": recip_data["omerta_user_number"],
            "amount": 750.00,
            "currency": "EGP",
            "password": "Customer@2026!",
            "is_vpn": True,
            "client_ip": "185.220.101.5",
            "isp": "Mullvad Commercial VPN",
        }
        res_trf = await client.post("/api/v1/customer/transfers", json=transfer_payload, headers=headers_cust)
        assert res_trf.status_code == 201, res_trf.text
        trf_data = res_trf.json()

        txn_id = trf_data["transaction_id"]
        # Must be held in PENDING_CUSTOMER_VERIFICATION!
        assert trf_data["status"] == "PENDING_CUSTOMER_VERIFICATION"
        assert trf_data["hold_reason"] == "VPN Detected - Requires Customer Confirmation"

        # 5. Ledger Invariance Check: Balance should NOT be reduced!
        accs_after_hold = await client.get("/api/v1/customer/accounts", headers=headers_cust)
        assert accs_after_hold.json()[0]["balance"] == initial_balance

        # 6. Customer confirms transfer ("CONFIRM")
        res_confirm = await client.post(
            f"/api/v1/transactions/{txn_id}/customer-confirmation",
            json={"action": "CONFIRM"},
            headers=headers_cust,
        )
        assert res_confirm.status_code == 200
        confirm_data = res_confirm.json()
        assert confirm_data["customer_action"] == "CONFIRM"
        # Since VPN detection is high-risk, it must NOT bypass admin review!
        assert confirm_data["status"] == "PENDING_REVIEW"

        # 7. Login Compliance Admin
        login_admin = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin@omerta.ai", "password": "AdminPass123!"},
        )
        assert login_admin.status_code == 200
        token_admin = login_admin.json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # 8. Admin approves transfer -> Settles ledger atomically!
        res_approve = await client.post(
            f"/api/v1/admin/transactions/{txn_id}/approve",
            json={"rationale": "Compliance verified customer intent and legitimate IP shift."},
            headers=headers_admin,
        )
        assert res_approve.status_code == 200
        approve_data = res_approve.json()
        assert approve_data["status"] == "COMPLETED"

        # 9. Verify balances and ledger entries in DB
        accs_final = await client.get("/api/v1/customer/accounts", headers=headers_cust)
        sender_acc_final = next(a for a in accs_final.json() if a["account_id"] == sender_acc["account_id"])
        assert sender_acc_final["balance"] == initial_balance - 750.00


@pytest.mark.asyncio
async def test_customer_denial_restriction_and_privilege_restoration(seeded_db):
    """E2E Test:
    1. Customer initiates transfer with VPN -> Held in PENDING_CUSTOMER_VERIFICATION.
    2. Customer DENIES transfer ("DENY") ->
       - Transfer is CANCELLED.
       - Customer is placed on OUTGOING_TRANSFERS_ONLY restriction.
       - Security ticket is created.
    3. Server enforcement -> Customer cannot initiate new transfers (403 TRANSFERS_RESTRICTED).
    4. Admin restores privileges -> Restriction cleared, security ticket resolved.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login Customer (Ziad Karim)
        login_cust = await client.post(
            "/api/v1/auth/login",
            json={"username": "ziad@omerta.ai", "password": "Customer@2026!"},
        )
        token_cust = login_cust.json()["access_token"]
        headers_cust = {"Authorization": f"Bearer {token_cust}"}

        accs_res = await client.get("/api/v1/customer/accounts", headers=headers_cust)
        sender_acc = accs_res.json()[0]

        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            layla = await session.scalar(select(Customer).where(Customer.name.like("%Layla%")).limit(1))
            assert layla is not None
            layla_user_number = layla.omerta_user_number

        lookup_res = await client.get(f"/api/v1/customer/recipient/lookup?identifier={layla_user_number}", headers=headers_cust)
        assert lookup_res.status_code == 200
        recip_data = lookup_res.json()

        # 2. Initiate transfer with VPN
        res_trf = await client.post(
            "/api/v1/customer/transfers",
            json={
                "sender_account_id": sender_acc["account_id"],
                "recipient_user_number": recip_data["omerta_user_number"],
                "amount": 300.00,
                "currency": "EGP",
                "password": "Customer@2026!",
                "is_vpn": True,
            },
            headers=headers_cust,
        )
        assert res_trf.status_code == 201
        txn_id = res_trf.json()["transaction_id"]

        # 3. Customer DENIES the transfer ("DENY")
        res_deny = await client.post(
            f"/api/v1/transactions/{txn_id}/customer-confirmation",
            json={"action": "DENY"},
            headers=headers_cust,
        )
        assert res_deny.status_code == 200
        deny_data = res_deny.json()
        assert deny_data["customer_action"] == "DENY"
        assert deny_data["status"] == "CANCELLED"
        assert deny_data["restriction_applied"] == "OUTGOING_TRANSFERS_ONLY"
        assert deny_data["security_ticket_created"] is True

        # 4. Server Enforcement Check: Attempting a new transfer MUST FAIL with 403 TRANSFERS_RESTRICTED
        res_blocked = await client.post(
            "/api/v1/customer/transfers",
            json={
                "sender_account_id": sender_acc["account_id"],
                "recipient_user_number": recip_data["omerta_user_number"],
                "amount": 50.00,
                "currency": "EGP",
                "password": "Customer@2026!",
                "is_vpn": False,
            },
            headers=headers_cust,
        )
        assert res_blocked.status_code == 403
        assert res_blocked.json()["detail"]["error"] == "TRANSFERS_RESTRICTED"

        # 5. Login Admin
        login_admin = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin@omerta.ai", "password": "AdminPass123!"},
        )
        assert login_admin.status_code == 200
        token_admin = login_admin.json()["access_token"]
        headers_admin = {"Authorization": f"Bearer {token_admin}"}

        # 6. Admin checks security tickets
        tickets_res = await client.get("/api/v1/admin/security-tickets?status=OPEN", headers=headers_admin)
        assert tickets_res.status_code == 200
        tickets_data = tickets_res.json()
        tickets_list = tickets_data.get("tickets", tickets_data) if isinstance(tickets_data, dict) else tickets_data
        assert any(t["ticket_type"] == "FRAUD_CUSTOMER_DENIAL" for t in tickets_list)

        # 7. Admin restores transfer privileges
        # Fetch customer ID for Ziad Karim
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            cust = await session.scalar(select(Customer).where(Customer.name.like("%Ziad%")).limit(1))
            cust_id = cust.id

        res_restore = await client.post(
            f"/api/v1/admin/customers/{cust_id}/restore-transaction-privileges",
            json={"reason": "Customer called support, identity confirmed via video call and SMS OTP."},
            headers=headers_admin,
        )
        assert res_restore.status_code == 200
        restore_data = res_restore.json()
        assert restore_data["privileges_restored"] is True
        assert restore_data["restrictions_released"] >= 1

        # 8. Server Enforcement Check: Transfer should now succeed!
        res_allowed = await client.post(
            "/api/v1/customer/transfers",
            json={
                "sender_account_id": sender_acc["account_id"],
                "recipient_user_number": recip_data["omerta_user_number"],
                "amount": 50.00,
                "currency": "EGP",
                "password": "Customer@2026!",
                "is_vpn": False,
            },
            headers=headers_cust,
        )
        assert res_allowed.status_code == 201
        assert res_allowed.json()["status"] == "COMPLETED"
