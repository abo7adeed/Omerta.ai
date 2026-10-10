"""Device Application Service for Omerta.ai.

Manages device intelligence, hardware fingerprinting, emulator risk flags, and account links.
"""

from typing import Any

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from infrastructure.database.models import (
    Account,
    Alert,
    Customer,
    Device,
    Session,
    Transaction,
)


def parse_device_telemetry(user_agent: str, platform: str = "", device_type: str = "") -> dict[str, str]:
    """Parse real browser, operating system, and hardware model from User-Agent string."""
    ua = (user_agent or "").lower()

    # Browser detection
    browser = "Web Browser"
    if "edg" in ua:
        browser = "Microsoft Edge"
    elif "firefox" in ua or "fxios" in ua:
        browser = "Mozilla Firefox"
    elif "chrome" in ua or "crios" in ua:
        browser = "Google Chrome"
    elif "safari" in ua and "chrome" not in ua:
        browser = "Apple Safari"
    elif "opera" in ua or "opr" in ua:
        browser = "Opera Browser"

    # OS & Model detection
    os_name = platform or "Desktop"
    model = "Workstation"

    if "iphone" in ua:
        os_name = "iOS"
        browser = "Mobile Safari" if browser == "Web Browser" else browser
        model = "Apple iPhone"
    elif "ipad" in ua:
        os_name = "iPadOS"
        model = "Apple iPad"
    elif "android" in ua:
        os_name = "Android"
        if "pixel" in ua:
            model = "Google Pixel"
        elif "sm-" in ua or "samsung" in ua:
            model = "Samsung Galaxy"
        else:
            model = "Android Smartphone"
    elif "macintosh" in ua or "mac os" in ua:
        os_name = "macOS"
        model = "Apple Mac Workstation"
    elif "windows" in ua:
        os_name = "Windows"
        model = "Windows PC Workstation"
    elif "linux" in ua or "x11" in ua:
        os_name = "Linux"
        model = "Linux Desktop Workstation"

    return {
        "browser": browser,
        "os_name": os_name,
        "model": model,
    }


