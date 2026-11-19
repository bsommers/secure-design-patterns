# AGENTS.md — Secure Design Patterns Library

## 1. Purpose
This repository is a specification-grounded, machine-verifiable **Secure Design Patterns Library** pairing:
1. **Normative Authority Registries** (`authorities/*.json`) — Exact specification sections, RFCs, OWASP categories, and CWEs.
2. **Structured Pattern Catalogs & Markdown Specifications** (`patterns/<domain>/catalog.json` + `<ID>-<slug>.md`).
3. **Runnable, Strictly-Typed Reference Implementations** (`patterns/mcp_serve_ref/*.py`) proving each pattern defeats real-world edge cases and adversarial inputs.

## 2. Canonical Commands (Run from Repository Root)
- **Validate all pattern schemas, authority cross-references, required sections & relative links:**
  ```bash
  python3 scripts/validate_patterns.py
  ```
- **Run reference implementation & torture test suite:**
  ```bash
  pytest -q
  ```
- **Lint & strict typecheck:**
  ```bash
  ruff check patterns scripts tests && mypy patterns/mcp_serve_ref scripts
  ```

## 3. Authoring & Updating Patterns (Invariants)
1. **Authority Traceability Required:** Every pattern in `patterns/<domain>/catalog.json` MUST cite at least one primary normative specification authority registered in `authorities/*.json` plus concrete CWE/OWASP identifiers—never ungrounded folklore.
2. **Skeptical Failure Mode Grounding:** Every pattern MUST document the exact failure mode where naive implementations fall flat (e.g., 3,000-element short-string arrays bypassing string-only byte caps, cyclic `$ref` recursion crashes, `mcp==2.3.0` dropping `anyOf` header tools, or agent reward-hacking unlocked test suites).
3. **Executable Proof:** Security and bounding claims should be backed by deterministic reference code in `patterns/<domain>_ref/` and torture tests in `tests/`.
4. **Zero Broken Links:** Every Markdown file in the repository is checked by `scripts/validate_patterns.py` for required headings (`## Problem & Failure Mode`, `## Normative Authorities`, `## Solution & Invariants`, `## Anti-Patterns`, `## Verification Gates`) and valid relative links.
