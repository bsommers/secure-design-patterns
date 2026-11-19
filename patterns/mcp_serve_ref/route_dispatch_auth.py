"""Reference implementation of Pattern MCP-001: Server-Bound Credential Isolation."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass


class AuthConfigurationError(RuntimeError):
    """Raised when server-bound credentials or route rules violate MCP-001 invariants."""


@dataclass(frozen=True)
class SchemeBinding:
    """Server-bound credential scheme resolved strictly from server environment mappings."""

    scheme_type: str  # "bearer" | "api_key_header"
    env_var: str
    header_name: str = "Authorization"


@dataclass(frozen=True)
class RouteAuthRule:
    """Per-operation OpenAPI security override rule."""

    method: str
    path_template: str
    auth_scheme: str  # "none" for OpenAPI security: [], or named scheme key


def _compile_path_regex(path_template: str, base_prefix: str = "") -> re.Pattern[str]:
    prefix = base_prefix.rstrip("/")
    full_tpl = f"{prefix}/{path_template.lstrip('/')}".rstrip("/") or "/"
    escaped = re.sub(
        r"\{[^{}/]+\}", r"[^/]+", re.escape(full_tpl).replace(r"\{", "{").replace(r"\}", "}")
    )
    return re.compile(f"^{escaped}$")


class ServerBoundRouteAuth:
    """Dispatches server-bound upstream auth headers per route without client passthrough."""

    def __init__(
        self,
        *,
        default_scheme: SchemeBinding | None,
        named_schemes: Mapping[str, SchemeBinding],
        route_rules: list[RouteAuthRule],
        env: Mapping[str, str],
        base_path_prefix: str = "",
    ) -> None:
        self._default = default_scheme
        self._schemes = dict(named_schemes)
        self._env = dict(env)
        self._compiled_rules: list[tuple[str, re.Pattern[str], str]] = []

        for rule in route_rules:
            if rule.auth_scheme != "none" and rule.auth_scheme not in self._schemes:
                raise AuthConfigurationError(
                    f"Route {rule.method} {rule.path_template} references unknown "
                    f"scheme '{rule.auth_scheme}'."
                )
            self._compiled_rules.append(
                (
                    rule.method.upper(),
                    _compile_path_regex(rule.path_template, base_path_prefix),
                    rule.auth_scheme,
                )
            )

    def _resolve_binding_headers(self, binding: SchemeBinding) -> dict[str, str]:
        secret = self._env.get(binding.env_var, "").strip()
        if not secret:
            raise AuthConfigurationError(
                f"Missing required server-bound credential env var '{binding.env_var}'."
            )
        if binding.scheme_type == "bearer":
            return {"Authorization": f"Bearer {secret}"}
        if binding.scheme_type == "api_key_header":
            return {binding.header_name: secret}
        raise AuthConfigurationError(f"Unsupported scheme_type '{binding.scheme_type}'.")

    def headers_for_request(
        self,
        method: str,
        url_path: str,
        *,
        incoming_mcp_headers: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        """Compute outbound upstream auth headers, ignoring any incoming MCP client credentials."""
        # MCP-001 Invariant: incoming_mcp_headers is accepted ONLY so callers cannot accidentally
        # merge it; any Authorization/Cookie on incoming MCP transport is never forwarded upstream.
        _ = incoming_mcp_headers
        normalized_method = method.upper()
        normalized_path = url_path.rstrip("/") or "/"

        for rule_method, pattern, scheme_name in self._compiled_rules:
            if rule_method == normalized_method and pattern.match(normalized_path):
                if scheme_name == "none":
                    return {}
                return self._resolve_binding_headers(self._schemes[scheme_name])

        if self._default is None:
            return {}
        return self._resolve_binding_headers(self._default)
