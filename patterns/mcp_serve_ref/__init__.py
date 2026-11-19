"""Strictly-typed runnable reference implementations for mcp-serve (MCP 2026-07-28) patterns."""

from patterns.mcp_serve_ref.dual_axis_bounding import (
    PayloadBudgetExceededError,
    bound_structured_payload,
)
from patterns.mcp_serve_ref.header_validator import (
    HeaderMirroringError,
    validate_x_mcp_header_param,
)
from patterns.mcp_serve_ref.route_dispatch_auth import (
    AuthConfigurationError,
    RouteAuthRule,
    ServerBoundRouteAuth,
)
from patterns.mcp_serve_ref.schema_normalizer import (
    SchemaNormalizationError,
    flatten_composed_schema,
    rank_projected_fields,
    resolve_schema_refs,
)
from patterns.mcp_serve_ref.workspace_integrity import (
    LockedWorkspaceDigest,
    TamperDetectionError,
)

__all__ = [
    "AuthConfigurationError",
    "HeaderMirroringError",
    "LockedWorkspaceDigest",
    "PayloadBudgetExceededError",
    "RouteAuthRule",
    "SchemaNormalizationError",
    "ServerBoundRouteAuth",
    "TamperDetectionError",
    "bound_structured_payload",
    "flatten_composed_schema",
    "rank_projected_fields",
    "resolve_schema_refs",
    "validate_x_mcp_header_param",
]
