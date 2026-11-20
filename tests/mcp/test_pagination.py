"""Automated Test Suite: Cursor-Based Pagination & Envelope Verification.

Validates:
- Stateless opaque cursor generation and decoding.
- Detection and rejection of corrupted or tampered cursors with INVALID_PAGINATION_CURSOR.
- Standardized pagination metadata envelope construction.
- Multi-page iteration sequencing.
"""

import pytest
from mcp_servers.common.token_optimization import (
    encode_cursor,
    decode_cursor,
    build_paginated_envelope,
)
from mcp_servers.common.errors import InvalidCursorError


def test_cursor_round_trip():
    """Verify offset encodes and decodes deterministically."""
    for offset in [0, 20, 50, 100, 2500]:
        cursor = encode_cursor(offset)
        assert isinstance(cursor, str)
        assert len(cursor) > 0
        decoded = decode_cursor(cursor)
        assert decoded == offset


def test_none_or_empty_cursor_returns_zero_offset():
    """Omitting cursor starts pagination from offset 0."""
    assert decode_cursor(None) == 0
    assert decode_cursor("") == 0
    assert decode_cursor("   ") == 0


@pytest.mark.parametrize(
    "corrupted_cursor",
    [
        "not_base64!",
        "???",
        "ey...",
        "e30=",  # valid base64, but no offset
        "ZXlKdlptWmxkQ0k2SW1WNGNHbHlaV1FnYzJobFpHeDFZVzRnWm1GcGJEbz0=",  # tampered
    ],
)
def test_corrupted_cursor_raises_invalid_cursor_error(corrupted_cursor: str):
    """Malformed or invalid cursor raises InvalidCursorError."""
    with pytest.raises(InvalidCursorError) as exc_info:
        decode_cursor(corrupted_cursor)

    payload = exc_info.value.payload
    assert payload["error"] == "INVALID_PAGINATION_CURSOR"
    assert "recovery" in payload


def test_build_paginated_envelope_has_more():
    """Verify envelope when more records remain to be fetched."""
    items = [{"id": f"TXN-{i}"} for i in range(20)]
    envelope = build_paginated_envelope(items=items, offset=0, limit=20, total_count=50)

    assert envelope["count"] == 20
    assert envelope["truncated"] is True
    pag = envelope["pagination"]
    assert pag["offset"] == 0
    assert pag["returned"] == 20
    assert pag["limit"] == 20
    assert pag["has_more"] is True
    assert pag["next_cursor"] is not None

    next_offset = decode_cursor(pag["next_cursor"])
    assert next_offset == 20


def test_build_paginated_envelope_terminal_page():
    """Verify envelope on final page where no further records exist."""
    items = [{"id": f"TXN-{i}"} for i in range(10)]
    envelope = build_paginated_envelope(items=items, offset=40, limit=20, total_count=50)

    assert envelope["count"] == 10
    assert envelope["truncated"] is False
    pag = envelope["pagination"]
    assert pag["offset"] == 40
    assert pag["returned"] == 10
    assert pag["has_more"] is False
    assert pag["next_cursor"] is None

