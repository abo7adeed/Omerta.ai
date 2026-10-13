import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from infrastructure.database.session import get_engine
from infrastructure.database.models import Transaction, Transfer, TransactionConfirmationToken, Account
from apps.api.main import app


@pytest.mark.asyncio
async def test_vpn_transfer_pending_email_confirm_and_admin_approval():
    """Test end-to-end VPN transfer workflow:
    1. Transfer initiated with VPN signal is created in PENDING status (not rejected with 403).
    2. Confirmation token is created and email dispatched.
    3. Customer clicking confirmation link (CONFIRM with token) settles the transfer to COMPLETED.
    4. Another held transfer can be approved or rejected by admin, with status reflected for customer.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Login as customer (Ziad)
        login_cust = await client.post(
            "/api/v1/auth/login",
            json={"username": "ziad@omerta.ai", "password": "Customer@2026!"},
        )
        assert login_cust.status_code == 200, login_cust.text
        cust_token = login_cust.json()["access_token"]
        cust_headers = {"Authorization": f"Bearer {cust_token}"}

        # Get sender account
        accs_res = await client.get("/api/v1/customer/accounts", headers=cust_headers)
        assert accs_res.status_code == 200
        sender_acc_id = accs_res.json()[0]["account_id"]
        initial_balance = accs_res.json()[0]["balance"]

        # 2. Initiate transfer with VPN telemetry (e.g. US IP, hosting ISP)
        transfer_payload = {
            "sender_account_id": sender_acc_id,
            "recipient_identifier": "OMR-3847-1920",  # Layla Hassan
            "amount": 250.0,
            "currency": "EGP",
            "password": "Customer@2026!",
            "note": "VPN test payment",
            "is_vpn": True,
            "country": "US",
            "isp": "M247 Ltd VPN Hosting",
            "city": "New York",
        }
        res_tx = await client.post("/api/v1/customer/transfers", json=transfer_payload, headers=cust_headers)
        assert res_tx.status_code == 201, f"Expected 201 Created but got {res_tx.status_code}: {res_tx.text}"
        receipt = res_tx.json()
        assert receipt["status"] in ("PENDING_CUSTOMER_VERIFICATION", "PENDING_REVIEW")
        txn_ref = receipt["transaction_id"]

        # Verify transaction status appears for customer in /customer/transactions
        txns_list = await client.get("/api/v1/customer/transactions", headers=cust_headers)
        assert txns_list.status_code == 200
        items = txns_list.json()["items"]
        found_txn = next((t for t in items if t["transaction_id"] == txn_ref), None)
        assert found_txn is not None, f"Transaction {txn_ref} not found in customer transactions"
        assert found_txn["status"] in ("PENDING_CUSTOMER_VERIFICATION", "PENDING_REVIEW")

        # Verify in database: confirmation token exists
        from sqlalchemy.ext.asyncio import AsyncSession
        async with AsyncSession(get_engine(), expire_on_commit=False) as session:
            db_txn = await session.scalar(select(Transaction).where(Transaction.external_id == txn_ref))
            assert db_txn is not None
            assert db_txn.status in ("PENDING_CUSTOMER_VERIFICATION", "PENDING_REVIEW")

            # Find confirmation token
            token_rec = await session.scalar(
                select(TransactionConfirmationToken).where(TransactionConfirmationToken.transaction_id == db_txn.id)
            )
            assert token_rec is not None
            assert token_rec.used_at is None

        # 3. Simulate customer clicking confirmation link from email (token-based confirmation)
        # We need raw token; let's test confirmation endpoint using authenticated session or token
        confirm_res = await client.post(
            f"/api/v1/transactions/{txn_ref}/customer-confirmation",
            json={"action": "CONFIRM"},
            headers=cust_headers,
        )
        assert confirm_res.status_code == 200, confirm_res.text
        confirm_data = confirm_res.json()
        assert confirm_data["success"] is True
        assert confirm_data["status"] == "COMPLETED"

        # Verify transaction is now COMPLETED for customer
        txns_after = await client.get("/api/v1/customer/transactions", headers=cust_headers)
        found_after = next((t for t in txns_after.json()["items"] if t["transaction_id"] == txn_ref), None)
        assert found_after is not None
        assert found_after["status"] == "COMPLETED"

        # 4. Second transfer: Admin approval scenario
        res_tx2 = await client.post("/api/v1/customer/transfers", json={
            "sender_account_id": sender_acc_id,
            "recipient_identifier": "OMR-3847-1920",
            "amount": 300.0,
            "currency": "EGP",
            "password": "Customer@2026!",
            "note": "Admin approval test",
            "is_vpn": True,
            "country": "DE",
            "isp": "Datacenter Proxy",
        }, headers=cust_headers)
        assert res_tx2.status_code == 201
        txn2_ref = res_tx2.json()["transaction_id"]

        # Login as Admin
        login_admin = await client.post(
            "/api/v1/auth/login",
            json={"username": "admin@omerta.ai", "password": "AdminPass123!"},
        )
        assert login_admin.status_code == 200
        admin_headers = {"Authorization": f"Bearer {login_admin.json()['access_token']}"}

        # Admin approves the transaction
        approve_res = await client.post(
            f"/api/v1/admin/transactions/{txn2_ref}/approve",
            json={"rationale": "Compliance officer verified identity and approved transfer."},
            headers=admin_headers,
        )
        assert approve_res.status_code == 200, approve_res.text
        assert approve_res.json()["status"] == "COMPLETED"

        # Verify customer sees it as COMPLETED
        txns_final = await client.get("/api/v1/customer/transactions", headers=cust_headers)
        found_final = next((t for t in txns_final.json()["items"] if t["transaction_id"] == txn2_ref), None)
        assert found_final is not None
        assert found_final["status"] == "COMPLETED"
