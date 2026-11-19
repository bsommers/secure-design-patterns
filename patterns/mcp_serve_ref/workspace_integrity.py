"""Reference implementation of Pattern MCP-002: Immutable Chassis & Narrow Agent Overlay."""

from __future__ import annotations

import hashlib
import stat
from pathlib import Path


class TamperDetectionError(RuntimeError):
    """Raised when an untrusted step mutates or injects files into locked chassis paths."""


class LockedWorkspaceDigest:
    """Pre/post SHA-256 integrity monitor and byte restorer for locked Golden Template paths."""

    def __init__(self, workspace_root: Path, locked_rel_paths: tuple[str, ...]) -> None:
        self.workspace_root = workspace_root.resolve()
        self.locked_rel_paths = locked_rel_paths
        self._digests: dict[Path, str] = {}
        self._backups: dict[Path, bytes] = {}
        self._locked_dirs: list[Path] = []

    def snapshot_and_lock(self) -> None:
        """Record SHA-256 digests + byte backups and apply POSIX 0444 read-only mode."""
        self._digests.clear()
        self._backups.clear()
        self._locked_dirs.clear()

        for rel in self.locked_rel_paths:
            target = (self.workspace_root / rel).resolve()
            if not target.exists():
                continue
            if target.is_file():
                self._record_file(target)
            elif target.is_dir():
                self._locked_dirs.append(target)
                for child in sorted(target.rglob("*")):
                    if child.is_file() and "__pycache__" not in child.parts:
                        self._record_file(child)

    def _record_file(self, file_path: Path) -> None:
        raw = file_path.read_bytes()
        self._digests[file_path] = hashlib.sha256(raw).hexdigest()
        self._backups[file_path] = raw
        file_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)

    def verify_or_restore(self) -> None:
        """Verify all locked files match their pre-agent SHA-256; restore & raise on any drift."""
        violations: list[str] = []

        for file_path, expected_sha in self._digests.items():
            rel = file_path.relative_to(self.workspace_root)
            if not file_path.exists():
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_bytes(self._backups[file_path])
                violations.append(f"Deleted locked file restored: {rel}")
                continue

            actual_sha = hashlib.sha256(file_path.read_bytes()).hexdigest()
            if actual_sha != expected_sha:
                file_path.chmod(stat.S_IWUSR | stat.S_IRUSR)
                file_path.write_bytes(self._backups[file_path])
                file_path.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
                violations.append(f"Modified locked file restored: {rel}")

        for locked_dir in self._locked_dirs:
            for child in sorted(locked_dir.rglob("*")):
                if (
                    child.is_file()
                    and "__pycache__" not in child.parts
                    and child not in self._digests
                ):
                    rel = child.relative_to(self.workspace_root)
                    child.unlink(missing_ok=True)
                    violations.append(f"Unauthorized file in locked directory removed: {rel}")

        if violations:
            raise TamperDetectionError(
                "Locked chassis integrity violation(s) detected: " + "; ".join(violations)
            )