class DeviceService:
    """Service layer for device intelligence and association tracking."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_devices(
        self,
        *,
        search: str | None = None,
        device_type: str | None = None,
        platform: str | None = None,
        risk_level: str | None = None,
        is_emulator: bool | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        """Paginated list of devices with real user names, browser info, and active session status."""
        query = select(Device).options(
            selectinload(Device.sessions).selectinload(Session.account),
            selectinload(Device.sessions).selectinload(Session.customer).selectinload(Customer.accounts),
            selectinload(Device.sessions).selectinload(Session.user),
            selectinload(Device.sessions).selectinload(Session.ip_address),
        )

        conditions = []
        if search:
            clean = f"%{search.strip()}%"
            conditions.append(
                or_(
                    Device.external_id.ilike(clean),
                    Device.platform.ilike(clean),
                    Device.user_agent.ilike(clean),
                )
            )
        if device_type:
            conditions.append(Device.device_type == device_type.upper())
        if platform:
            conditions.append(Device.platform == platform)
        if risk_level:
            conditions.append(Device.risk_level == risk_level.upper())
        if is_emulator is not None:
            conditions.append(Device.is_emulator == is_emulator)

        if conditions:
            query = query.where(*conditions)

        count_q = select(func.count(Device.id))
        if conditions:
            count_q = count_q.where(*conditions)
        total = await self.session.scalar(count_q) or 0

        offset = (max(1, page) - 1) * page_size
        query = query.order_by(Device.id.desc()).offset(offset).limit(page_size)

        devices = (await self.session.scalars(query)).all()

        dev_ids = [d.id for d in devices]
        dev_txns_map: dict[int, list[Transaction]] = {}
        if dev_ids:
            txns_query = (
                select(Transaction)
                .options(selectinload(Transaction.account), selectinload(Transaction.recipient_account))
                .where(Transaction.device_id.in_(dev_ids))
            )
            for t in (await self.session.scalars(txns_query)).all():
                if t.device_id not in dev_txns_map:
                    dev_txns_map[t.device_id] = []
                dev_txns_map[t.device_id].append(t)

        items = []
        for d in devices:
            unique_accs = {s.account.external_id for s in d.sessions if s.account}
            user_names = []
            user_roles = set()
            active_now = False
            last_ip = "127.0.0.1"
            last_location = "Egypt"
            is_vpn = False

            for s in d.sessions:
                if s.is_active:
                    active_now = True
                if s.account:
                    unique_accs.add(s.account.external_id)
                if s.customer:
                    user_names.append(s.customer.name)
                    if getattr(s.customer, "accounts", None):
                        for acc in s.customer.accounts:
                            unique_accs.add(acc.external_id)
                if s.user:
                    if s.user.full_name and s.user.full_name not in user_names:
                        user_names.append(s.user.full_name)
                    user_roles.add(s.user.role)
                if s.ip_address:
                    last_ip = s.ip_address.address
                    loc_country = s.ip_address.country or "EG"
                    last_location = "Cairo, Egypt" if loc_country.upper() in ("EG", "EGYPT") else f"{loc_country} Gateway"
                    if s.ip_address.is_vpn:
                        is_vpn = True

            txns_for_dev = dev_txns_map.get(d.id, [])
            for t in txns_for_dev:
                if t.account:
                    unique_accs.add(t.account.external_id)
                    if t.account.customer_name and t.account.customer_name not in user_names:
                        user_names.append(t.account.customer_name)
                if t.recipient_account:
                    unique_accs.add(t.recipient_account.external_id)

            acc_count = len(unique_accs)
            
            calculated_risk = d.risk_level or "LOW"
            if acc_count >= 3:
                calculated_risk = "CRITICAL"
            elif acc_count >= 2 or d.is_emulator or d.is_rooted or is_vpn:
                calculated_risk = "HIGH"

            telemetry = parse_device_telemetry(d.user_agent, d.platform, d.device_type)
            primary_user = user_names[0] if user_names else (f"User ({list(user_roles)[0]})" if user_roles else "System User")

            items.append({
                "id": d.id,
                "external_id": d.external_id,
                "device_id": d.external_id,
                "device_type": d.device_type,
                "platform": telemetry["os_name"] or d.platform,
                "browser": telemetry["browser"],
                "model": telemetry["model"],
                "user_agent": d.user_agent,
                "user_name": primary_user,
                "user_names": list(dict.fromkeys(user_names)),
                "user_roles": list(user_roles),
                "is_active_now": active_now,
                "is_emulator": d.is_emulator,
                "is_rooted": d.is_rooted,
                "risk_level": calculated_risk,
                "risk_score": 85 if calculated_risk == "CRITICAL" else (65 if calculated_risk == "HIGH" else 20),
                "session_count": len(d.sessions),
                "account_count": acc_count,
                "is_shared": acc_count > 1,
                "ip_address": last_ip,
                "location": last_location,
                "first_seen_at": d.first_seen_at.isoformat(),
                "last_seen_at": d.last_seen_at.isoformat(),
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 1,
        }

    async def get_device_detail(self, identifier: str) -> dict[str, Any] | None:
        """Fetch detail view of a device and associated accounts & transactions."""
        query = select(Device).options(
            selectinload(Device.sessions).selectinload(Session.account),
            selectinload(Device.sessions).selectinload(Session.customer).selectinload(Customer.accounts),
            selectinload(Device.sessions).selectinload(Session.user),
            selectinload(Device.sessions).selectinload(Session.ip_address),
        )

        if identifier.isdigit():
            query = query.where(or_(Device.id == int(identifier), Device.external_id == identifier))
        else:
            query = query.where(Device.external_id == identifier)

        device = await self.session.scalar(query)
        if not device:
            return None

        # Associated unique accounts and users
        associated_accounts = {}
        user_names = []
        user_roles = set()
        active_now = False
        last_ip = "127.0.0.1"
        last_location = "Cairo, Egypt"
        is_vpn = False

        for s in device.sessions:
            if s.is_active:
                active_now = True
            if s.customer:
                if s.customer.name not in user_names:
                    user_names.append(s.customer.name)
            if s.user:
                if s.user.full_name and s.user.full_name not in user_names:
                    user_names.append(s.user.full_name)
                user_roles.add(s.user.role)
            if s.ip_address:
                last_ip = s.ip_address.address
                loc_country = s.ip_address.country or "EG"
                last_location = "Cairo, Egypt" if loc_country.upper() in ("EG", "EGYPT") else f"{loc_country} Gateway"
                if s.ip_address.is_vpn:
                    is_vpn = True

            if s.account and s.account.external_id not in associated_accounts:
                associated_accounts[s.account.external_id] = {
                    "id": s.account.id,
                    "external_id": s.account.external_id,
                    "customer_name": s.account.customer_name,
                    "currency": s.account.currency,
                    "risk_level": s.account.risk_level,
                }
            elif s.customer and getattr(s.customer, "accounts", None):
                for acc in s.customer.accounts:
                    if acc.external_id not in associated_accounts:
                        associated_accounts[acc.external_id] = {
                            "id": acc.id,
                            "external_id": acc.external_id,
                            "customer_name": acc.customer_name or s.customer.name,
                            "currency": acc.currency,
                            "risk_level": acc.risk_level,
                        }

        calc_risk = device.risk_level or "LOW"
        if len(associated_accounts) >= 3:
            calc_risk = "CRITICAL"
        elif len(associated_accounts) >= 2 or device.is_emulator or device.is_rooted or is_vpn:
            calc_risk = "HIGH"

        telemetry = parse_device_telemetry(device.user_agent, device.platform, device.device_type)
        primary_user = user_names[0] if user_names else (f"User ({list(user_roles)[0]})" if user_roles else "System User")

        # Fetch recent transactions on this device
        txns_q = (
            select(Transaction)
            .options(selectinload(Transaction.recipient_account), selectinload(Transaction.account))
            .where(Transaction.device_id == device.id)
            .order_by(desc(Transaction.timestamp))
            .limit(10)
        )
        txns = (await self.session.scalars(txns_q)).all()

        for t in txns:
            if t.account and t.account.external_id not in associated_accounts:
                associated_accounts[t.account.external_id] = {
                    "id": t.account.id,
                    "external_id": t.account.external_id,
                    "customer_name": t.account.customer_name,
                    "currency": t.account.currency,
                    "balance": float(t.account.balance),
                    "account_type": t.account.account_type,
                    "risk_level": t.account.risk_level,
                }

        # If still no associated accounts directly on device, check linked session user customer accounts
        if not associated_accounts:
            for s in device.sessions:
                if s.user_id:
                    cust = await self.session.scalar(
                        select(Customer).options(selectinload(Customer.accounts)).where(Customer.user_id == s.user_id).limit(1)
                    )
                    if cust and cust.accounts:
                        for acc in cust.accounts:
                            associated_accounts[acc.external_id] = {
                                "id": acc.id,
                                "external_id": acc.external_id,
                                "customer_name": acc.customer_name or cust.name,
                                "currency": acc.currency,
                                "balance": float(acc.balance),
                                "account_type": acc.account_type,
                                "risk_level": acc.risk_level,
                            }

        # If no transactions tagged with device_id, load transactions from associated accounts
        if not txns and associated_accounts:
            acc_ids = [acc["id"] for acc in associated_accounts.values()]
            txns_fallback = (
                select(Transaction)
                .options(selectinload(Transaction.recipient_account), selectinload(Transaction.account))
                .where(or_(Transaction.account_id.in_(acc_ids), Transaction.recipient_account_id.in_(acc_ids)))
                .order_by(desc(Transaction.timestamp))
                .limit(8)
            )
            txns = (await self.session.scalars(txns_fallback)).all()

        device_dict = {
            "id": device.id,
            "external_id": device.external_id,
            "device_id": device.external_id,
            "device_type": device.device_type,
            "platform": telemetry["os_name"] or device.platform,
            "browser": telemetry["browser"],
            "model": telemetry["model"],
            "user_agent": device.user_agent,
            "user_name": primary_user,
            "user_names": user_names,
            "user_roles": list(user_roles),
            "is_active_now": active_now,
            "is_emulator": device.is_emulator,
            "is_rooted": device.is_rooted,
            "risk_level": calc_risk,
            "risk_score": 85 if calc_risk == "CRITICAL" else (65 if calc_risk == "HIGH" else 20),
            "ip_address": last_ip,
            "location": last_location,
            "screen_resolution": "1920×1080 (Full HD)" if "desktop" in device.device_type.lower() else "1170×2532 (Retina)",
            "first_seen_at": device.first_seen_at.isoformat(),
            "last_seen_at": device.last_seen_at.isoformat(),
        }

        return {
            **device_dict,
            "device": device_dict,
            "associated_accounts": list(associated_accounts.values()),
            "recent_sessions": [
                {
                    "id": s.id,
                    "external_id": s.external_id,
                    "customer": (s.customer.name if s.customer else (s.user.full_name if s.user else "N/A")),
                    "account": s.account.external_id if s.account else "N/A",
                    "ip_address": s.ip_address.address if s.ip_address else "127.0.0.1",
                    "country": s.ip_address.country if s.ip_address else "EG",
                    "is_vpn": s.is_vpn,
                    "is_active": s.is_active,
                    "started_at": s.started_at.isoformat(),
                }
                for s in device.sessions[:10]
            ],
            "recent_transactions": [
                {
                    "id": t.id,
                    "external_id": t.external_id,
                    "counterparty": (
                        t.recipient_account.customer_name
                        if t.recipient_account
                        else (t.account.customer_name if t.account else "Counterparty")
                    ),
                    "amount": float(t.amount),
                    "currency": t.currency,
                    "type": t.transaction_type,
                    "status": t.status,
                    "risk_score": float(t.risk_score) if t.risk_score is not None else 0.0,
                    "risk_level": t.risk_level,
                    "timestamp": t.timestamp.isoformat(),
                }
                for t in txns
            ],
        }


