# MCP-004: Cycle-Safe & Polymorphic Schema Projection

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `high` · **Status:** `canonical`
- **Reference Implementation:** [`../mcp_serve_ref/schema_normalizer.py`](../mcp_serve_ref/schema_normalizer.py)

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

Real-world enterprise OpenAPI 3.x specs (GitHub, Stripe, Jira, Kubernetes, Datadog) break naive OpenAPI-to-MCP generators in four distinct ways:
1. **Build-Time SSRF & Path Traversal via `$ref`:** Following `$ref: "https://internal.corp/schema.json"` triggers Server-Side Request Forgery, while `$ref: "../../etc/passwd"` traverses outside the spec workspace.
2. **Valid Cyclic `$ref` Graphs Crash Depth Counters:** Self-referential domain models (`User.manager -> #/components/schemas/User` or `Comment.replies -> Comment[]`) are completely valid OpenAPI, yet a naive recursive inliner without cycle tracking hits `depth > 25` and aborts ingestion.
3. **Polymorphic Erasure (`allOf` / `oneOf` / `anyOf`):** Schemas composed via `allOf: [$ref: BaseEntity, {properties: {datapoints: ...}}]` have no top-level `"properties"` key before merging, causing naive projectors to emit useless `{id, status}` stubs.
4. **Heuristic Metadata Bias:** Field rankers that boost `id`, `status`, `created_at`, and `updated_at` can fill the top-`N` field budget with audit boilerplate and drop the actual payload array (`rows`, `series`, `datapoints`, `line_items`).

## Normative Authorities

- **`JSON-SCHEMA:2020-12`** — JSON Schema Core Draft `2020-12` (§8.2.3 `$ref`, §10.2 `allOf`/`anyOf`/`oneOf`).
- **`IETF:RFC-6901`** — JSON Pointer (`~1` and `~0` token unescaping).
- **`OPENAPI:3.1.0`** — OpenAPI Specification v3.1.0 (§4.8.24 Schema Object).
- **Weaknesses:** `CWE-918` (SSRF), `CWE-22` (Path Traversal), `CWE-674` (Uncontrolled Recursion), `OWASP-API4:2023`, `OWASP-LLM10:2025`.

## Solution & Invariants

1. **Zero-Network, Path-Confined `$ref` Resolution:**
   - Reject any `$ref` with a URI scheme (`http://`, `https://`, `file://`).
   - Allow relative file `$ref`s (`./common/error.json#/Error`) **only** after verifying `(current_doc.parent / rel_path).resolve().is_relative_to(spec_root.resolve())`.
2. **Ancestor-Stack Cycle Breaking (`ancestor_refs: frozenset[str]`):**
   - Track canonical `<doc_rel_path>#/<json_pointer>` identifiers along the active call stack (not globally across sibling branches, so shared non-cyclic `$ref`s still inline everywhere!).
   - When `canonical_ref in ancestor_refs`, break the cycle deterministically into `{"type": "object", "properties": {"id": {"type": "string"}}, "x-mcp-cycle-broken": True}`.
3. **Composition Flattening & Data-Carrier Priority:**
   - Merge `allOf` `properties` and `required` sets recursively; unwrap 2-branch nullable `anyOf`/`oneOf` (`[T, {"type": "null"}]`) into `T` (`nullable=True`); merge common + discriminator variant fields on polymorphic objects.
   - Rank explicit `x-mcp-fields` allowlists highest (`+1000`), and rank structural data carriers (`rows`, `columns`, `series`, `datapoints`, `events`, `line_items`, `results` at `+75`) *above* generic audit timestamps (`*_at` at `+60`).

## Anti-Patterns

- Fetching `$ref` URLs with `urllib` or `httpx` during schema normalization.
- Tracking visited `$ref`s in a single global mutable `set` across sibling branches (which wrongly turns the second occurrence of `Timestamp` or `UserSummary` into a cycle stub even when no cycle exists!).
- Falling back to `data: dict[str, Any]` raw passthrough blobs.

## Verification Gates

- **SSRF & Traversal Gate:** Assert `https://...` and `../secret.json#/Key` raise `SchemaSecurityError`.
- **Cycle vs. Diamond Reuse Gate:** Assert `User.manager -> User` breaks the cycle cleanly while `Incident.reporter -> UserSummary` + `Incident.assignee -> UserSummary` (diamond reuse, non-cyclic) expands *both* sibling fields completely.
- **Polymorphic Data-Carrier Gate:** Assert an `allOf` metric schema retains `datapoints` ahead of `updated_at`.
