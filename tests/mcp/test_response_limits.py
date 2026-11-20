"""Automated Test Suite: Response Limits & Result-Set Bounding.

Validates:
- Upper-bound clamping to MAX_LIMIT (100) to prevent context exhaustion.
- Sensible defaults (20) applied when limit is omitted.
- Clean rejection of non-integer, zero, and negative limits.
- Strict limit exceedance enforcement where applicable.
"""

import pytest
from mcp_servers.common.token_optimization import validate_and_clamp_limit, DEFAULT_LIMIT, MAX_LIMIT, MIN_LIMIT
from mcp_servers.common.errors import ResultLimitExceededError
from domain.errors import ValidationError


def test_default_limit_applied_when_none():
    """Omitting limit returns DEFAULT_LIMIT (20)."""
    assert validate_and_clamp_limit(None) == DEFAULT_LIMIT
    assert DEFAULT_LIMIT == 20


def test_valid_limits_accepted():
    """Values within [1, 100] are accepted without alteration."""
    for limit in [1, 10, 20, 50, 100]:
        assert validate_and_clamp_limit(limit) == limit


def test_clamping_behavior_on_oversized_limit():
    """Limits exceeding 100 are clamped to 100 when strict=False."""
    assert validate_and_clamp_limit(150) == MAX_LIMIT
    assert validate_and_clamp_limit(1000) == MAX_LIMIT
    assert validate_and_clamp_limit(999999) == MAX_LIMIT


def test_strict_mode_raises_on_oversized_limit():
    """Limits exceeding 100 raise ResultLimitExceededError when strict=True."""
    with pytest.raises(ResultLimitExceededError) as exc_info:
        validate_and_clamp_limit(150, strict=True)

    payload = exc_info.value.payload
    assert payload["error"] == "RESULT_LIMIT_EXCEEDED"
    assert payload["requested_limit"] == 150
    assert payload["max_limit"] == 100
    assert "recovery" in payload


@pytest.mark.parametrize("invalid_limit", [0, -1, -50])
def test_negative_or_zero_limit_rejected(invalid_limit: int):
    """Limits < 1 are rejected cleanly with ValidationError."""
    with pytest.raises(ValidationError) as exc_info:
        validate_and_clamp_limit(invalid_limit)

    assert exc_info.value.payload["error"] == "VALIDATION_ERROR"
    assert exc_info.value.payload["field"] == "limit"


@pytest.mark.parametrize("invalid_type", ["20", 25.5, True, False, [], {}])
def test_non_integer_type_rejected(invalid_type):
    """Non-integer types (including booleans) are rejected cleanly."""
    with pytest.raises(ValidationError) as exc_info:
        validate_and_clamp_limit(invalid_type)

    assert exc_info.value.payload["error"] == "VALIDATION_ERROR"
    assert exc_info.value.payload["field"] == "limit"

