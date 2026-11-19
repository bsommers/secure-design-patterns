# MCP-007: Primitive RFC 9110 `x-mcp-header` Mirroring (Non-Union Contract)

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `high` · **Status:** `canonical`
- **Reference Implementation:** [`../mcp_serve_ref/header_validator.py`](../mcp_serve_ref/header_validator.py)

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

Streamable HTTP deployments sometimes mirror non-sensitive tool parameters (such as `Idempotency-Key`, `X-Tenant-Region`, or `X-Correlation-ID`) onto HTTP headers for edge routing or deduplication via `json_schema_extra={"x-mcp-header": "..."}`. Three sharp edges cause security flaws or **silent tool disappearance**:
1. **Header Name Injection (`CRLF` / Delimiters):** Unvalidated `x-mcp-header` names containing whitespace, colons, or control characters violate HTTP field syntax (`CWE-113`).
2. **Credential & PII Leakage in Transport Metadata:** Attaching `x-mcp-header` to `api_key`, `authorization`, `token`, `password`, or `ssn` exposes secrets to intermediate proxies and access logs (`CWE-200`).
3. **The `mcp==2.3.0` Nullable `anyOf` Silent Drop:** In Python/Pydantic, declaring an optional header-mirrored parameter as `str | None = None` emits JSON Schema `{"anyOf": [{"type": "string"}, {"type": "null"}], "x-mcp-header": "Idempotency-Key"}`. The `mcp` SDK (`2.3.0`) validates `x-mcp-header` properties by checking top-level `"type" in {"string", "integer", "boolean"}`—when `"anyOf"` is present instead of top-level `"type"`, **`mcp` silently drops the entire tool from `tools/list` with zero startup exception!**

## Normative Authorities

- **`MCP-2026-07-28:HEADER-MIRRORING`** — MCP Streamable HTTP Header Mirroring Specification.
- **`IETF:RFC-9110`** — HTTP Semantics §5.1 (`field-name = token = 1*tchar`).
- **Weaknesses:** `CWE-113` (Improper Neutralization of CRLF Sequences in HTTP Headers), `CWE-200` (Exposure of Sensitive Information), `OWASP-API8:2023`, `OWASP-API2:2023`.

## Solution & Invariants

1. **Strict RFC 9110 `1*tchar` Validation:** Verify header names match `^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$` and do not target Hop-by-Hop or `Authorization`/`Cookie`/`Host` headers.
2. **Sensitive Parameter Blocklist & Primitive-Only Types:** Reject `x-mcp-header` on any parameter matching `(token|key|secret|password|authorization|cookie|ssn)` (except explicitly safe `idempotency_key` mapped to `Idempotency-Key`) and permit only `string`, `integer`, or `boolean` primitives.
3. **Non-Union Optional Default (`str = ""`):** Always type optional `x-mcp-header` parameters as `Annotated[str, Field(default="", ...)] = ""` (never `str | None`), emitting `"type": "string"` cleanly and omitting the upstream header when the runtime value is `""`.

## Anti-Patterns

- `idempotency_key: Annotated[str | None, Field(default=None, json_schema_extra={"x-mcp-header": "Idempotency-Key"})] = None` (silently disappears from `tools/list` in `mcp==2.3.0`!).
- Mirroring `number` (`float`), `array`, or `object` fields into HTTP headers.

## Verification Gates

- **Manifest-to-`tools/list` Parity Gate:** Assert `[t.name for t in await client.list_tools()]` matches the manifest tool list 1-for-1 (catching silent SDK drops immediately).
- **Schema Shape Gate:** Assert every `inputSchema` property carrying `"x-mcp-header"` declares a top-level `"type"` in `{"string", "integer", "boolean"}` and zero `"anyOf"` / `"oneOf"` keys.
