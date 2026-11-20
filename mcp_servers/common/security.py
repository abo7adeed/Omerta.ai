"""Read-only security invariant enforcement and multi-layered injection defense for MCP tools."""

from __future__ import annotations

import re
from typing import Any

from domain.errors import ValidationError
from mcp_servers.common.errors import SecurityValidationError

# Strict identifier regex: alphanumeric, underscores, hyphens, periods, colons (IPv6), and at-signs
SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_\-\.:/@]+$")

# Prohibited SQL mutation verbs (whole-word matching)
PROHIBITED_SQL_KEYWORDS = re.compile(
    r"\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|DROP\s+(TABLE|DATABASE|INDEX|VIEW)|"
    r"ALTER\s+(TABLE|DATABASE)|TRUNCATE\s+TABLE|CREATE\s+(TABLE|DATABASE|USER|ROLE)|"
    r"GRANT\s+\w+\s+TO|REVOKE\s+\w+\s+FROM|UNION\s+(ALL\s+)?SELECT|INFORMATION_SCHEMA)\b",
    re.IGNORECASE,
)

# Prohibited Cypher mutation verbs
PROHIBITED_CYPHER_KEYWORDS = re.compile(
    r"\b(CREATE\s+\(|MERGE\s+\(|SET\s+\w+\.|DETACH\s+DELETE|DELETE\s+\w+|"
    r"REMOVE\s+\w+\.|DROP\s+INDEX|DROP\s+CONSTRAINT|CALL\s+dbms|CALL\s+apoc)\b",
    re.IGNORECASE,
)

# Prohibited Shell / Command execution triggers for identifiers
PROHIBITED_SHELL_PATTERNS = re.compile(
    r"([;&|`$><]|\$\(|\b(powershell|cmd\.exe|bash|sh|zsh|curl|wget|python\s+-c|eval|exec|subprocess)\b)",
    re.IGNORECASE,
)

# Prohibited Shell patterns specifically for text search queries (allows comparison > < and company &)
PROHIBITED_QUERY_SHELL_PATTERNS = re.compile(
    r"([;`$]|\$\(|\b(powershell|cmd\.exe|bash|zsh|curl|wget|python\s+-c|subprocess)\b|\|\s*\w+)",
    re.IGNORECASE,
)

# Directory traversal
PATH_TRAVERSAL_RE = re.compile(r"(\.\./|\.\.\\)")


def validate_safe_identifier(
    value: Any,
    field_name: str = "identifier",
    max_length: int = 64,
) -> str:
    """Validate that an external identifier strictly conforms to read-only security invariants.

    Raises:
    - ValidationError: If value is not a string, is blank, or exceeds max_length without security violation.
    - SecurityValidationError: If value contains SQL/Cypher mutation keywords, shell metacharacters, or traversal sequences.
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)

    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} must not be empty", field=field_name)

    # 1. Security Check: Path traversal (relative or absolute)
    if PATH_TRAVERSAL_RE.search(cleaned) or cleaned.startswith(("/", "\\")):
        raise SecurityValidationError(
            message=f"Path traversal detected in {field_name}",
            field=field_name,
            detail="Identifier contains prohibited path traversal sequences or directory paths",
            recovery="Provide a clean entity identifier without filesystem paths.",
        )

    # 2. Security Check: OS command injection
    if PROHIBITED_SHELL_PATTERNS.search(cleaned):
        raise SecurityValidationError(
            message=f"Prohibited shell injection sequence detected in {field_name}",
            field=field_name,
            detail="Identifier contains shell metacharacters or execution triggers",
            recovery="Remove all shell metacharacters (; & | $ ` > <) and execution commands.",
        )

    # 3. Security Check: SQL mutation keywords
    if PROHIBITED_SQL_KEYWORDS.search(cleaned):
        raise SecurityValidationError(
            message=f"Prohibited SQL mutation detected in {field_name}",
            field=field_name,
            detail="The identifier contains prohibited SQL modification keywords",
            recovery="All MCP tools are strictly read-only. Remove all SQL mutation verbs.",
        )

    # 4. Security Check: Cypher mutation keywords
    if PROHIBITED_CYPHER_KEYWORDS.search(cleaned):
        raise SecurityValidationError(
            message=f"Prohibited Cypher mutation detected in {field_name}",
            field=field_name,
            detail="The identifier contains prohibited Cypher modification keywords",
            recovery="All MCP graph tools are strictly read-only. Remove Cypher mutation verbs.",
        )

    # 5. Length Check
    if len(cleaned) > max_length:
        raise ValidationError(f"{field_name} exceeds {max_length} characters", field=field_name)

    # 6. Character Set Match
    if not SAFE_IDENTIFIER_RE.match(cleaned):
        raise SecurityValidationError(
            message=f"Invalid characters detected in {field_name}",
            field=field_name,
            detail=f"Identifier contains invalid characters: '{cleaned}'",
            recovery="Identifiers may only contain letters, digits, dashes, underscores, periods, and colons.",
        )

    return cleaned


def validate_safe_query(
    value: Any,
    field_name: str = "query",
    max_length: int = 512,
) -> str:
    """Validate knowledge / text search query against shell and mutation injection."""
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string", field=field_name)

    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} must not be empty", field=field_name)

    # 1. Reject shell execution patterns in text query
    if PROHIBITED_QUERY_SHELL_PATTERNS.search(cleaned):
        raise SecurityValidationError(
            message="Prohibited shell execution syntax in query",
            field=field_name,
            detail="Search query contains prohibited shell metacharacters or command patterns",
            recovery="Search using standard text or AML keywords without shell commands.",
        )

    # 2. Reject database drop/truncate/delete statements in query
    if re.search(r"\b(DROP\s+TABLE|TRUNCATE\s+TABLE|DELETE\s+FROM|DETACH\s+DELETE)\b", cleaned, re.IGNORECASE):
        raise SecurityValidationError(
            message="Prohibited mutation syntax in search query",
            field=field_name,
            detail="Search query contains prohibited database mutation keywords",
            recovery="Knowledge search is strictly read-only. Use policy or regulatory search terms.",
        )

    # 3. Length Check
    if len(cleaned) > max_length:
        raise ValidationError(f"{field_name} exceeds {max_length} characters", field=field_name)

    return cleaned
