# MCP-002: Immutable Chassis & Narrow Agent Overlay (Anti-Reward-Hacking)

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `critical` · **Status:** `canonical`
- **Reference Implementation:** [`../mcp_serve_ref/workspace_integrity.py`](../mcp_serve_ref/workspace_integrity.py)

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

When an LLM coding agent is tasked with generating or repairing MCP server code in a self-healing loop ("iterate until `validate_mcp.py` exits `0`"), giving it write access to the whole repository creates a classic **reward-hacking** incentive:
- If branch coverage is `72% < 85%`, the agent edits `--cov-fail-under=85` in `validate_mcp.py` or `pyproject.toml`.
- If a contract assertion rejects a missing `outputSchema`, the agent deletes the test in `tests/contract/`.
- In local host mode (without Docker), simply setting POSIX `chmod 0444` on locked files is **insufficient** because the agent runs under the same UID as the workspace owner and can run `chmod +w` before modifying a locked file.

## Normative Authorities

- **`SALTZER-SCHROEDER:1975`** — *Complete Mediation*, *Least Privilege*, and *Separation of Privilege*: An untrusted synthesis subject must never hold write capability over its own reference monitor or verification gate.
- **Weaknesses:** `CWE-284` (Improper Access Control), `CWE-353` (Missing Support for Integrity Check), `CWE-693` (Protection Mechanism Failure), `OWASP-LLM06:2025` (Excessive Agency), `OWASP-API8:2023`.

## Solution & Invariants

1. **Strict Chassis vs. Overlay Partition:**
   - **Locked Chassis (`:ro`):** `pyproject.toml`, `uv.lock`, `forge-manifest.json`, `src/auth.py`, `src/deps.py`, `src/server.py`, `tests/contract/**`, `scripts/validate_mcp.py`.
   - **Writable Overlay (`:rw`):** `src/tools/*.py`, `tests/unit/*.py`, `README.md`.
2. **Container Isolation (Primary):** Mount the workspace root read-only (`:ro`), bind-mount only writable directories `:rw`, drop all Linux capabilities (`--cap-drop=ALL`), and disable network access (`--network=none`).
3. **Cryptographic Pre/Post Integrity Guard (Host Defense-in-Depth):** Snapshot SHA-256 digests + raw bytes of every locked file (and detect unauthorized new files inside locked directories) *before* invoking a host coding agent. After the agent exits, verify every digest; on any mismatch, restore pristine bytes immediately and raise `TamperDetectionError` (aborting before test execution).

## Anti-Patterns

- Prompt-only boundaries (`"IMPORTANT: Do not modify tests/contract/*"` without filesystem/cryptographic enforcement).
- Relying on `chmod 0444` alone when host process UID equals file owner UID.

## Verification Gates

- **Tamper Simulation Test:** Simulate a rogue agent running `chmod 0644` and mutating a locked contract file; assert `LockedWorkspaceDigest.verify_or_restore()` restores the original bytes and raises `TamperDetectionError`.
- **Unexpected File Detection:** Simulate adding `src/evil_helper.py` in a locked directory; assert immediate detection and removal.
