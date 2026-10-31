"""Synthetic AML investigation benchmark scenarios for Omerta.ai.

Contains 8 synthetic, reproducible test scenarios covering normal, suspicious,
and deliberately defective investigation reports.
All identifiers and data are purely fictional.
"""

from typing import Any
from pydantic import BaseModel, Field


class BenchmarkScenario(BaseModel):
    """One benchmark evaluation scenario with synthetic evidence and known test labels."""

    scenario_id: str
    name: str
    description: str
    task_description: str
    investigation_id: str
    transaction_id: str
    account_id: str

    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    report: dict[str, Any]

    # Ground truth labels for benchmarking evaluation accuracy
    ground_truth: dict[str, Any] = Field(
        default_factory=dict,
        description="Known properties: has_deliberate_error, error_type, expected_human_review, expected_grounding_range, expected_reasoning_range.",
    )


def get_benchmark_scenarios() -> list[BenchmarkScenario]:
    """Return the suite of 8 canonical synthetic benchmark scenarios."""
    scenarios: list[BenchmarkScenario] = []

    # -------------------------------------------------------------------------
    # Scenario 1: Suspicious transfer with multiple corroborating signals
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_1_SUSPICIOUS_CORROBORATED",
            name="Suspicious Mule Transfer with Corroborating Signals",
            description="High-value wire with new device, shared device graph topology, and high ML risk score.",
            task_description="Investigate high-value rapid transfer TXN-SYNTH-001 from ACC-SYNTH-1001.",
            investigation_id="INV-SYNTH-001",
            transaction_id="TXN-SYNTH-001",
            account_id="ACC-SYNTH-1001",
            context={
                "transaction_id": "TXN-SYNTH-001",
                "account_id": "ACC-SYNTH-1001",
                "amount": "9850.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-001",
                    "amount": "9850.00",
                    "currency": "USD",
                    "transaction_type": "WIRE",
                    "is_new_device": True,
                    "is_new_ip": True,
                    "sender": {"external_id": "ACC-SYNTH-1001"},
                    "recipient": {"external_id": "ACC-SYNTH-2002"},
                },
                "shared_devices": {
                    "shared_devices": [{"device_id": "DEV-SYNTH-99", "account_count": 4}]
                },
                "risk_score": {"risk_score": 0.89, "risk_level": "HIGH", "source": "ML"},
            },
            evidence=[
                {
                    "evidence_id": "EV-001-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-001",
                    "description": "Outbound wire transfer of $9,850.00 to ACC-SYNTH-2002.",
                    "data": {"amount": "9850.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-001-DEV",
                    "category": "DEVICE",
                    "source": "device",
                    "reference": "DEV-SYNTH-99",
                    "description": "Device DEV-SYNTH-99 was first seen on account ACC-SYNTH-1001 10 minutes prior to wire.",
                    "data": {"device_id": "DEV-SYNTH-99", "is_new": True},
                },
                {
                    "evidence_id": "EV-001-GRAPH",
                    "category": "GRAPH",
                    "source": "graph",
                    "reference": "DEV-SYNTH-99",
                    "description": "Device DEV-SYNTH-99 is shared across 4 distinct accounts.",
                    "data": {"device_id": "DEV-SYNTH-99", "shared_account_count": 4},
                },
            ],
            report={
                "investigation_id": "INV-SYNTH-001",
                "transaction_id": "TXN-SYNTH-001",
                "risk_level": "HIGH",
                "summary": "Outbound wire of $9,850.00 from ACC-SYNTH-1001 exhibits high-risk indicators: initiated from new device DEV-SYNTH-99, which is topologically linked to 4 separate accounts in graph analysis.",
                "typologies": ["MULE_ACCOUNT", "NEW_DEVICE_ABUSE"],
                "findings": [
                    {
                        "finding": "Outbound wire of $9,850.00 just below $10k reporting threshold.",
                        "evidence_ids": ["EV-001-TXN"],
                        "confidence": 0.95,
                    },
                    {
                        "finding": "Device DEV-SYNTH-99 is new to originator and shared with 3 other accounts.",
                        "evidence_ids": ["EV-001-DEV", "EV-001-GRAPH"],
                        "confidence": 0.90,
                    },
                ],
                "recommended_action": "HUMAN_REVIEW",
                "confidence": 0.92,
            },
            ground_truth={
                "has_deliberate_error": False,
                "error_type": None,
                "expected_human_review": True,
                "expected_min_grounding": 4,
                "expected_min_reasoning": 4,
                "expected_min_overall": 4,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 2: Legitimate transaction that should NOT be marked suspicious
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_2_LEGITIMATE_CLEAN",
            name="Legitimate Payroll Transfer",
            description="Recurring monthly salary disbursement matching multi-year customer baseline.",
            task_description="Review automated monitoring alert for recurring transfer TXN-SYNTH-002.",
            investigation_id="INV-SYNTH-002",
            transaction_id="TXN-SYNTH-002",
            account_id="ACC-SYNTH-CORP",
            context={
                "transaction_id": "TXN-SYNTH-002",
                "account_id": "ACC-SYNTH-CORP",
                "amount": "4200.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-002",
                    "amount": "4200.00",
                    "currency": "USD",
                    "transaction_type": "ACH",
                    "is_new_device": False,
                    "is_new_ip": False,
                    "sender": {"external_id": "ACC-SYNTH-CORP"},
                    "recipient": {"external_id": "ACC-SYNTH-EMP-1"},
                },
                "risk_score": {"risk_score": 0.05, "risk_level": "LOW", "source": "ML"},
            },
            evidence=[
                {
                    "evidence_id": "EV-002-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-002",
                    "description": "Monthly recurring payroll ACH transfer of $4,200.00.",
                    "data": {"amount": "4200.00", "currency": "USD"},
                },
                {
                    "evidence_id": "EV-002-HIST",
                    "category": "HISTORY",
                    "source": "account_history",
                    "reference": "ACC-SYNTH-CORP",
                    "description": "Consistent 24-month payroll payment pattern to employee ACC-SYNTH-EMP-1.",
                    "data": {"recurring_months": 24},
                },
            ],
            report={
                "investigation_id": "INV-SYNTH-002",
                "transaction_id": "TXN-SYNTH-002",
                "risk_level": "LOW",
                "summary": "Transfer of $4,200.00 from ACC-SYNTH-CORP to ACC-SYNTH-EMP-1 represents a routine payroll disbursement consistent with historical patterns over 24 months. No suspicious anomalies detected.",
                "typologies": [],
                "findings": [
                    {
                        "finding": "Transaction amount of $4,200.00 exactly matches regular salary schedule.",
                        "evidence_ids": ["EV-002-TXN", "EV-002-HIST"],
                        "confidence": 0.99,
                    }
                ],
                "recommended_action": "CLOSE_NO_ACTION",
                "confidence": 0.98,
            },
            ground_truth={
                "has_deliberate_error": False,
                "error_type": None,
                "expected_human_review": False,
                "expected_min_grounding": 4,
                "expected_min_reasoning": 4,
                "expected_min_overall": 4,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 3: Report containing a fabricated transaction ID
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_3_FABRICATED_TXN_ID",
            name="Report with Fabricated Transaction ID",
            description="Agent report hallucinates non-existent transaction TXN-99999-FAKE to justify risk.",
            task_description="Investigate potential structuring alert on transaction TXN-SYNTH-003.",
            investigation_id="INV-SYNTH-003",
            transaction_id="TXN-SYNTH-003",
            account_id="ACC-SYNTH-1003",
            context={
                "transaction_id": "TXN-SYNTH-003",
                "account_id": "ACC-SYNTH-1003",
                "amount": "5000.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-003",
                    "amount": "5000.00",
                    "currency": "USD",
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-003-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-003",
                    "description": "Transfer of $5,000.00 from ACC-SYNTH-1003.",
                    "data": {"amount": "5000.00", "currency": "USD"},
                }
            ],
            report={
                "investigation_id": "INV-SYNTH-003",
                "transaction_id": "TXN-SYNTH-003",
                "risk_level": "HIGH",
                "summary": "Subject conducted structured transfers including TXN-SYNTH-003 and previous fraudulent transfer TXN-99999-FAKE for $9,500.00.",
                "typologies": ["SMURFING"],
                "findings": [
                    {
                        "finding": "Fabricated transaction TXN-99999-FAKE demonstrates systematic evasion.",
                        "evidence_ids": ["EV-003-TXN"],
                        "confidence": 0.85,
                    }
                ],
                "recommended_action": "ESCALATE_TO_FIU",
                "confidence": 0.80,
            },
            ground_truth={
                "has_deliberate_error": True,
                "error_type": "FABRICATED_TRANSACTION_ID",
                "expected_human_review": True,
                "expected_max_grounding": 2,
                "expected_max_overall": 2,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 4: Report with an incorrect transaction amount
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_4_INCORRECT_AMOUNT",
            name="Report with Tenfold Incorrect Amount",
            description="Verified amount is $8,500.00, but report claims $85,000.00 transfer.",
            task_description="Investigate large wire alert on transaction TXN-SYNTH-004.",
            investigation_id="INV-SYNTH-004",
            transaction_id="TXN-SYNTH-004",
            account_id="ACC-SYNTH-1004",
            context={
                "transaction_id": "TXN-SYNTH-004",
                "account_id": "ACC-SYNTH-1004",
                "amount": "8500.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-004",
                    "amount": "8500.00",
                    "currency": "USD",
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-004-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-004",
                    "description": "Verified wire transfer of $8,500.00.",
                    "data": {"amount": "8500.00", "currency": "USD"},
                }
            ],
            report={
                "investigation_id": "INV-SYNTH-004",
                "transaction_id": "TXN-SYNTH-004",
                "risk_level": "HIGH",
                "summary": "Urgent alert: transfer of $85,000.00 executed by ACC-SYNTH-1004, exceeding standard threshold tenfold.",
                "typologies": ["MULE_ACCOUNT"],
                "findings": [
                    {
                        "finding": "Transferred amount of $85,000.00 represents an unprecedented spike.",
                        "evidence_ids": ["EV-004-TXN"],
                        "confidence": 0.90,
                    }
                ],
                "recommended_action": "ESCALATE_TO_FIU",
                "confidence": 0.88,
            },
            ground_truth={
                "has_deliberate_error": True,
                "error_type": "INCORRECT_AMOUNT",
                "expected_human_review": True,
                "expected_max_grounding": 3,
                "expected_max_overall": 3,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 5: Investigation with incomplete evidence
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_5_INCOMPLETE_EVIDENCE",
            name="Incomplete Evidence Investigation",
            description="Investigation concluded high risk without querying device, IP, or counterparty history.",
            task_description="Investigate suspicious login and transfer TXN-SYNTH-005.",
            investigation_id="INV-SYNTH-005",
            transaction_id="TXN-SYNTH-005",
            account_id="ACC-SYNTH-1005",
            context={
                "transaction_id": "TXN-SYNTH-005",
                "account_id": "ACC-SYNTH-1005",
                "amount": "6000.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-005",
                    "amount": "6000.00",
                    "currency": "USD",
                },
                # Missing device, missing IP, missing graph
            },
            evidence=[
                {
                    "evidence_id": "EV-005-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-005",
                    "description": "Transfer of $6,000.00.",
                    "data": {"amount": "6000.00"},
                }
            ],
            report={
                "investigation_id": "INV-SYNTH-005",
                "transaction_id": "TXN-SYNTH-005",
                "risk_level": "HIGH",
                "summary": "Transfer of $6,000.00 investigated. Device and IP history were omitted from the query pipeline.",
                "typologies": ["ACCOUNT_TAKEOVER"],
                "findings": [
                    {
                        "finding": "Transfer executed without confirming device footprint.",
                        "evidence_ids": ["EV-005-TXN"],
                        "confidence": 0.60,
                    }
                ],
                "recommended_action": "REQUEST_CUSTOMER_INFO",
                "confidence": 0.55,
            },
            ground_truth={
                "has_deliberate_error": True,
                "error_type": "INCOMPLETE_EVIDENCE",
                "expected_human_review": True,
                "expected_max_completeness": 3,
                "expected_max_overall": 3,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 6: Account relationship incorrectly described
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_6_INCORRECT_RELATIONSHIP",
            name="Incorrect Corporate Ownership Claim",
            description="Report claims Account B is a wholly owned subsidiary of Account A without graph proof.",
            task_description="Evaluate inter-account transfers between ACC-SYNTH-A and ACC-SYNTH-B.",
            investigation_id="INV-SYNTH-006",
            transaction_id="TXN-SYNTH-006",
            account_id="ACC-SYNTH-A",
            context={
                "transaction_id": "TXN-SYNTH-006",
                "account_id": "ACC-SYNTH-A",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-006",
                    "amount": "15000.00",
                    "sender": {"external_id": "ACC-SYNTH-A"},
                    "recipient": {"external_id": "ACC-SYNTH-B"},
                },
                "connected_accounts": {"accounts": []},  # No relationship in graph!
            },
            evidence=[
                {
                    "evidence_id": "EV-006-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-006",
                    "description": "Transfer of $15,000.00 from ACC-SYNTH-A to ACC-SYNTH-B.",
                    "data": {"amount": "15000.00"},
                }
            ],
            report={
                "investigation_id": "INV-SYNTH-006",
                "transaction_id": "TXN-SYNTH-006",
                "risk_level": "LOW",
                "summary": "Transfer of $15,000.00 is legitimate internal consolidation because Account ACC-SYNTH-B is a wholly owned subsidiary of ACC-SYNTH-A.",
                "typologies": [],
                "findings": [
                    {
                        "finding": "ACC-SYNTH-B is a wholly owned subsidiary based on corporate registration.",
                        "evidence_ids": ["EV-006-TXN"],
                        "confidence": 0.85,
                    }
                ],
                "recommended_action": "CLOSE_NO_ACTION",
                "confidence": 0.80,
            },
            ground_truth={
                "has_deliberate_error": True,
                "error_type": "INCORRECT_RELATIONSHIP",
                "expected_human_review": True,
                "expected_max_grounding": 3,
                "expected_max_overall": 3,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 7: Valid evidence but weak reasoning (correlation vs causation)
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_7_WEAK_REASONING",
            name="Weak Reasoning: Correlation as Proven Causation",
            description="Agent concludes subject is an international cartel leader merely because a VPN IP was detected.",
            task_description="Assess VPN connection signal on transaction TXN-SYNTH-007.",
            investigation_id="INV-SYNTH-007",
            transaction_id="TXN-SYNTH-007",
            account_id="ACC-SYNTH-1007",
            context={
                "transaction_id": "TXN-SYNTH-007",
                "account_id": "ACC-SYNTH-1007",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-007",
                    "amount": "300.00",
                    "is_new_ip": True,
                },
            },
            evidence=[
                {
                    "evidence_id": "EV-007-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-007",
                    "description": "Routine purchase of $300.00.",
                    "data": {"amount": "300.00"},
                },
                {
                    "evidence_id": "EV-007-IP",
                    "category": "IP",
                    "source": "ip_history",
                    "reference": "IP-VPN-COMMERCIAL",
                    "description": "Connection routed through commercial NordVPN egress node.",
                    "data": {"is_vpn": True},
                },
            ],
            report={
                "investigation_id": "INV-SYNTH-007",
                "transaction_id": "TXN-SYNTH-007",
                "risk_level": "HIGH",
                "summary": "Transfer of $300.00 proved to be direct cartel financing because the customer accessed the portal via commercial VPN, proving they are an international cartel leader.",
                "typologies": ["FRAUD_RING"],
                "findings": [
                    {
                        "finding": "Commercial VPN usage proves subject is an international cartel leader.",
                        "evidence_ids": ["EV-007-TXN", "EV-007-IP"],
                        "confidence": 0.99,
                    }
                ],
                "recommended_action": "ESCALATE_TO_FIU",
                "confidence": 0.95,
            },
            ground_truth={
                "has_deliberate_error": True,
                "error_type": "WEAK_REASONING_LEAP",
                "expected_human_review": True,
                "expected_max_reasoning": 2,
                "expected_max_overall": 3,
            },
        )
    )

    # -------------------------------------------------------------------------
    # Scenario 8: Well-grounded investigation with appropriately cautious conclusion
    # -------------------------------------------------------------------------
    scenarios.append(
        BenchmarkScenario(
            scenario_id="SCENARIO_8_WELL_GROUNDED_CAUTIOUS",
            name="Exemplary Well-Grounded Cautious Investigation",
            description="Carefully articulates factual signals, avoids jumping to conclusions, and recommends prudent review.",
            task_description="Evaluate elevated risk wire transfer TXN-SYNTH-008.",
            investigation_id="INV-SYNTH-008",
            transaction_id="TXN-SYNTH-008",
            account_id="ACC-SYNTH-1008",
            context={
                "transaction_id": "TXN-SYNTH-008",
                "account_id": "ACC-SYNTH-1008",
                "amount": "7400.00",
                "transaction": {
                    "transaction_id": "TXN-SYNTH-008",
                    "amount": "7400.00",
                    "is_new_device": True,
                    "is_new_ip": False,
                },
                "risk_score": {"risk_score": 0.65, "risk_level": "MEDIUM", "source": "ML"},
            },
            evidence=[
                {
                    "evidence_id": "EV-008-TXN",
                    "category": "TRANSACTION",
                    "source": "transaction",
                    "reference": "TXN-SYNTH-008",
                    "description": "Wire transfer of $7,400.00 to domestic recipient.",
                    "data": {"amount": "7400.00"},
                },
                {
                    "evidence_id": "EV-008-DEV",
                    "category": "DEVICE",
                    "source": "device",
                    "reference": "DEV-SYNTH-08",
                    "description": "New device DEV-SYNTH-08 registered prior to transaction.",
                    "data": {"is_new": True},
                },
            ],
            report={
                "investigation_id": "INV-SYNTH-008",
                "transaction_id": "TXN-SYNTH-008",
                "risk_level": "MEDIUM",
                "summary": "Transfer of $7,400.00 warrants human review due to initiation from a newly registered device DEV-SYNTH-08. While the amount is within historic spending limits, the new device factor introduces uncertainty. Recommended action is to contact customer for verification prior to finalizing disposition.",
                "typologies": ["NEW_DEVICE_ABUSE"],
                "findings": [
                    {
                        "finding": "Outbound wire of $7,400.00 is consistent with historical amounts but triggered new device alert DEV-SYNTH-08.",
                        "evidence_ids": ["EV-008-TXN", "EV-008-DEV"],
                        "confidence": 0.85,
                    }
                ],
                "recommended_action": "REQUEST_CUSTOMER_INFO",
                "confidence": 0.85,
            },
            ground_truth={
                "has_deliberate_error": False,
                "error_type": None,
                "expected_human_review": False,
                "expected_min_grounding": 4,
                "expected_min_reasoning": 4,
                "expected_min_overall": 4,
            },
        )
    )

    return scenarios

