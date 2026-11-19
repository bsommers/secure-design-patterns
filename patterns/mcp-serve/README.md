# `mcp-serve` — MCP Server (`2026-07-28`) Secure Design Patterns

[← Back to Library Root](../../README.md) · [Normative Authorities](../../authorities/README.md) · [Machine Catalog (`catalog.json`)](catalog.json)

This domain catalog codifies **eight specification-grounded architecture and security patterns (`MCP-001` through `MCP-008`)** for building, generating, and verifying **Model Context Protocol (`2026-07-28`)** servers. Each pattern was forged from normative protocol specifications (`SEP-2575`, `SEP-2567`, `SEP-2577`, JSON Schema `2020-12`, RFC 9700, RFC 9110, RFC 6901) and empirical failure modes uncovered while engineering [`bsommers/forge`](https://github.com/bsommers/forge).

---

## Pattern Index

| ID | Pattern | Severity | Core Failure Mode Defeated | Reference Module |
|----|---------|:--------:|----------------------------|------------------|
| [`MCP-001`](MCP-001-server-bound-credential-isolation.md) | **Server-Bound Credential Isolation** | `critical` | Confused-deputy token passthrough & single-credential over-privilege on `security: []` / admin routes | [`route_dispatch_auth.py`](../mcp_serve_ref/route_dispatch_auth.py) |
| [`MCP-002`](MCP-002-immutable-chassis-narrow-agent-overlay.md) | **Immutable Chassis / Narrow Agent Overlay** | `critical` | Coding-agent reward hacking (mutating contract tests, auth middleware, or coverage gates) | [`workspace_integrity.py`](../mcp_serve_ref/workspace_integrity.py) |
| [`MCP-003`](MCP-003-dual-axis-structured-payload-bounding.md) | **Dual-Axis Structured Payload Bounding** | `high` | Stock middleware erasing `outputSchema`; 3,000-element short-string arrays bypassing `32 KiB` string caps | [`dual_axis_bounding.py`](../mcp_serve_ref/dual_axis_bounding.py) |
| [`MCP-004`](MCP-004-cycle-safe-polymorphic-schema-projection.md) | **Cycle-Safe & Polymorphic Schema Projection** | `high` | Remote `$ref` SSRF, `../` traversal, cyclic `$ref` crashes, `allOf` erasure & dropped data arrays | [`schema_normalizer.py`](../mcp_serve_ref/schema_normalizer.py) |
| [`MCP-005`](MCP-005-composite-intent-tools-over-crud-mirrors.md) | **Composite Intent Tools over CRUD Mirrors** | `medium` | Chatty 6–10 turn LLM foreign-key joins & cross-shard context window bloat (`> 15` tools) | — |
| [`MCP-006`](MCP-006-stateless-sessionless-execution.md) | **Stateless Sessionless Execution** | `high` | Sticky session scaling breaks, global state cross-tenant bleed & async DI lifespan re-entry crashes | — |
| [`MCP-007`](MCP-007-primitive-rfc9110-header-mirroring.md) | **Primitive RFC 9110 Header Mirroring** | `high` | CRLF header injection, secret header leakage & `mcp==2.3.0` silently dropping `str \| None` (`anyOf`) tools | [`header_validator.py`](../mcp_serve_ref/header_validator.py) |
| [`MCP-008`](MCP-008-layered-sandbox-and-stdio-frame-hygiene.md) | **Layered OS Sandbox & STDIO Frame Hygiene** | `critical` | `stdout` `print()` JSON-RPC corruption, `SEP-2577` drift & mistaking AST lint for kernel isolation | — |
