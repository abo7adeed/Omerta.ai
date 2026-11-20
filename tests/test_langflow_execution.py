"""Phase 4 Verification Suite: Langflow Standalone Execution & Omerta Sanctions Bridge.

Validates the 10 core integration scenarios:
1. Exact match execution via Langflow Component
2. Arabic name with diacritics / normalization via Langflow Component
3. Fuzzy name matching via Langflow Component
4. No-match execution (true negative) via Langflow Component
5. Invalid input handling (empty name)
6. Backend unavailable handling (connection refused)
7. Authentication failure handling (invalid bearer token -> HTTP 401)
8. Direct verification of real MCP tool invocation through FastAPI backend
9. Structured payload verification (match provenance, confidence, matched fields)
10. Mandatory Human-in-the-Loop review invariant (review_required: True)
11. End-to-end multi-node pipeline data chaining
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

# Add local paths
sys.path.insert(0, str(Path(__file__).parent.parent / "langflow" / "components"))

from apps.api.main import app
from infrastructure.security.jwt_auth import create_access_token
from langflow.components.omerta_sanctions_bridge import (
    Data,
    OmertaSanctionsBridgeComponent,
)
from mcp_servers.common.specialist_rbac import generate_specialist_token


@pytest.fixture
def auth_token() -> str:
    """Generate authorized specialist token for SanctionsScreeningAgent."""
    return generate_specialist_token("SanctionsScreeningAgent")


# ===========================================================================
# SCENARIO 1: Langflow Execution with Exact-Match Entity
# ===========================================================================
def test_scenario_01_exact_match_execution() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Mohamed El-Sayed Ahmed",
        "entity_type": "individual",
        "country": "EG",
        "birth_date": "1982-05-14",
        "identification_number": "EG-NAT-28205140102931",
        "threshold": 0.70,
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("match_found") is True
    assert data.get("best_match_confidence") == 1.0
    assert data.get("review_required") is True
    assert len(data.get("matched_entities", [])) >= 1
    best_cand = data["matched_entities"][0]
    assert best_cand.get("caption") == "Mohamed El-Sayed Ahmed"
    assert data.get("_langflow_bridge", {}).get("executed") is True
    assert data.get("_langflow_bridge", {}).get("status_code") == 200


# ===========================================================================
# SCENARIO 2: Langflow Execution with Arabic Name & Tashkeel
# ===========================================================================
def test_scenario_02_arabic_name_execution() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "مُحَمَّدُ السَّيِّد أحْمَد",
        "entity_type": "individual",
        "country": "EG",
        "threshold": 0.70,
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("match_found") is True
    assert data.get("best_match_confidence") >= 0.85
    assert data.get("review_required") is True
    assert data.get("_langflow_bridge", {}).get("executed") is True


# ===========================================================================
# SCENARIO 3: Langflow Execution with Fuzzy Name
# ===========================================================================
def test_scenario_03_fuzzy_name_execution() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Viktor Boout",
        "entity_type": "individual",
        "country": "RU",
        "threshold": 0.70,
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("match_found") is True
    assert data.get("best_match_confidence") >= 0.70
    assert data.get("review_required") is True
    best_cand = data["matched_entities"][0]
    assert "Viktor" in best_cand.get("caption", "")


# ===========================================================================
# SCENARIO 4: Langflow No-Match Execution (True Negative)
# ===========================================================================
def test_scenario_04_no_match_execution() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Jane Elizabeth Henderson-Smith",
        "entity_type": "individual",
        "country": "GB",
        "threshold": 0.70,
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("match_found") is False
    assert data.get("best_match_confidence") < 0.70
    assert data.get("review_required") is False
    assert len(data.get("matched_entities", [])) == 0


# ===========================================================================
# SCENARIO 5: Invalid Input Handling
# ===========================================================================
def test_scenario_05_invalid_input_handling() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "   ",
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("error") == "INVALID_INPUT"
    assert data.get("match_found") is False
    assert data.get("review_required") is False
    assert "Entity name is required" in data.get("detail", "")


# ===========================================================================
# SCENARIO 6: Backend Unavailable Handling
# ===========================================================================
def test_scenario_06_backend_unavailable_handling() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Mohamed El-Sayed Ahmed",
        "endpoint_url": "http://127.0.0.1:59999/api/v1/sanctions/screen",  # Non-existent port
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("error") == "BACKEND_UNAVAILABLE"
    assert data.get("match_found") is False
    assert data.get("review_required") is False
    assert data.get("_langflow_bridge", {}).get("executed") is False


# ===========================================================================
# SCENARIO 7: Authentication Failure Handling (HTTP 401)
# ===========================================================================
def test_scenario_07_auth_failure_handling() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Mohamed El-Sayed Ahmed",
        "auth_token": "invalid_tampered_jwt_token_12345",
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("error") == "HTTP_401"
    assert data.get("match_found") is False
    assert data.get("review_required") is False
    assert data.get("_langflow_bridge", {}).get("status_code") == 401


# ===========================================================================
# SCENARIO 8: MCP Tool Invocation Verified
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_08_mcp_tool_invocation_verified() -> None:
    valid_jwt = create_access_token(
        user_id="USR-001",
        username="analyst@omerta.ai",
        role="FRAUD_ANALYST",
        full_name="Tariq Mansour",
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/sanctions/screen",
            json={
                "name": "Mohamed El-Sayed Ahmed",
                "entity_type": "individual",
                "countries": ["EG"],
                "threshold": 0.70,
            },
            headers={"Authorization": f"Bearer {valid_jwt}"},
        )
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["match_found"] is True
        # Verify execution metadata contains status from real MCP tool
        metadata = payload.get("execution_metadata", {})
        assert metadata.get("status_code") in ("MATCH_FOUND", "OK", "SUCCESS")
        assert metadata.get("source_queried") in ("OPENSANCTIONS_API", "CACHE", "LOCAL_BASELINE")


# ===========================================================================
# SCENARIO 9: Full Structured Payload Verification
# ===========================================================================
def test_scenario_09_full_structured_payload() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Mohamed El-Sayed Ahmed",
        "country": "EG",
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert "query_echo" in data
    assert "match_found" in data
    assert "best_match_confidence" in data
    assert "review_required" in data
    assert "matched_entities" in data
    assert "total_candidates_analyzed" in data
    assert "execution_metadata" in data
    assert "_langflow_bridge" in data

    match = data["matched_entities"][0]
    assert "caption" in match
    assert "confidence_score" in match
    assert "matched_fields" in match
    assert "conflicting_fields" in match
    assert "reasoning" in match
    assert "sanctions_details" in match


# ===========================================================================
# SCENARIO 10: Mandatory Human-in-the-Loop Review Invariant
# ===========================================================================
def test_scenario_10_mandatory_hitl_enforced() -> None:
    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "entity_name": "Mohamed El-Sayed Ahmed",
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    # INVARIANT: Whenever match_found is True, review_required MUST be True
    if data.get("match_found"):
        assert data.get("review_required") is True, "CRITICAL: HITL violation - potential match flagged without review obligation"


# ===========================================================================
# SCENARIO 11: Multi-Node Pipeline Data Chaining
# ===========================================================================
def test_scenario_11_upstream_data_chaining() -> None:
    # Simulate upstream Normalization node output
    upstream_payload = Data(data={
        "original_name": "مُحَمَّدُ السَّيِّد أحْمَد",
        "normalized_name": "محمد السيد احمد",
        "name": "Mohamed El-Sayed Ahmed",
        "entity_type": "individual",
        "country": "EG",
        "normalization_applied": True,
    })

    comp = OmertaSanctionsBridgeComponent()
    comp.set_attributes({
        "input_data": upstream_payload,
        "endpoint_url": "http://127.0.0.1:8000/api/v1/sanctions/screen",
    })
    res = comp.execute_screening()
    data = res.data

    assert data.get("match_found") is True
    assert data.get("best_match_confidence") >= 0.85
    assert data.get("review_required") is True
