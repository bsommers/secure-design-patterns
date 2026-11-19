# MCP-006: Stateless Sessionless Execution & Lifespan Async DI Safety

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `high` · **Status:** `canonical`

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

MCP `2026-07-28` (`SEP-2575` & `SEP-2567`) eliminates stateful `initialize` handshakes and sticky `Mcp-Session-Id` headers so Streamable HTTP servers can autoscale horizontally behind standard L7 load balancers. Two common implementation bugs break stateless execution:
1. **Cross-Tenant State Bleed via Module Globals:** Storing `LAST_PAGE_CURSOR`, `ACTIVE_INCIDENT_ID`, or cached user responses in module-level Python dicts/lists leaks state across concurrent callers and fails randomly when subsequent requests land on different replicas.
2. **Async Context-Manager Re-Entry Crash in Dependency Injection:** Pooling a single `httpx.AsyncClient` in the server lifespan is essential to avoid TLS handshake/socket exhaustion. However, if the FastMCP dependency provider (`get_http_client`) is declared as a synchronous `def` returning an already-entered `httpx.AsyncClient` (which implements `__aenter__`/`__aexit__`), async DI containers inspect the return value, see an async context manager, and attempt to `async with client:` a **second time** per tool call—raising `RuntimeError: Cannot open a client instance more than once`.

## Normative Authorities

- **`MCP-2026-07-28:SEP-2575`** — Stateless Capability Discovery (`server/discover`).
- **`MCP-2026-07-28:SEP-2567`** — Sessionless Streamable HTTP Transport.
- **Weaknesses:** `CWE-362` (Concurrent Execution Using Shared Resource with Improper Synchronization), `CWE-664` (Improper Control of a Resource Through its Lifetime), `CWE-404`, `OWASP-API4:2023`, `OWASP-API1:2023`.

## Solution & Invariants

1. **Zero Mutable Module Globals in `src/tools/`:** Every tool invocation MUST be pure with respect to server memory; pagination (`cursor`, `next_cursor`) and idempotency tokens MUST pass explicitly in tool inputs and outputs.
2. **Lifespan Pool + `async def` DI Getter:** Enter a single `httpx.AsyncClient` inside the server's `@lifespan` context manager, store it on lifespan state, and expose it via `async def get_http_client() -> httpx.AsyncClient` (`Depends(get_http_client)`), preventing DI re-entry into `__aenter__`.

## Anti-Patterns

- `CURRENT_FILTERS: dict[str, str] = {}` at module scope in `src/tools/*.py`.
- Creating `async with httpx.AsyncClient() as client:` inside each `@tool` call (defeating connection pooling and offline `respx` transport injection).
- Defining `def get_http_client() -> httpx.AsyncClient:` synchronously when returning an active async context manager.

## Verification Gates

- **Concurrency & Lifespan Gate:** Execute `asyncio.gather` across 10 concurrent tool invocations over one FastMCP `Client(mcp)` session and assert zero `RuntimeError` re-entry faults and zero cross-call state leakage.
