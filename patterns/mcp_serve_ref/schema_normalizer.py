"""Reference implementation of Pattern MCP-004: Cycle-Safe & Polymorphic Schema Projection."""

from __future__ import annotations

import json
import urllib.parse
from pathlib import Path
from typing import Any


class SchemaNormalizationError(RuntimeError):
    """Raised when an OpenAPI/JSON Schema violates SSRF, path-confinement, or pointer rules."""


DATA_CARRIER_NAMES = frozenset(
    {
        "items",
        "rows",
        "columns",
        "series",
        "datapoints",
        "entries",
        "events",
        "results",
        "records",
        "line_items",
        "findings",
        "metrics",
    }
)
PRIMARY_ID_NAMES = frozenset({"id", "uid", "uuid", "key", "slug"})
CORE_SUMMARY_NAMES = frozenset({"name", "title", "status", "state", "severity", "summary", "type"})


def _resolve_json_pointer(doc: dict[str, Any], fragment: str) -> Any:
    if not fragment or fragment == "/":
        return doc
    if not fragment.startswith("/"):
        raise SchemaNormalizationError(f"Invalid RFC 6901 JSON Pointer fragment '{fragment}'.")
    current: Any = doc
    for raw_token in fragment.lstrip("/").split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and token in current:
            current = current[token]
        else:
            raise SchemaNormalizationError(
                f"Unresolvable JSON Pointer token '{token}' in '#{fragment}'."
            )
    return current


