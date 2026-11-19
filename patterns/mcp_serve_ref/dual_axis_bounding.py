"""Reference implementation of Pattern MCP-003: Dual-Axis Structured Payload Bounding."""

from __future__ import annotations

import copy
import json
from typing import Any


class PayloadBudgetExceededError(RuntimeError):
    """Raised when irreducible scalar structures exceed max_bytes after dual-axis bounding."""


def _wire_json_len(value: Any) -> int:
    # Measure conservative ensure_ascii=True wire length so surrogate-pair escapes
    # (\ud83d\udd25 = 12B vs 4B raw UTF-8) never exceed max_bytes under stdlib json.dumps().
    return len(json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8"))


def _slice_lists_proportionally(node: Any, keep_ratio: float) -> tuple[Any, bool]:
    """Slice list cardinalities while keeping >= 1 element on non-empty lists."""
    sliced_any = False
    if isinstance(node, list):
        if len(node) > 1:
            target_len = max(1, int(len(node) * keep_ratio))
            if target_len < len(node):
                node = node[:target_len]
                sliced_any = True
        new_items = []
        for item in node:
            updated_item, child_sliced = _slice_lists_proportionally(item, keep_ratio)
            new_items.append(updated_item)
            sliced_any = sliced_any or child_sliced
        return new_items, sliced_any

    if isinstance(node, dict):
        out: dict[str, Any] = {}
        for k, v in node.items():
            updated_v, child_sliced = _slice_lists_proportionally(v, keep_ratio)
            out[k] = updated_v
            sliced_any = sliced_any or child_sliced
        if sliced_any and "truncated" in out and isinstance(out["truncated"], bool):
            out["truncated"] = True
        return out, sliced_any

    return node, False


def _truncate_strings_proportionally(
    node: Any,
    scale: float,
    suffix: str = "... [truncated]",
) -> Any:
    """Shrink UTF-8 strings >= 16 bytes cleanly on character boundaries."""
    if isinstance(node, str):
        encoded = node.encode("utf-8")
        if len(encoded) < 16:
            return node
        suffix_bytes = suffix.encode("utf-8")
        budget = max(16, int(len(encoded) * scale))
        if budget >= len(encoded):
            return node
        keep_bytes = max(1, budget - len(suffix_bytes))
        trimmed = encoded[:keep_bytes].decode("utf-8", errors="ignore")
        return f"{trimmed}{suffix}"

    if isinstance(node, list):
        return [_truncate_strings_proportionally(item, scale, suffix) for item in node]

    if isinstance(node, dict):
        return {k: _truncate_strings_proportionally(v, scale, suffix) for k, v in node.items()}

    return node


def bound_structured_payload(
    payload: dict[str, Any],
    *,
    max_bytes: int = 32_768,
    truncation_suffix: str = "... [truncated]",
) -> dict[str, Any]:
    """Bound structured tool output below max_bytes without invalidating outputSchema.

    Pass 1 (Cardinality Axis): Binary-search list slicing (defeats 3,000-item short-ID bypass).
    Pass 2 (String Byte Axis): Proportional UTF-8 string truncation for oversized text blobs.
    Pass 3 (Fail-Closed Guard): Raise PayloadBudgetExceededError if scalars still exceed max_bytes.
    """
    if max_bytes < 64:
        raise ValueError("max_bytes must be >= 64")

    current = copy.deepcopy(payload)
    if _wire_json_len(current) <= max_bytes:
        return current

    # Pass 1: Binary search list cardinality ratio in [0.0005, 1.0]
    low, high = 0.0, 1.0
    best_sliced: dict[str, Any] | None = None
    for _ in range(14):
        mid = (low + high) / 2.0
        candidate, did_slice = _slice_lists_proportionally(current, mid)
        if not did_slice and mid < 0.01:
            break
        size = _wire_json_len(candidate)
        if size <= max_bytes:
            best_sliced = candidate
            low = mid
        else:
            high = mid

    if best_sliced is not None:
        return best_sliced

    # Minimum 1-item list slice still exceeds max_bytes; apply minimum slice first, then Pass 2
    min_sliced, _ = _slice_lists_proportionally(current, 0.0)
    current = dict(min_sliced)
    if _wire_json_len(current) <= max_bytes:
        return current

    # Pass 2: Binary search UTF-8 string byte scale
    s_low, s_high = 0.0, 1.0
    best_str_bounded: dict[str, Any] | None = None
    for _ in range(14):
        s_mid = (s_low + s_high) / 2.0
        str_candidate: dict[str, Any] = _truncate_strings_proportionally(
            current,
            s_mid,
            truncation_suffix,
        )
        if _wire_json_len(str_candidate) <= max_bytes:
            best_str_bounded = str_candidate
            s_low = s_mid
        else:
            s_high = s_mid

    if best_str_bounded is not None:
        return best_str_bounded

    raise PayloadBudgetExceededError(
        f"Structured payload exceeds {max_bytes}-byte budget after list and string bounding; "
        "narrow query filters or reduce requested page size."
    )
