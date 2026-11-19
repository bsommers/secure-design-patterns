# Specification-Derived Authorities

Every pattern in the **Secure Design Patterns Library** is anchored to a three-tier hierarchy of verifiable authorities so security and architectural controls never degrade into cargo-cult rules:

1. **Tier 1 — Normative Protocol & Language Specifications (`normative_spec`)**: Exact protocol versions, SEPs/RFCs, and schema standards with `MUST` / `MUST NOT` semantics (e.g., Model Context Protocol `2026-07-28`, `SEP-2575`, `SEP-2567`, `SEP-2577`, JSON Schema `2020-12`, IETF RFC 9110, RFC 6901, RFC 9700 OAuth 2.1).
2. **Tier 2 — Industry Threat & Weakness Taxonomies (`security_taxonomy`)**: Concrete weakness and attack-surface identifiers (MITRE CWE, OWASP API Security Top 10 `2023`, OWASP Top 10 for LLM Applications `2025`, Saltzer & Schroeder protection principles).
3. **Tier 3 — Empirical Field Lessons (`empirical_field`)**: Reproducible failure modes encountered in real implementations—such as `mcp==2.3.0` silently dropping tools when `x-mcp-header` parameters emit `anyOf`, stock `ResponseLimitingMiddleware` stripping `outputSchema=None`, or high-cardinality arrays of 10-byte IDs bypassing string-only `32 KiB` truncation budgets in [`bsommers/forge`](https://github.com/bsommers/forge).

## Authority Registries

- [`mcp-2026-07-28.json`](mcp-2026-07-28.json) — Normative specification, RFC, and foundational security authorities referenced by [`../patterns/mcp-serve/catalog.json`](../patterns/mcp-serve/catalog.json).
