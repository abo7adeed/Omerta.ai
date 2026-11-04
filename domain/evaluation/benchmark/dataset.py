"""Standardized and versioned benchmark dataset for Omerta.ai side-by-side LLM evaluation.

Contains 7 canonical, reproducible test cases covering clean, suspicious,
trap, incomplete evidence, schema-stress, and regression scenarios.
All identifiers and transaction payloads are synthetic.
"""

from typing import Any
from pydantic import BaseModel, Field


class BenchmarkCase(BaseModel):
    """Specification of an individual benchmark test case."""

    case_id: str
    scenario_type: str  # CLEAN | SUSPICIOUS | UNSUPPORTED_TRAP | INCOMPLETE_EVIDENCE | SCHEMA_STRESS | REGRESSION
    title: str
    description: str
    task_description: str
    investigation_id: str
    transaction_id: str
    account_id: str

    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    ground_truth: dict[str, Any] = Field(
        default_factory=dict,
        description="Expected attributes: expected_risk_level, expected_action, requires_human_review, known_traps, etc.",
    )

    def to_agent_state(self) -> dict[str, Any]:
        """Convert case into standard agent state dictionary format expected by investigator prompts."""
        return {
            "investigation_id": self.investigation_id,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "transaction": self.context.get("transaction", {}),
            "risk_score": self.context.get("risk_score", {}),
            "shared_devices": self.context.get("shared_devices", {}),
            "shared_ips": self.context.get("shared_ips", {}),
            "fraud_ring_signals": self.context.get("fraud_ring_signals", {}),
            "knowledge_results": self.context.get("knowledge_results", {}),
            "evidence": self.evidence,
        }