def resolve_schema_refs(
    node: Any,
    root_doc: dict[str, Any],
    *,
    spec_root_dir: Path,
    current_doc_path: Path,
    ancestor_refs: frozenset[str] = frozenset(),
    doc_cache: dict[Path, dict[str, Any]] | None = None,
) -> Any:
    """Resolve internal and path-confined relative JSON '$ref's while breaking recursive cycles."""
    root_dir = spec_root_dir.resolve()
    cur_path = current_doc_path.resolve()
    cache = doc_cache if doc_cache is not None else {cur_path: root_doc}

    if isinstance(node, list):
        return [
            resolve_schema_refs(
                item,
                root_doc,
                spec_root_dir=root_dir,
                current_doc_path=cur_path,
                ancestor_refs=ancestor_refs,
                doc_cache=cache,
            )
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    if "$ref" in node:
        raw_ref = node["$ref"]
        if not isinstance(raw_ref, str) or not raw_ref.strip():
            raise SchemaNormalizationError("Schema '$ref' must be a non-empty string.")

        parsed = urllib.parse.urlsplit(raw_ref)
        if parsed.scheme or parsed.netloc:
            raise SchemaNormalizationError(
                f"External or URI-schemed '$ref' forbidden (SSRF guard): '{raw_ref}'"
            )

        if parsed.path:
            target_path = (cur_path.parent / parsed.path).resolve()
            if not target_path.is_relative_to(root_dir):
                raise SchemaNormalizationError(
                    f"Relative '$ref' escapes spec root (path traversal guard): '{raw_ref}'"
                )
            if not target_path.is_file():
                raise SchemaNormalizationError(f"Referenced schema file not found: '{raw_ref}'")
            if target_path not in cache:
                cache[target_path] = json.loads(target_path.read_text(encoding="utf-8"))
            target_doc = cache[target_path]
        else:
            target_path = cur_path
            target_doc = cache.get(cur_path, root_doc)

        rel_doc_id = str(target_path.relative_to(root_dir))
        fragment = f"/{parsed.fragment.lstrip('/')}" if parsed.fragment else ""
        canonical_ref = f"{rel_doc_id}#{fragment}"

        if canonical_ref in ancestor_refs:
            return {
                "type": "object",
                "properties": {"id": {"type": "string"}},
                "x-mcp-cycle-broken": True,
            }

        resolved_target = _resolve_json_pointer(target_doc, fragment)
        sibling_overrides = {
            k: resolve_schema_refs(
                v,
                target_doc,
                spec_root_dir=root_dir,
                current_doc_path=target_path,
                ancestor_refs=ancestor_refs,
                doc_cache=cache,
            )
            for k, v in node.items()
            if k != "$ref"
        }
        inlined = resolve_schema_refs(
            resolved_target,
            target_doc,
            spec_root_dir=root_dir,
            current_doc_path=target_path,
            ancestor_refs=ancestor_refs | {canonical_ref},
            doc_cache=cache,
        )
        if isinstance(inlined, dict) and sibling_overrides:
            return {**inlined, **sibling_overrides}
        return inlined

    return {
        k: resolve_schema_refs(
            v,
            root_doc,
            spec_root_dir=root_dir,
            current_doc_path=cur_path,
            ancestor_refs=ancestor_refs,
            doc_cache=cache,
        )
        for k, v in node.items()
    }


def flatten_composed_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Flatten OpenAPI 3.x / JSON Schema 2020-12 allOf and nullable/polymorphic oneOf/anyOf."""
    result: dict[str, Any] = {
        k: v for k, v in schema.items() if k not in {"allOf", "oneOf", "anyOf"}
    }
    merged_props: dict[str, Any] = dict(result.get("properties", {}))
    merged_req: list[str] = list(result.get("required", []))

    if "allOf" in schema and isinstance(schema["allOf"], list):
        for sub in schema["allOf"]:
            if isinstance(sub, dict):
                flat_sub = flatten_composed_schema(sub)
                for prop_k, prop_v in flat_sub.get("properties", {}).items():
                    merged_props[prop_k] = prop_v
                for req_k in flat_sub.get("required", []):
                    if req_k not in merged_req:
                        merged_req.append(req_k)
        result["type"] = "object"

    for union_kw in ("anyOf", "oneOf"):
        variants = schema.get(union_kw)
        if not isinstance(variants, list) or not variants:
            continue
        non_null = [v for v in variants if isinstance(v, dict) and v.get("type") != "null"]
        has_null = len(non_null) < len(variants)
        if len(non_null) == 1:
            unwrapped = flatten_composed_schema(non_null[0])
            result.update(unwrapped)
            merged_props.update(unwrapped.get("properties", {}))
            if has_null:
                result["nullable"] = True
        elif len(non_null) > 1:
            for variant in non_null:
                flat_var = flatten_composed_schema(variant)
                for prop_k, prop_v in flat_var.get("properties", {}).items():
                    merged_props.setdefault(prop_k, prop_v)
            result.setdefault("type", "object")

    if merged_props:
        result["properties"] = {
            k: flatten_composed_schema(v) if isinstance(v, dict) else v
            for k, v in merged_props.items()
        }
    if merged_req:
        result["required"] = merged_req
    return result


def rank_projected_fields(
    schema: dict[str, Any],
    *,
    max_fields: int = 8,
    x_mcp_fields: list[str] | None = None,
) -> list[str]:
    """Select top-N fields, boosting x-mcp-fields and data carriers over audit metadata."""
    flat = flatten_composed_schema(schema)
    props = flat.get("properties", {})
    if not isinstance(props, dict) or not props:
        return []

    required_set = set(flat.get("required", []))
    explicit_order = {name: idx for idx, name in enumerate(x_mcp_fields or [])}

    scored: list[tuple[int, int, str]] = []
    for decl_idx, (name, prop_schema) in enumerate(props.items()):
        lower = name.lower()
        score = 10
        if name in explicit_order:
            score += 1000 - explicit_order[name]
        if lower in PRIMARY_ID_NAMES or lower.endswith("_id"):
            score += 90
        if lower in CORE_SUMMARY_NAMES:
            score += 80
        if lower in DATA_CARRIER_NAMES or (
            isinstance(prop_schema, dict) and prop_schema.get("type") == "array"
        ):
            score += 75
        if name in required_set:
            score += 65
        if lower.endswith("_at") or lower in {"created", "updated", "timestamp"}:
            score += 50
        scored.append((-score, decl_idx, name))

    scored.sort()
    return [name for _, _, name in scored[:max_fields]]
