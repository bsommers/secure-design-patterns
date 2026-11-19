# Changelog

All notable changes to the **Secure Design Patterns Library** are documented in this file.

## [1.0.0] - 2026-11-19

### Added
- **Pattern Schema & Deterministic Validator** (`schema/pattern.schema.json`, `scripts/validate_patterns.py`): Enforces JSON Schema `2020-12` structure, authority ID cross-references, Markdown heading completeness, and zero broken relative links.
- **Specification-Derived Authorities Registry** (`authorities/mcp-2026-07-28.json`, `authorities/README.md`): Normative citations spanning MCP Specification `2026-07-28` (`SEP-2575`, `SEP-2567`, `SEP-2577`, JSON Schema `2020-12` `outputSchema`/`structuredContent`, Token Passthrough Prohibition, `stdio` transport), IETF RFC 9110, RFC 6901, RFC 9700 (OAuth 2.1 Security Best Current Practice), OWASP API Security Top 10 (2023), OWASP Top 10 for LLM Applications (2025), Saltzer & Schroeder design principles, and MITRE CWEs.
- **`mcp-serve` Domain Catalog (`MCP-001` through `MCP-008`)** (`patterns/mcp-serve/`):
  - `MCP-001`: Server-Bound Credential Isolation (Anti-Token-Passthrough & Per-Route Auth Dispatch)
  - `MCP-002`: Immutable Chassis / Narrow Agent Overlay (`:ro` Golden Template + `SHA-256` Tamper Guard)
  - `MCP-003`: Dual-Axis Structured Payload Bounding (Collection Cardinality Slicing + UTF-8 Byte Truncation)
  - `MCP-004`: Cycle-Safe & Polymorphic Schema Projection (`ancestor_refs` Cycle Breaking, Path-Confined `$ref`s & `allOf` Merge)
  - `MCP-005`: Composite Intent Tools over CRUD Mirrors (Server-Side Joins & `<= 15` Active Toolset Budgets)
  - `MCP-006`: Stateless Sessionless Execution (`SEP-2575` `server/discover`, `SEP-2567` Cursor Continuity & Async DI Safety)
  - `MCP-007`: Primitive RFC 9110 Header Mirroring (`1*tchar` Validation, Sensitive-Name Blocking & Non-Union Typing)
  - `MCP-008`: Layered OS Sandbox & STDIO Frame Hygiene (Kernel Containment + AST `SEP-2577` Gate + `stderr`-Only JSON Logging)
- **Runnable Reference Package & Torture Suite** (`patterns/mcp_serve_ref/`, `tests/test_mcp_serve_patterns.py`): Strictly-typed Python reference modules proving `MCP-001`, `MCP-002`, `MCP-003`, `MCP-004`, and `MCP-007` against adversarial and wild OpenAPI inputs, verified via SHA-pinned GitHub Actions CI (`.github/workflows/ci.yml`) and interactive catalog showcase (`docs/index.html`).
