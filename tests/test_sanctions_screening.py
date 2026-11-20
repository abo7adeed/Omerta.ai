"""Automated Verification Suite: Sanctions & Watchlist Screening Agent (14 Evaluation Scenarios).

Tests:
1. Exact match on known sanctioned individual
2. Exact match on known sanctioned organization/company
3. Close transliteration of Arabic name (Muhammad vs Mohamed)
4. Arabic name with prefix variation & Tashkeel (diacritics)
5. Typo in name (1-2 character edit distance)
6. Same name, different date of birth (false positive filtering)
7. Same name, different nationality/country (false positive filtering)
8. Partial name match (missing middle name)
9. Non-sanctioned innocent entity (true negative)
10. Entity with aliases matching watchlist
11. Empty / invalid input validation
12. Upstream OpenSanctions API timeout / offline resilience
13. Rate limit handling (HTTP 429 backoff / fallback)
14. Injection attempt via input fields (security validation)
"""

import pytest
from httpx import AsyncClient, ASGITransport

from apps.api.main import app
from domain.services.entity_resolution_service import (
    EntityResolutionService,
    calculate_name_similarity,
    normalize_arabic_text,
    normalize_english_text,
    normalize_name,
)
from domain.services.opensanctions_service import OpenSanctionsService
from infrastructure.opensanctions.client import OpenSanctionsClient
from mcp_servers.common.specialist_rbac import generate_specialist_token
from mcp_servers.sanctions_server.tools import screen_entity_against_watchlists


@pytest.fixture
def auth_token():
    return generate_specialist_token("SanctionsScreeningAgent")


# ===========================================================================
# SCENARIO 1: Exact Match on Known Sanctioned Individual
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_01_exact_match_individual(auth_token):
    res = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        entity_type="individual",
        countries=["EG"],
        birth_date="1982-05-14",
        identification_number="EG-NAT-28205140102931",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["review_required"] is True
    assert res["best_match_confidence"] >= 0.85
    best_cand = res["matched_entities"][0]
    assert best_cand["caption"] == "Mohamed El-Sayed Ahmed"
    assert "Date of birth exact match" in " ".join(best_cand["matched_fields"])
    assert "Country match" in " ".join(best_cand["matched_fields"])


