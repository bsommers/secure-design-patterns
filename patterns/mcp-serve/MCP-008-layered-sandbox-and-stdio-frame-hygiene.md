# MCP-008: Layered OS Sandboxing, `SEP-2577` Hygiene & `stdio` Frame Integrity

- **Domain:** `mcp-serve` (`MCP 2026-07-28`)
- **Severity:** `critical` · **Status:** `canonical`

[← Back to `mcp-serve` Index](README.md)

## Problem & Failure Mode

Two operational illusions routinely bite MCP server pipelines:
1. **`stdout` Pollution Corrupts `stdio` Transport:** Over `stdio`, the MCP client parses `stdout` as a strict stream of newline-delimited JSON-RPC 2.0 messages. A single `print("debug")` or noisy third-party startup banner written to `stdout` breaks JSON-RPC framing and disconnects the client—a failure invisible to in-memory unit tests that never spawn a real subprocess.
2. **Mistaking AST Linting for an OS Security Sandbox:** Static AST checks forbidding `import os`, `subprocess`, `socket`, `eval()`, and deprecated `SEP-2577` calls (`.sample()`, `.list_roots()`, `.set_logging_level()`) are invaluable **code-hygiene gates** on `src/tools/*.py`, **but they are NOT a security boundary** against an untrusted code-generation process or malicious dependency (`getattr(__builtins__, ...)` or setup hooks can trivially bypass naive AST checks unless contained by the OS kernel).

## Normative Authorities

- **`MCP-2026-07-28:STDIO-TRANSPORT`** — MCP `stdio` Transport Framing (`stdout` reserved exclusively for JSON-RPC; logs to `stderr`).
- **`MCP-2026-07-28:SEP-2577`** — Deprecation of Roots, Sampling, and Protocol-Level Logging in `2026-07-28`.
- **`SALTZER-SCHROEDER:1975`** — Defense in Depth & Economy of Mechanism.
- **Weaknesses:** `CWE-265` (Privilege / Sandbox Issues), `CWE-116` (Improper Encoding or Escaping of Output — Frame Corruption), `CWE-74` (Prompt Injection via Tool Docstrings), `OWASP-LLM05:2025`, `OWASP-LLM01:2025`.

## Solution & Invariants

1. **Structured `stderr`-Only Logging + Live Subprocess Probe:** Configure logging handlers explicitly on `sys.stderr`, enforce Ruff `T20` (`print()` ban), and spawn the real server binary over `PythonStdioTransport` during CI to verify `server/discover` (`protocolVersion == "2026-07-28"`) succeeds with zero `stdout` frame corruption.
2. **`SEP-2577` & Docstring Prompt-Injection AST Gate:** Audit all `@tool` ASTs to reject `.sample()`, `.list_roots()`, `.set_logging_level()`, and imperative prompt-injection phrasing (`"ignore previous instructions"`, `"you must always call"`, `"system prompt"`) in tool descriptions.
3. **Kernel-Level Containment for Untrusted Execution:** Run synthesis agents and untrusted verification inside real OS sandboxes:
   - **Containers:** `docker run --network=none --cap-drop=ALL --security-opt=no-new-privileges --read-only`.
   - **macOS Host Fallback:** `sandbox-exec` seatbelt profiles restricting `file-write*` to the narrow tool overlay and denying reads of `~/.ssh`, `~/.aws`, and `~/.config`.
   - **Linux Host Fallback:** `bwrap --ro-bind / / --unshare-net` with explicit writable bind mounts.

## Anti-Patterns

- Testing MCP servers exclusively with in-process `Client(mcp)` mocks and never testing real subprocess `stdio` framing before release.
- Claiming an AST linter "sandboxes" untrusted LLM-generated code on an unisolated host.

## Verification Gates

- **Gate 1 (Lint):** `ruff check --select T20,S` (`0` print statements, `0` Bandit findings).
- **Gate 2 (AST):** Zero `SEP-2577` deprecated calls and zero prompt-injection docstring triggers.
- **Gate 3 (Live `stdio` Subprocess):** Subprocess `server/discover` returns valid JSON-RPC `protocolVersion: "2026-07-28"` with clean `stdout`.
