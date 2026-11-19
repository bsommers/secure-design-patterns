"""Reference implementation of Pattern MCP-007: Primitive RFC 9110 x-mcp-header Mirroring."""

from __future__ import annotations

import re
from typing import Any

# RFC 9110 §5.1 token = 1*tchar
RFC9110_TCHAR_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")

FORBIDDEN_HEADER_NAMES = frozenset(
    {
        "authorization",
        "proxy-authorization",
        "cookie",
        "set-cookie",
        "host",
        "connection",
        "transfer-encoding",
        "content-length",
        "upgrade",
    }
)

SENSITIVE_PARAM_TOKENS = frozenset(
    {
        "token",
        "secret",
        "password",
        "passwd",
        "authorization",
        "cookie",
        "apikey",
        "api_key",
        "private_key",
        "ssn",
    }
)

ALLOWED_PRIMITIVE_TYPES = frozenset({"string", "integer", "boolean"})


class HeaderMirroringError(RuntimeError):
    """Raised when an x-mcp-header parameter violates RFC 9110, secret hygiene, or MCP SDK rules."""


def validate_x_mcp_header_param(
    param_name: str,
    prop_schema: dict[str, Any],
) -> str:
    """Validate a tool inputSchema property carrying x-mcp-header and return the header name."""
    header_name = prop_schema.get("x-mcp-header")
    if not isinstance(header_name, str) or not header_name:
        raise HeaderMirroringError(
            f"Parameter '{param_name}' has empty or non-string x-mcp-header."
        )

    if not RFC9110_TCHAR_RE.match(header_name):
        raise HeaderMirroringError(
            f"Header '{header_name}' on '{param_name}' violates RFC 9110 §5.1 1*tchar syntax."
        )

    if header_name.lower() in FORBIDDEN_HEADER_NAMES:
        raise HeaderMirroringError(
            f"Header '{header_name}' on '{param_name}' is a forbidden security/hop-by-hop header."
        )

    lower_param = param_name.lower()
    if lower_param != "idempotency_key" and (
        lower_param in SENSITIVE_PARAM_TOKENS
        or any(
            tok in lower_param.split("_") for tok in {"token", "secret", "password", "key", "ssn"}
        )
    ):
        raise HeaderMirroringError(
            f"Parameter '{param_name}' appears sensitive and MUST NOT be mirrored via x-mcp-header."
        )

    if "anyOf" in prop_schema or "oneOf" in prop_schema:
        raise HeaderMirroringError(
            f"Parameter '{param_name}' uses anyOf/oneOf union with x-mcp-header='{header_name}', "
            "causing mcp==2.3.0 to drop the tool; use a non-union primitive with default=''."
        )

    schema_type = prop_schema.get("type")
    if schema_type not in ALLOWED_PRIMITIVE_TYPES:
        raise HeaderMirroringError(
            f"Parameter '{param_name}' has type '{schema_type}'; x-mcp-header requires one of "
            f"{sorted(ALLOWED_PRIMITIVE_TYPES)}."
        )

    return header_name