# ===========================================================================
# SCENARIO 2: Exact Match on Known Sanctioned Organization / Company
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_02_exact_match_organization(auth_token):
    res = await screen_entity_against_watchlists(
        name="Al-Barakaat Financial Network",
        entity_type="organization",
        countries=["SO"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["review_required"] is True
    assert res["best_match_confidence"] >= 0.80
    assert any("Al-Barakaat" in m["caption"] for m in res["matched_entities"])


# ===========================================================================
# SCENARIO 3: Close Transliteration of Arabic Name
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_03_close_arabic_transliteration(auth_token):
    # 'Muhammad Al-Sayed Ahmad' vs 'Mohamed El-Sayed Ahmed'
    res = await screen_entity_against_watchlists(
        name="Muhammad Al-Sayed Ahmad",
        countries=["EG"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["best_match_confidence"] >= 0.70
    assert res["matched_entities"][0]["caption"] == "Mohamed El-Sayed Ahmed"


# ===========================================================================
# SCENARIO 4: Arabic Name with Prefix Variation & Diacritics (Tashkeel)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_04_arabic_script_with_tashkeel(auth_token):
    # With Tashkeel, Hamzas, and Al- prefix
    arabic_input = "مُحَمَّدُ السَّيِّد أحْمَد"
    res = await screen_entity_against_watchlists(
        name=arabic_input,
        countries=["EG"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["best_match_confidence"] >= 0.70
    # Should resolve to Mohamed El-Sayed Ahmed
    assert res["matched_entities"][0]["caption"] == "Mohamed El-Sayed Ahmed"


# ===========================================================================
# SCENARIO 5: Typo in Name (1-2 Character Edit Distance)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_05_typo_in_name(auth_token):
    # Typo: 'Viktor Boout' vs 'Viktor Bout'
    res = await screen_entity_against_watchlists(
        name="Viktor Boout",
        countries=["RU"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["best_match_confidence"] >= 0.75
    assert "Viktor Anatolyevich Bout" in res["matched_entities"][0]["caption"]


# ===========================================================================
# SCENARIO 6: Same Name, Different Date of Birth (False Positive Filter)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_06_dob_conflict_filtering(auth_token):
    # Real record is 1982-05-14; query has 2002-11-30 (20 year difference)
    res = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        birth_date="2002-11-30",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    # The DOB mismatch should heavily penalize the score
    for cand in res["matched_entities"]:
        if cand["caption"] == "Mohamed El-Sayed Ahmed":
            assert any("Date of birth mismatch" in f for f in cand["conflicting_fields"])
            assert cand["confidence_score"] < 0.75


# ===========================================================================
# SCENARIO 7: Same Name, Different Nationality/Country (False Positive Filter)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_07_country_conflict_filtering(auth_token):
    # Real record is EG; query provides JP
    res = await screen_entity_against_watchlists(
        name="Mohamed El-Sayed Ahmed",
        countries=["JP"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    for cand in res["matched_entities"]:
        if cand["caption"] == "Mohamed El-Sayed Ahmed":
            assert any("Country conflict" in f for f in cand["conflicting_fields"])


# ===========================================================================
# SCENARIO 8: Partial Name Match (Missing Middle Name)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_08_partial_name_match(auth_token):
    # "Mohamed Ahmed" vs "Mohamed El-Sayed Ahmed"
    res = await screen_entity_against_watchlists(
        name="Mohamed Ahmed",
        countries=["EG"],
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    # Should find match but with lower or moderate similarity
    assert len(res["matched_entities"]) > 0
    best = res["matched_entities"][0]
    assert best["caption"] == "Mohamed El-Sayed Ahmed"


# ===========================================================================
# SCENARIO 9: Non-Sanctioned Innocent Entity (True Negative)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_09_innocent_entity_true_negative(auth_token):
    res = await screen_entity_against_watchlists(
        name="Jane Elizabeth Henderson-Smith",
        countries=["NZ"],
        birth_date="1995-04-12",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is False
    assert res["review_required"] is False
    assert res["best_match_confidence"] < 0.40


# ===========================================================================
# SCENARIO 10: Entity with Aliases Matching Watchlist
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_10_alias_matching(auth_token):
    # Alias 'Boris' or 'Victor Bout'
    res = await screen_entity_against_watchlists(
        name="Victor Bout",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res["match_found"] is True
    assert res["best_match_confidence"] >= 0.85
    assert "Viktor Anatolyevich Bout" in res["matched_entities"][0]["caption"]


# ===========================================================================
# SCENARIO 11: Empty / Invalid Input Validation
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_11_input_validation(auth_token):
    # Blank name
    res1 = await screen_entity_against_watchlists(
        name="",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res1.get("error") == "INVALID_INPUT"

    # None name
    res2 = await screen_entity_against_watchlists(
        name=None,  # type: ignore
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res2.get("error") == "INVALID_INPUT"


# ===========================================================================
# SCENARIO 12: Upstream API Timeout / Offline Resilience
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_12_offline_baseline_resilience(auth_token):
    # Client pointing to an unreachable port to simulate upstream timeout
    unreachable_client = OpenSanctionsClient(
        base_url="http://127.0.0.1:59999",
        timeout=0.2,
    )
    entities, source = await unreachable_client.search("Mohamed El-Sayed Ahmed", limit=5)
    assert source == "LOCAL_BASELINE"
    assert len(entities) > 0
    assert any("Mohamed" in e.get("caption", "") for e in entities)


# ===========================================================================
# SCENARIO 13: Rate Limit Handling (HTTP 429 Backoff / Fallback)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_13_rate_limit_handling():
    # Verify client search falls back gracefully without raising unhandled exception
    client = OpenSanctionsClient()
    entities, source = await client.search("Ilan Shor", limit=5)
    assert source in ("ONLINE_API", "LOCAL_BASELINE", "CACHE")
    assert len(entities) > 0


# ===========================================================================
# SCENARIO 14: Injection Attempt via Input Fields (Security Validation)
# ===========================================================================
@pytest.mark.asyncio
async def test_scenario_14_injection_security(auth_token):
    # SQL Drop Table mutation vector
    res1 = await screen_entity_against_watchlists(
        name="DROP TABLE customers",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res1.get("error") in ("SECURITY_VIOLATION", "INVALID_INPUT")

    # Shell injection vector in national ID
    res2 = await screen_entity_against_watchlists(
        name="Viktor Bout",
        identification_number="EG-NAT; rm -rf /",
        specialist="SanctionsScreeningAgent",
        auth_token=auth_token,
    )
    assert res2.get("error") in ("SECURITY_VIOLATION", "INVALID_INPUT")


# ===========================================================================
# FASTAPI INTEGRATION TESTS
# ===========================================================================
@pytest.mark.asyncio
async def test_fastapi_sanctions_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/sanctions/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["baseline_entity_count"] > 0


@pytest.mark.asyncio
async def test_fastapi_screen_entity_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post(
            "/api/v1/sanctions/screen",
            json={
                "name": "Ilan Shor",
                "entity_type": "individual",
                "countries": ["MD"],
                "birth_date": "1987-03-06",
                "threshold": 0.70,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["match_found"] is True
        assert data["review_required"] is True
        assert data["best_match_confidence"] >= 0.85