def get_benchmark_dataset(version: str = "1.0") -> list[BenchmarkCase]:
    """Return the canonical suite of versioned benchmark cases."""
    cases: list[BenchmarkCase] = []

    # -------------------------------------------------------------------------
    # Case 1: Clean Commercial Payment (Complete, Verified Evidence)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-01-CLEAN-COMPLETE",
            scenario_type="CLEAN",
            title="Clean Commercial Supplier Payment",
            description="Established corporate account paying a verified recurring supplier with matched invoice.",
            task_description="Investigate routine vendor disbursement TXN-CLN-101 from ACC-CORP-501.",
            investigation_id="INV-CLN-2026-001",
            transaction_id="TXN-CLN-101",
            account_id="ACC-CORP-501",
            context={
                "transaction": {
                    "transaction_id": "TXN-CLN-101",
                    "amount": "4250.00",
                    "currency": "USD",
                    "transaction_type": "ACH_OUT",
                    "is_new_device": False,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-CORP-501", "name": "Apex Manufacturing Ltd"},
                    "recipient": {"external_id": "ACC-VEND-902", "name": "Industrial Logistics Inc"},
                },
                "risk_score": {"risk_score": 0.08, "risk_level": "LOW", "source": "ML"},
                "shared_devices": {"shared_devices": []},
                "shared_ips": {"shared_ips": []},
                "fraud_ring_signals": {"signals": []},
            },
            evidence=[
                {
                    "evidence_id": "EV-CLN-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-CLN-101",
                    "description": "Routine ACH debit of $4,250.00 to regular vendor ACC-VEND-902.",
                    "data": {"amount": "4250.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-CLN-02",
                    "category": "DEVICE",
                    "source": "device",
                    "reference": "DEV-CORP-01",
                    "description": "Authorized corporate office workstation, authenticated for 24 months.",
                    "data": {"device_id": "DEV-CORP-01", "is_new": False},
                },
                {
                    "evidence_id": "EV-CLN-03",
                    "category": "DOCUMENT",
                    "source": "erp_invoice",
                    "reference": "INV-PO-98211",
                    "description": "Valid purchase order and bill of lading for industrial components.",
                    "data": {"matched_po": "PO-98211", "amount": "4250.00"},
                },
            ],
            ground_truth={
                "expected_risk_level": "LOW",
                "expected_action": "CLOSE_NO_ACTION",
                "requires_human_review": False,
                "deliberate_errors": False,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 2: Suspicious Rapid Mule Pass-Through with Corroborating Signals
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-02-SUSPICIOUS-CORROBORATED",
            scenario_type="SUSPICIOUS",
            title="Suspicious Mule Wire with Shared Device Ring",
            description="High-value rapid pass-through wire from a new device topologically linked to 4 distinct accounts.",
            task_description="Investigate high-velocity outbound wire TXN-MULE-202 from ACC-MULE-101.",
            investigation_id="INV-MULE-2026-002",
            transaction_id="TXN-MULE-202",
            account_id="ACC-MULE-101",
            context={
                "transaction": {
                    "transaction_id": "TXN-MULE-202",
                    "amount": "9850.00",
                    "currency": "USD",
                    "transaction_type": "WIRE_OUT",
                    "is_new_device": True,
                    "is_new_ip": True,
                    "sender": {"external_id": "ACC-MULE-101"},
                    "recipient": {"external_id": "ACC-OFFSHORE-999"},
                },
                "risk_score": {"risk_score": 0.92, "risk_level": "HIGH", "source": "ML"},
                "shared_devices": {
                    "shared_devices": [{"device_id": "DEV-SYNTH-99", "account_count": 4}]
                },
                "shared_ips": {
                    "shared_ips": [{"ip_address": "198.51.100.44", "account_count": 5}]
                },
                "fraud_ring_signals": {
                    "signals": [
                        {"type": "PASS_THROUGH", "entity_id": "ACC-MULE-101", "confidence": 0.88},
                        {"type": "SHARED_DEVICE", "entity_id": "DEV-SYNTH-99", "confidence": 0.95},
                    ]
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-MULE-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-MULE-202",
                    "description": "Outbound international wire of $9,850.00 immediately following a deposit.",
                    "data": {"amount": "9850.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-MULE-02",
                    "category": "DEVICE",
                    "source": "device",
                    "reference": "DEV-SYNTH-99",
                    "description": "Device DEV-SYNTH-99 registered 8 minutes prior to high-value wire execution.",
                    "data": {"device_id": "DEV-SYNTH-99", "is_new": True},
                },
                {
                    "evidence_id": "EV-MULE-03",
                    "category": "GRAPH",
                    "source": "graph",
                    "reference": "DEV-SYNTH-99",
                    "description": "Graph community analysis reveals DEV-SYNTH-99 links 4 accounts in a ring.",
                    "data": {"device_id": "DEV-SYNTH-99", "linked_accounts": 4},
                },
            ],
            ground_truth={
                "expected_risk_level": "HIGH",
                "expected_action": "HUMAN_REVIEW",
                "requires_human_review": True,
                "typologies": ["MULE_ACCOUNT", "NEW_DEVICE_ABUSE"],
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 3: Unsupported Claims Trap (Hallucination Sensitivity Test)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-03-UNSUPPORTED-CLAIMS-TRAP",
            scenario_type="UNSUPPORTED_TRAP",
            title="Commercial Transfer with Decoy Counterparty Trap",
            description="Moderate transaction where unsupported allegations of sanctions or narcotics trade are tempting but completely absent from evidence.",
            task_description="Evaluate transfer TXN-TRAP-303 from ACC-RETAIL-404 without making unverified assertions.",
            investigation_id="INV-TRAP-2026-003",
            transaction_id="TXN-TRAP-303",
            account_id="ACC-RETAIL-404",
            context={
                "transaction": {
                    "transaction_id": "TXN-TRAP-303",
                    "amount": "12500.00",
                    "currency": "USD",
                    "transaction_type": "DOMESTIC_TRANSFER",
                    "is_new_device": False,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-RETAIL-404"},
                    "recipient": {"external_id": "ACC-MED-505"},
                },
                "risk_score": {"risk_score": 0.35, "risk_level": "MEDIUM", "source": "ML"},
                "shared_devices": {"shared_devices": []},
                "shared_ips": {"shared_ips": []},
                "fraud_ring_signals": {"signals": []},
            },
            evidence=[
                {
                    "evidence_id": "EV-TRAP-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-TRAP-303",
                    "description": "Domestic business wire of $12,500.00 to medical equipment distributor.",
                    "data": {"amount": "12500.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-TRAP-02",
                    "category": "ACCOUNT",
                    "source": "kyc",
                    "reference": "ACC-MED-505",
                    "description": "Medical supply vendor established in 2019, active licenses verified.",
                    "data": {"kyc_verified": True},
                },
            ],
            ground_truth={
                "expected_risk_level": "LOW",
                "expected_action": "CLOSE_NO_ACTION",
                "requires_human_review": False,
                "hallucination_trap": "Candidate must NOT allege sanctioned jurisdictions or darknet activity.",
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 4: Incomplete Evidence (Missing Counterparty Clearing Trail)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-04-INCOMPLETE-EVIDENCE",
            scenario_type="INCOMPLETE_EVIDENCE",
            title="Cross-Border Wire with Incomplete Intermediary Records",
            description="International transfer where beneficiary bank routing failed to return full clearing data.",
            task_description="Investigate cross-border wire TXN-INC-404 where intermediary clearing data is missing.",
            investigation_id="INV-INC-2026-004",
            transaction_id="TXN-INC-404",
            account_id="ACC-IMP-606",
            context={
                "transaction": {
                    "transaction_id": "TXN-INC-404",
                    "amount": "7400.00",
                    "currency": "EUR",
                    "transaction_type": "CROSS_BORDER_WIRE",
                    "is_new_device": False,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-IMP-606"},
                    "recipient": {"external_id": "ACC-UNKNOWN-707"},
                },
                "risk_score": {"risk_score": 0.45, "risk_level": "MEDIUM", "source": "ML"},
                "shared_devices": {"shared_devices": []},
                "shared_ips": {"shared_ips": []},
                "fraud_ring_signals": {"signals": []},
            },
            evidence=[
                {
                    "evidence_id": "EV-INC-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-INC-404",
                    "description": "Cross-border outbound wire of 7,400.00 EUR to intermediary bank.",
                    "data": {"amount": "7400.00", "currency": "EUR"},
                },
                {
                    "evidence_id": "EV-INC-02",
                    "category": "SYSTEM",
                    "source": "swift_gateway",
                    "reference": "MSG-SWIFT-991",
                    "description": "Beneficiary clearing status: PENDING_CORRESPONDENT_RESPONSE. Counterparty identity unverified.",
                    "data": {"status": "INCOMPLETE_CORRESPONDENT_DATA"},
                },
            ],
            ground_truth={
                "expected_risk_level": "MEDIUM",
                "expected_action": "REQUEST_CUSTOMER_INFO",
                "requires_human_review": True,
                "evidence_gap_expected": True,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 5: Regression Case INV-SAR-2026-001 (Suspicious Structuring Pattern)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-05-REGRESSION-SAR-001",
            scenario_type="REGRESSION",
            title="Regression Test: INV-SAR-2026-001 (Smurfing Sequence)",
            description="Replicates original regression case with repeated structured deposits under threshold followed by wire.",
            task_description="Evaluate suspicious structuring alert INV-SAR-2026-001 on account ACC-SAR-101.",
            investigation_id="INV-SAR-2026-001",
            transaction_id="TXN-SAR-001",
            account_id="ACC-SAR-101",
            context={
                "transaction": {
                    "transaction_id": "TXN-SAR-001",
                    "amount": "9900.00",
                    "currency": "USD",
                    "transaction_type": "WIRE_OUT",
                    "is_new_device": True,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-SAR-101"},
                    "recipient": {"external_id": "ACC-SAR-BENEFICIARY"},
                },
                "risk_score": {"risk_score": 0.85, "risk_level": "HIGH", "source": "ML"},
                "shared_devices": {
                    "shared_devices": [{"device_id": "DEV-SAR-01", "account_count": 3}]
                },
                "shared_ips": {"shared_ips": []},
                "fraud_ring_signals": {
                    "signals": [{"type": "SMURFING", "entity_id": "ACC-SAR-101", "confidence": 0.82}]
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-SAR-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SAR-001",
                    "description": "Wire transfer of $9,900.00, just below the $10,000 regulatory reporting threshold.",
                    "data": {"amount": "9900.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-SAR-02",
                    "category": "GRAPH",
                    "source": "graph",
                    "reference": "DEV-SAR-01",
                    "description": "Device DEV-SAR-01 linked to 3 accounts with concurrent cash deposits.",
                    "data": {"device_id": "DEV-SAR-01", "account_count": 3},
                },
            ],
            ground_truth={
                "expected_risk_level": "HIGH",
                "expected_action": "ESCALATE_TO_FIU",
                "requires_human_review": True,
                "typologies": ["SMURFING", "MULE_ACCOUNT"],
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 6: Regression Case INV-CLEAN-2026-002 (Verified Commercial Payroll)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-06-REGRESSION-CLEAN-002",
            scenario_type="REGRESSION",
            title="Regression Test: INV-CLEAN-2026-002 (Routine Payroll Batch)",
            description="Replicates original regression case for verified biometric corporate payroll disbursement.",
            task_description="Review scheduled payroll disbursement INV-CLEAN-2026-002 from ACC-CORP-202.",
            investigation_id="INV-CLEAN-2026-002",
            transaction_id="TXN-PAYROLL-002",
            account_id="ACC-CORP-202",
            context={
                "transaction": {
                    "transaction_id": "TXN-PAYROLL-002",
                    "amount": "18450.00",
                    "currency": "USD",
                    "transaction_type": "PAYROLL_BATCH",
                    "is_new_device": False,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-CORP-202"},
                    "recipient": {"external_id": "ACC-PAYROLL-PROCESSOR"},
                },
                "risk_score": {"risk_score": 0.04, "risk_level": "LOW", "source": "ML"},
                "shared_devices": {"shared_devices": []},
                "shared_ips": {"shared_ips": []},
                "fraud_ring_signals": {"signals": []},
            },
            evidence=[
                {
                    "evidence_id": "EV-CLN-10",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-PAYROLL-002",
                    "description": "Monthly payroll disbursement of $18,450.00 to 12 verified employee accounts.",
                    "data": {"amount": "18450.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-CLN-11",
                    "category": "AUTHENTICATION",
                    "source": "sso_audit",
                    "reference": "AUTH-BIO-882",
                    "description": "Dual-authorization biometric confirmation completed by CFO and HR Controller.",
                    "data": {"mfa_verified": True},
                },
            ],
            ground_truth={
                "expected_risk_level": "LOW",
                "expected_action": "CLOSE_NO_ACTION",
                "requires_human_review": False,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Case 7: Strict Schema Stress Test (Summary Enforcement & Citation Bounds)
    # -------------------------------------------------------------------------
    cases.append(
        BenchmarkCase(
            case_id="CASE-07-SCHEMA-STRESS",
            scenario_type="SCHEMA_STRESS",
            title="Complex Multi-Jurisdiction Layering (Schema Stress)",
            description="Complex multi-leg transaction demanding exact InvestigationReport schema conformance with mandatory summary and citations.",
            task_description="Analyze complex multi-hop transfer TXN-LAYER-707 and produce strictly valid InvestigationReport JSON.",
            investigation_id="INV-LAYER-2026-007",
            transaction_id="TXN-LAYER-707",
            account_id="ACC-HOLDING-707",
            context={
                "transaction": {
                    "transaction_id": "TXN-LAYER-707",
                    "amount": "49500.00",
                    "currency": "EUR",
                    "transaction_type": "WIRE_OUT",
                    "is_new_device": True,
                    "is_new_ip": True,
                    "sender": {"external_id": "ACC-HOLDING-707"},
                    "recipient": {"external_id": "ACC-SHELL-909"},
                },
                "risk_score": {"risk_score": 0.81, "risk_level": "HIGH", "source": "ML"},
                "shared_devices": {
                    "shared_devices": [{"device_id": "DEV-ANON-77", "account_count": 6}]
                },
                "shared_ips": {
                    "shared_ips": [{"ip_address": "203.0.113.88", "account_count": 8}]
                },
                "fraud_ring_signals": {
                    "signals": [{"type": "LAYERING", "entity_id": "ACC-HOLDING-707", "confidence": 0.85}]
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-LAYER-01",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-LAYER-707",
                    "description": "Wire transfer of 49,500.00 EUR to offshore shell account ACC-SHELL-909.",
                    "data": {"amount": "49500.00", "currency": "EUR"},
                },
                {
                    "evidence_id": "EV-LAYER-02",
                    "category": "GRAPH",
                    "source": "graph",
                    "reference": "DEV-ANON-77",
                    "description": "High centrality node DEV-ANON-77 connected to 6 distinct entity accounts across 3 jurisdictions.",
                    "data": {"device_id": "DEV-ANON-77", "connected_nodes": 6},
                },
                {
                    "evidence_id": "EV-LAYER-03",
                    "category": "RISK",
                    "source": "rules_engine",
                    "reference": "RULE-HIGH-RISK-SHELL",
                    "description": "Counterparty jurisdiction flagged on FATF increased monitoring watchlist.",
                    "data": {"jurisdiction": "FATF_GREY_LIST"},
                },
            ],
            ground_truth={
                "expected_risk_level": "HIGH",
                "expected_action": "ESCALATE_TO_FIU",
                "requires_human_review": True,
                "typologies": ["LAYERING", "MULE_ACCOUNT"],
            },
        )
    )

    return cases

