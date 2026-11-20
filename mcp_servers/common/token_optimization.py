"""Token optimization, result-set bounding, and cursor pagination helpers for MCP tools."""

from __future__ import annotations

import base64
import json
from typing import Any

from mcp_servers.common.errors import InvalidCursorError, ResultLimitExceededError
from domain.errors import ValidationError

DEFAULT_LIMIT = 20
MAX_LIMIT = 100
MIN_LIMIT = 1


def validate_and_clamp_limit(
    value: int | None,
    *,
    default: int = DEFAULT_LIMIT,
    max_limit: int = MAX_LIMIT,
    strict: bool = False,
) -> int:
    """Validate limit and clamp within [MIN_LIMIT, max_limit].

    If strict is True and value > max_limit, raises ResultLimitExceededError.
    Otherwise clamps to max_limit.
    """
    if value is None:
        return default

    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("limit must be an integer", field="limit")

    if value < MIN_LIMIT:
        raise ValidationError(f"limit must be >= {MIN_LIMIT}", field="limit", limit=value)

    if value > max_limit:
        if strict:
            raise ResultLimitExceededError(requested=value, max_allowed=max_limit)
        return max_limit

    return value


def encode_cursor(offset: int, metadata: str = "") -> str:
    """Encode an integer offset into an opaque, URL-safe base64 pagination cursor."""
    payload = {"o": int(offset), "m": metadata}
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def decode_cursor(cursor: str | None) -> int:
    """Decode an opaque pagination cursor back into an integer offset.

    Returns 0 if cursor is None or empty.
    Raises InvalidCursorError if malformed or missing offset key.
    """
    if cursor is None:
        return 0

    cleaned = cursor.strip()
    if not cleaned:
        return 0

    try:
        raw = base64.urlsafe_b64decode(cleaned.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict) or "o" not in data:
            raise InvalidCursorError(cursor=cleaned)
        offset = int(data["o"])
        if offset < 0:
            raise ValueError("Negative offset")
        return offset
    except Exception as exc:
        raise InvalidCursorError(cursor=cleaned) from exc


def build_paginated_envelope(
    items: list[Any],
    offset: int,
    limit: int,
    total_count: int | None = None,
) -> dict[str, Any]:
    """Construct a standardized token-optimized pagination envelope."""
    returned_count = len(items)
    has_more = False

    if total_count is not None:
        has_more = (offset + returned_count) < total_count
    else:
        # If returned equal to requested limit, there may be more
        has_more = returned_count >= limit

    next_cursor = encode_cursor(offset + returned_count) if has_more else None

    return {
        "items": items,
        "count": returned_count,
        "limit": limit,
        "truncated": has_more,
        "pagination": {
            "offset": offset,
            "returned": returned_count,
            "limit": limit,
            "has_more": has_more,
            "next_cursor": next_cursor,
            "total_estimate": total_count,
        },
    }
