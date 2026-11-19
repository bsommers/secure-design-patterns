# MCP-005: Composite Intent Tools & Active Toolset Budgets over CRUD Mirrors

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `medium` · **Status:** `canonical`

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

REST APIs are factored around resource normalization (`GET /incidents/{id}`, `GET /incidents/{id}/timeline`, `GET /users/{uid}`, `GET /schedules/{sid}/oncall`). LLMs, by contrast, reason in **user intents** (*"What is the blast radius and active commander of incident INC-42?"*).

Directly wrapping 1 REST endpoint = 1 MCP tool creates two compounding failure modes:
1. **N+1 Agent Round-Trip Amplification:** Answering a single triage question requires 6–10 sequential tool invocations, multiplying end-to-end latency, consuming context tokens on intermediate foreign-key JSON, and compounding tool-argument hallucination risk at each hop.
2. **Cross-Shard Context Crowding:** Splitting a 75-endpoint OpenAPI specification into five 15-tool shards satisfies a per-server tool cap, **but fails if an operator mounts all five shards simultaneously into one agent workspace**, re-exposing 75 tools in `tools/list` and degrading tool-selection accuracy.

## Normative Authorities

- **`MCP-2026-07-28:SEP-2575`** — MCP Stateless Discovery (`server/discover`) & Tool Selection Ergonomics.
- **`MCP-2026-07-28:OUTPUT-SCHEMA`** — Structured Composite Tool Outputs.
- **Weaknesses:** `CWE-400` (Uncontrolled Resource Consumption — Context/Token Exhaustion), `CWE-250` (Execution with Unnecessary Privileges — Mounting Destructive Admin Tools in Read/Triage Sessions), `OWASP-LLM06:2025`, `OWASP-LLM10:2025`.

## Solution & Invariants

1. **Enforce `<= 15` Tools per Active Client Profile (Not Just per Binary):** Partition multi-shard suites into role-scoped client profiles (e.g., `incident-triage-readonly`, `incident-responder`, `billing-analyst`), each mounting `<= 15` total tools.
2. **Server-Side Fan-Out Joins (`asyncio.gather`):** Replace chatty foreign-key lookup chains with composite intent tools (such as `triage_incident`) that fan out independent upstream `GET` calls concurrently over the pooled `httpx.AsyncClient` and return one unified Pydantic model.
3. **Quarantine Destructive Operations:** Tools carrying `ToolAnnotations(destructiveHint=True)` (`DELETE`, purge, revoke) MUST trigger explicit AppSec governance signoff and stay excluded from default read/triage profiles.

## Anti-Patterns

-Blindly converting a 200-operation OpenAPI spec into 200 MCP tools in a single client configuration.
- Mixing unguarded `DELETE` / `purge` administrative tools into routine read-only observability profiles.

## Verification Gates

- **Toolset Budget Gate:** Reject any server manifest or generated client profile whose active tool count exceeds `15`.
- **Destructive Governance Gate:** Require `requires_appsec_destructive_signoff: true` metadata whenever any tool sets `destructiveHint=True`.
