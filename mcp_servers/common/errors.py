"""Standardized error classes and recovery guidance for MCP infrastructure."""

from typing import Any
from domain.errors import DomainError, ValidationError


class SecurityValidationError(DomainError):
    """Input rejected due to prohibited operations, injection patterns, or boundary violations."""

    code = "SECURITY_VIOLATION"

    def __init__(
        self,
        message: str,
        field: str,
        detail: str,
        recovery: str = "",
        code: str | None = None,
    ) -> None:
        if code:
            self.code = code
        super().__init__(
            message,
            field=field,
            detail=detail,
            recovery=recovery
            or "All MCP tools are strictly read-only. Remove SQL/Cypher mutation keywords or shell commands.",
        )


class UnauthorizedToolAccessError(DomainError):
    """Specialist agent attempted to invoke a tool outside its least-privilege boundary."""

    code = "UNAUTHORIZED_TOOL_ACCESS"

    def __init__(self, specialist: str, tool_name: str, recovery: str = "", detail: str = "") -> None:
        super().__init__(
            f"Specialist '{specialist}' is unauthorized to call tool '{tool_name}'",
            specialist=specialist,
            tool=tool_name,
            detail=detail
            or f"The specialist '{specialist}' is restricted by least-privilege policy from calling '{tool_name}'.",
            recovery=recovery
            or f"Delegate this analysis to the specialist authorized for '{tool_name}'.",
        )


class AuthenticationRequiredError(DomainError):
    """Anonymous or unauthenticated MCP access attempted."""

    code = "AUTHENTICATION_REQUIRED"

    def __init__(self, detail: str = "", recovery: str = "") -> None:
        super().__init__(
            "Caller authentication is required for MCP access",
            detail=detail or "Anonymous calls are denied. Provide a valid specialist identity with auth_token.",
            recovery=recovery
            or "Authenticate using an explicit signed specialist token or trusted session context.",
        )


class InvalidCursorError(DomainError):
    """Supplied pagination cursor is malformed, corrupted, or expired."""

    code = "INVALID_PAGINATION_CURSOR"

    def __init__(self, cursor: str, recovery: str = "") -> None:
        super().__init__(
            f"Invalid pagination cursor: '{cursor}'",
            cursor=cursor,
            detail="The supplied pagination cursor could not be parsed or has expired.",
            recovery=recovery
            or "Restart pagination from the first page without providing a cursor parameter.",
        )


class ResultLimitExceededError(DomainError):
    """Requested result limit exceeds permitted maximum bounds."""

    code = "RESULT_LIMIT_EXCEEDED"

    def __init__(self, requested: int, max_allowed: int = 100, recovery: str = "") -> None:
        super().__init__(
            f"Requested limit {requested} exceeds maximum allowed {max_allowed}",
            requested_limit=requested,
            max_limit=max_allowed,
            detail=f"Result limits must not exceed {max_allowed} items per request.",
            recovery=recovery or f"Reduce requested limit to <= {max_allowed} and use cursor pagination.",
        )
