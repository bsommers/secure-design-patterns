# MCP-003: Dual-Axis Structured Payload Bounding (Cardinality + Byte Budget)

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `high` · **Status:** `canonical`
- **Reference Implementation:** [`../mcp_serve_ref/dual_axis_bounding.py`](../mcp_serve_ref/dual_axis_bounding.py)

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

Unbounded MCP tool responses blow out LLM context windows, spike token bills, and degrade multi-step reasoning. However, naive response-limiting middleware falls flat in **two subtle ways**:
1. **Erasing `outputSchema` (`output_schema = None`):** Stock FastMCP `ResponseLimitingMiddleware` strips `outputSchema` from `tools/list` because naive raw-string truncation slices serialized JSON mid-object, invalidating structured responses. That breaks MCP `2026-07-28` structured tool contracts.
2. **The High-Cardinality Short-String Bypass:** Middleware that preserves `outputSchema` by recursively shrinking individual strings `>= 16` bytes works on long log blobs, **but fails completely on high-cardinality lists of short values**. For example, `{"items": ["inc-000001", "inc-000002", ...]}` with `3,000` 10-byte IDs serializes to `~45–150 KiB` (far above a `32,768`-byte budget), yet *zero* individual strings are `>= 16` bytes—so string-only truncation leaves the `150 KiB` payload untouched!

## Normative Authorities

- **`MCP-2026-07-28:OUTPUT-SCHEMA`** — MCP Specification (`2026-07-28`), *Tools `outputSchema` & `structuredContent`*.
- **`JSON-SCHEMA:2020-12`** — JSON Schema Draft `2020-12` (`array` item validation & `object` property typing).
- **Weaknesses:** `CWE-770` (Allocation of Resources Without Limits or Throttling), `CWE-400` (Uncontrolled Resource Consumption), `OWASP-API4:2023`, `OWASP-LLM10:2025` (Unbounded Consumption).

## Solution & Invariants

Enforce payload budgets (`max_bytes`, default `32,768`) inside middleware across **two orthogonal axes** while keeping `outputSchema` intact:
1. **Axis 1 — Schema-Valid Collection Cardinality Slicing:** When UTF-8 serialized JSON exceeds `max_bytes`, locate `list` fields (starting with largest lists such as `items`, `rows`, `events`, `datapoints`) and binary-search/proportionally slice their cardinality (`items[:k]`, keeping `k >= 1` when originally non-empty so `minItems: 1` or homogeneous `list[ItemModel]` / `list[int]` / `list[str]` schemas remain 100% valid). If the schema/dict includes `truncated: bool`, set `truncated = True`.
2. **Axis 2 — Proportional UTF-8 String Byte Shrinking:** If serialized JSON still exceeds `max_bytes` (e.g., a single item carries a `200 KiB` stack trace), proportionally truncate UTF-8 strings (`>= 16` bytes) cleanly on character boundaries and append `... [truncated]`.
3. **Axis 3 — Fail-Closed Hard Cap:** If an irreducible non-string scalar structure still exceeds `max_bytes`, raise a clear, actionable `PayloadBudgetExceededError` / `ToolError` instructing the caller to narrow filters—never emit unbounded payloads or corrupt JSON.

## Anti-Patterns

- Slicing raw JSON text (`json_str[:32768]`), producing unparseable JSON and breaking `structuredContent`.
- Setting `tool.outputSchema = None` globally in middleware.
- Shrinking only strings `>= 16` bytes while leaving `len(items) == 5000` unsliced.

## Verification Gates

- **3,000-Item Short-ID Torture Gate:** Feed `{"items": [f"id-{i:06d}" for i in range(3000)], "next_cursor": "c2"}` (`> 42 KiB`, every string `9` bytes) into `bound_structured_payload(..., max_bytes=32_768)` and assert:
  1. `len(json.dumps(bounded).encode("utf-8")) <= 32_768`,
  2. `isinstance(bounded["items"], list)` and `len(bounded["items"]) >= 1`,
  3. Every remaining item preserves its exact `9`-byte ID format without corruption.
