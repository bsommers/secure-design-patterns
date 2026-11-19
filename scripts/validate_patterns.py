#!/usr/bin/env python3
"""Deterministic validator for Secure Design Pattern catalogs, authorities, and Markdown docs."""

from __future__ import annotations

import json
import re
import sys
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATTERN_HEADINGS = (
    "## Problem & Failure Mode",
    "## Normative Authorities",
    "## Solution & Invariants",
    "## Anti-Patterns",
    "## Verification Gates",
)

ID_RE = re.compile(r"^[A-Z]{2,8}-\d{3}$")
SLUG_RE = re.compile(r"^[a-z0-9-]+$")
CWE_RE = re.compile(r"^CWE-\d+$")
OWASP_RE = re.compile(r"^OWASP-(?:API|LLM)\d{1,2}:\d{4}$")
MD_LINK_RE = re.compile(r"!?\[[^\]]*\]\(((?:[^()]|\([^()]*\))+)\)")


def _strip_fenced_code(md_text: str) -> str:
    return re.sub(r"```.*?```", "", md_text, flags=re.DOTALL)


def load_registered_authorities(root: Path = ROOT) -> dict[str, dict[str, Any]]:
    """Load all authority IDs across authorities/*.json."""
    auth_dir = root / "authorities"
    registered: dict[str, dict[str, Any]] = {}
    for json_path in sorted(auth_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        for entry in payload.get("authorities", []):
            auth_id = entry["id"]
            if auth_id in registered:
                raise ValueError(f"Duplicate authority ID '{auth_id}' in {json_path}")
            registered[auth_id] = entry
    return registered


def validate_repository(root: Path = ROOT) -> list[str]:
    """Return a list of validation errors (empty list == 100% valid)."""
    errors: list[str] = []

    schema_path = root / "schema" / "pattern.schema.json"
    if not schema_path.is_file():
        return [f"Missing pattern schema: {schema_path}"]
    schema_doc = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema_doc.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        errors.append("schema/pattern.schema.json must target JSON Schema 2020-12.")

    try:
        authorities = load_registered_authorities(root)
    except Exception as exc:  # noqa: BLE001
        return [f"Authority registry error: {exc}"]

    if not authorities:
        errors.append("No authorities registered in authorities/*.json.")

    catalog_paths = sorted((root / "patterns").glob("*/catalog.json"))
    if not catalog_paths:
        errors.append("No patterns/*/catalog.json files found.")

    seen_pattern_ids: set[str] = set()

    for catalog_path in catalog_paths:
        domain_dir = catalog_path.parent
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        for req_key in ("domain", "title", "spec_version", "updated_at", "patterns"):
            if req_key not in catalog:
                errors.append(f"{catalog_path}: missing required top-level key '{req_key}'")

        patterns = catalog.get("patterns", [])
        if not isinstance(patterns, list) or not patterns:
            errors.append(f"{catalog_path}: 'patterns' must be a non-empty list")
            continue

        for entry in patterns:
            pid = entry.get("id", "")
            if not ID_RE.match(pid):
                errors.append(f"{catalog_path}: invalid pattern id '{pid}'")
            if pid in seen_pattern_ids:
                errors.append(f"{catalog_path}: duplicate pattern id '{pid}'")
            seen_pattern_ids.add(pid)

            if not SLUG_RE.match(entry.get("slug", "")):
                errors.append(f"{pid}: invalid slug '{entry.get('slug')}'")
            if entry.get("status") not in {"canonical", "draft", "deprecated"}:
                errors.append(f"{pid}: invalid status '{entry.get('status')}'")
            if entry.get("severity") not in {"critical", "high", "medium"}:
                errors.append(f"{pid}: invalid severity '{entry.get('severity')}'")

            if len(entry.get("invariants", [])) < 2:
                errors.append(f"{pid}: must define at least 2 invariants")
            if len(entry.get("anti_patterns", [])) < 1:
                errors.append(f"{pid}: must define at least 1 anti-pattern")
            if len(entry.get("verification_gates", [])) < 1:
                errors.append(f"{pid}: must define at least 1 verification gate")

            for auth_id in entry.get("authority_ids", []):
                if auth_id not in authorities:
                    errors.append(f"{pid}: unregistered authority_id '{auth_id}'")

            for cwe in entry.get("cwe_ids", []):
                if not CWE_RE.match(cwe):
                    errors.append(f"{pid}: invalid CWE identifier '{cwe}'")

            for owasp in entry.get("owasp_ids", []):
                if not OWASP_RE.match(owasp):
                    errors.append(f"{pid}: invalid OWASP identifier '{owasp}'")

            ref_mod = entry.get("reference_module")
            if ref_mod and not (root / ref_mod).is_file():
                errors.append(f"{pid}: missing reference_module '{ref_mod}'")

            md_file = domain_dir / entry.get("markdown_file", "")
            if not md_file.is_file():
                errors.append(f"{pid}: missing markdown file '{md_file}'")
            else:
                md_text = md_file.read_text(encoding="utf-8")
                for heading in REQUIRED_PATTERN_HEADINGS:
                    if heading not in md_text:
                        errors.append(
                            f"{pid} ({md_file.name}): missing required section '{heading}'"
                        )
                for auth_id in entry.get("authority_ids", []):
                    if auth_id not in md_text:
                        errors.append(
                            f"{pid} ({md_file.name}): authority '{auth_id}' not cited in Markdown"
                        )

    # Validate relative links across all Markdown files in the repo
    for md_path in sorted(root.rglob("*.md")):
        if ".venv" in md_path.parts:
            continue
        cleaned = _strip_fenced_code(md_path.read_text(encoding="utf-8"))
        for match in MD_LINK_RE.finditer(cleaned):
            raw_target = match.group(1).strip()
            if not raw_target or raw_target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            rel_part = urllib.parse.unquote(raw_target.split("#", 1)[0])
            if not rel_part:
                continue
            resolved = (md_path.parent / rel_part).resolve()
            if not resolved.exists():
                errors.append(
                    f"Broken relative link in {md_path.relative_to(root)}: '{raw_target}'"
                )

    return errors


def main() -> int:
    errors = validate_repository(ROOT)
    if errors:
        for err in errors:
            print(f"[FAIL] {err}", file=sys.stderr)
        return 1
    authorities = load_registered_authorities(ROOT)
    catalogs = list((ROOT / "patterns").glob("*/catalog.json"))
    total_patterns = sum(
        len(json.loads(c.read_text(encoding="utf-8"))["patterns"]) for c in catalogs
    )
    print(
        f"[PASS] Validated {total_patterns} secure design patterns across {len(catalogs)} "
        f"domain(s) against {len(authorities)} normative specification authorities."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
