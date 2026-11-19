# MCP-001: Server-Bound Credential Isolation & Per-Route Auth Dispatch

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `critical` · **Status:** `canonical`
- **Reference Implementation:** [`../mcp_serve_ref/route_dispatch_auth.py`](../mcp_serve_ref/route_dispatch_auth.py)

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

Naive HTTP-to-MCP wrappers fail in two opposite ways when authenticating to upstream REST APIs:
1. **Confused-Deputy Token Passthrough:** Forwarding the incoming MCP client's `Authorization: Bearer ...` header directly to an upstream service violates audience restriction. If a prompt injection tricks the agent into invoking an unintended tool, the server replays the caller's ambient token upstream. Even worse, developers sometimes add `api_key: str` to tool `inputSchema` parameters, leaking plaintext secrets into LLM transcripts and telemetry logs.
2. **Monolithic Server Token Over-Privilege:** Binding a single global credential onto an `httpx.AsyncClient` leaks bearer tokens to explicitly public endpoints (`security: []` such as `/health` or `/status`) and forces read-only triage tools to carry high-privilege `AdminApiKey` credentials required by only one administrative route.

## Normative Authorities

- **`MCP-2026-07-28:TOKEN-PASSTHROUGH`** — Model Context Protocol Specification (`2026-07-28`), *Authorization & Security Best Practices*: MCP servers MUST NOT accept or forward client tokens upstream unless explicitly audience-scoped for the server; upstream API credentials MUST be bound independently.
- **`IETF:RFC-9700`** — OAuth 2.0 Security Best Current Practice (§4.14 Audience Restriction).
- **`OPENAPI:3.1.0`** — OpenAPI v3.1.0 §4.8.30 Security Requirement Object (operation-level `security` overrides and `security: []` anonymous routes).
- **`SALTZER-SCHROEDER:1975`** — *Least Privilege* & *Complete Mediation* (per-operation credential scoping rather than ambient global tokens).
- **Weaknesses:** `CWE-287` (Improper Authentication), `CWE-863` (Incorrect Authorization), `CWE-522` (Insufficiently Protected Credentials), `OWASP-API2:2023`, `OWASP-LLM06:2025`.

## Solution & Invariants

1. **Env-Bound Credential Resolution Only:** Load upstream tokens, API keys, or OAuth2 client credentials exclusively from server-side environment variables (or mounted secret files) at startup—never from MCP request headers or tool arguments.
2. **Per-Operation Route Dispatch over a Single Connection Pool:** Compile `(HTTP method, path_template)` route rules from the normalized manifest into a stateless `RouteDispatchAuth` dispatcher:
   - Routes marked `auth_scheme: "none"` (`security: []`) inject **zero** auth headers/params.
   - Routes bound to named schemes (`AdminKey`, `ReadToken`) inject only that scheme's credential.
   - Unmatched routes fall back to the server's default auth handler (`fail-closed` if required env vars are absent).

## Anti-Patterns

- Reading `ctx.request_context.headers["authorization"]` inside an MCP tool and forwarding it to `httpx`.
- Exposing `token`, `api_key`, `password`, or `authorization` in `@tool` function parameters.
- Creating a new `httpx.AsyncClient` inside every tool call just to vary credentials per endpoint.

## Verification Gates

- **Static Schema Audit:** Fail CI if any tool `inputSchema` property matches `(?i)(token|secret|password|api[-_]?key|authorization)`.
- **Route Dispatch Unit Gate:** Verify `GET /health` (`auth_scheme="none"`) transmits zero `Authorization` or `X-API-Key` headers while `DELETE /admin/audit` transmits `X-Admin-Key` and `GET /incidents/1` transmits `Authorization: Bearer ...` over the same dispatcher.
