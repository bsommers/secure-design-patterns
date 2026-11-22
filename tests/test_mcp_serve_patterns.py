"""Comprehensive verification & torture tests for mcp-serve Secure Design Patterns."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from patterns.mcp_serve_ref.dual_axis_bounding import (
    PayloadBudgetExceededError,
    bound_structured_payload,
)
from patterns.mcp_serve_ref.header_validator import (
    HeaderMirroringError,
    validate_x_mcp_header_param,
)
from patterns.mcp_serve_ref.route_dispatch_auth import (
    AuthConfigurationError,
    RouteAuthRule,
    SchemeBinding,
    ServerBoundRouteAuth,
)
from patterns.mcp_serve_ref.schema_normalizer import (
    SchemaNormalizationError,
    flatten_composed_schema,
    rank_projected_fields,
    resolve_schema_refs,
)
from patterns.mcp_serve_ref.workspace_integrity import (
    LockedWorkspaceDigest,
    TamperDetectionError,
)
from scripts.validate_patterns import ROOT, validate_repository


def test_catalog_authorities_and_markdown_links_are_valid() -> None:
    assert validate_repository(ROOT) == []


def test_mcp001_server_bound_route_auth_blocks_passthrough_and_routes_per_op() -> None:
    router = ServerBoundRouteAuth(
        default_scheme=SchemeBinding("bearer", "ACME_API_TOKEN"),
        named_schemes={
            "AdminKey": SchemeBinding("api_key_header", "ACME_ADMIN_KEY", "X-Admin-Key"),
        },
        route_rules=[
            RouteAuthRule("GET", "/health", "none"),
            RouteAuthRule("DELETE", "/admin/audit/{entry_id}", "AdminKey"),
        ],
        env={
            "ACME_API_TOKEN": "server-scoped-token",
            "ACME_ADMIN_KEY": "server-admin-secret",
        },
        base_path_prefix="/v1",
    )

    caller_headers = {"Authorization": "Bearer ATTACKER_CLIENT_PASSTHROUGH_TOKEN"}

    # Public security: [] route sends zero auth headers despite incoming MCP caller header
    assert (
        router.headers_for_request("GET", "/v1/health", incoming_mcp_headers=caller_headers) == {}
    )

    # Default route injects server-bound bearer token, never caller's token
    assert router.headers_for_request(
        "GET", "/v1/incidents/inc-42", incoming_mcp_headers=caller_headers
    ) == {"Authorization": "Bearer server-scoped-token"}

    # Admin route dispatches isolated API key
    assert router.headers_for_request(
        "DELETE", "/v1/admin/audit/99", incoming_mcp_headers=caller_headers
    ) == {"X-Admin-Key": "server-admin-secret"}


def test_mcp001_missing_env_or_unknown_scheme_fails_closed() -> None:
    with pytest.raises(AuthConfigurationError, match="unknown scheme"):
        ServerBoundRouteAuth(
            default_scheme=None,
            named_schemes={},
            route_rules=[RouteAuthRule("GET", "/x", "GhostScheme")],
            env={},
        )

    router = ServerBoundRouteAuth(
        default_scheme=SchemeBinding("bearer", "MISSING_TOKEN"),
        named_schemes={},
        route_rules=[],
        env={},
    )
    with pytest.raises(AuthConfigurationError, match="MISSING_TOKEN"):
        router.headers_for_request("GET", "/items")


def test_mcp002_locked_workspace_digest_restores_modified_deleted_and_rogue_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "src" / "tools").mkdir(parents=True)
    (tmp_path / "tests" / "contract").mkdir(parents=True)

    auth_file = tmp_path / "src" / "auth.py"
    contract_file = tmp_path / "tests" / "contract" / "test_gate.py"
    tool_file = tmp_path / "src" / "tools" / "get_item.py"

    auth_file.write_text("STRICT_AUTH = True\n", encoding="utf-8")
    contract_file.write_text("assert STRICT_AUTH\n", encoding="utf-8")
    tool_file.write_text("def ok(): return 1\n", encoding="utf-8")

    guard = LockedWorkspaceDigest(tmp_path, ("src/auth.py", "tests/contract"))
    guard.snapshot_and_lock()

    # Editing writable overlay succeeds cleanly
    tool_file.write_text("def ok(): return 2\n", encoding="utf-8")
    guard.verify_or_restore()

    # Simulate rogue agent running chmod +w on src/auth.py and injecting a file in tests/contract
    auth_file.chmod(stat.S_IWUSR | stat.S_IRUSR)
    auth_file.write_text("STRICT_AUTH = False\n", encoding="utf-8")
    rogue_file = tmp_path / "tests" / "contract" / "conftest_override.py"
    rogue_file.write_text("# weaken gate\n", encoding="utf-8")

    with pytest.raises(TamperDetectionError, match="src/auth.py"):
        guard.verify_or_restore()

    assert auth_file.read_text(encoding="utf-8") == "STRICT_AUTH = True\n"
    assert not rogue_file.exists()


def test_mcp003_dual_axis_bounding_defeats_3000_short_id_array_bypass() -> None:
    # Every string is 10 bytes (< 16 bytes), yet 3,500 items serialize to ~49 KiB (> 32 KiB)
    payload = {
        "items": [f"inc-{i:06d}" for i in range(3500)],
        "next_cursor": "cur-2",
        "truncated": False,
    }
    raw_bytes = len(json.dumps(payload).encode("utf-8"))
    assert raw_bytes > 45_000

    bounded = bound_structured_payload(payload, max_bytes=32_768)
    bounded_bytes = len(json.dumps(bounded, separators=(",", ":")).encode("utf-8"))

    assert bounded_bytes <= 32_768
    assert isinstance(bounded["items"], list)
    assert 1 <= len(bounded["items"]) < 3500
    assert bounded["items"][0] == "inc-000000"
    assert bounded["truncated"] is True


def test_mcp003_dual_axis_bounding_truncates_oversized_utf8_strings_and_fails_closed() -> None:
    huge_trace = {"id": "inc-1", "stacktrace": "🔥error-frame-" * 4000}
    bounded = bound_structured_payload(huge_trace, max_bytes=4096)
    assert len(json.dumps(bounded, separators=(",", ":")).encode("utf-8")) <= 4096
    assert bounded["stacktrace"].endswith("... [truncated]")

    # Irreducible scalar dictionary (keys + integer values, single-element lists) exceeding tiny cap
    irreducible = {f"metric_counter_{i:03d}": 123456789 for i in range(40)}
    with pytest.raises(PayloadBudgetExceededError):
        bound_structured_payload(irreducible, max_bytes=128)


def test_mcp004_cycle_safe_and_diamond_schema_resolution(tmp_path: Path) -> None:
    common_dir = tmp_path / "common"
    common_dir.mkdir()
    (common_dir / "tag.json").write_text(
        json.dumps({"Tag": {"type": "object", "properties": {"key": {"type": "string"}}}}),
        encoding="utf-8",
    )

    spec_file = tmp_path / "openapi.json"
    root_doc = {
        "components": {
            "schemas": {
                "UserSummary": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string"},
                        "manager": {"$ref": "#/components/schemas/UserSummary"},
                    },
                },
                "Incident": {
                    "type": "object",
                    "properties": {
                        "reporter": {"$ref": "#/components/schemas/UserSummary"},
                        "assignee": {"$ref": "#/components/schemas/UserSummary"},
                        "tag": {"$ref": "./common/tag.json#/Tag"},
                    },
                },
            }
        }
    }
    spec_file.write_text(json.dumps(root_doc), encoding="utf-8")

    resolved = resolve_schema_refs(
        {"$ref": "#/components/schemas/Incident"},
        root_doc,
        spec_root_dir=tmp_path,
        current_doc_path=spec_file,
    )

    # Both diamond siblings expand UserSummary, while self-cycle UserSummary.manager breaks cleanly
    assert "email" in resolved["properties"]["reporter"]["properties"]
    assert "email" in resolved["properties"]["assignee"]["properties"]
    assert resolved["properties"]["reporter"]["properties"]["manager"]["x-mcp-cycle-broken"] is True
    assert "key" in resolved["properties"]["tag"]["properties"]


def test_mcp004_ssrf_and_path_traversal_refs_rejected(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec.json"
    spec_file.write_text("{}", encoding="utf-8")

    with pytest.raises(SchemaNormalizationError, match="SSRF"):
        resolve_schema_refs(
            {"$ref": "https://attacker.example/evil.json#/A"},
            {},
            spec_root_dir=tmp_path,
            current_doc_path=spec_file,
        )

    with pytest.raises(SchemaNormalizationError, match="traversal"):
        resolve_schema_refs(
            {"$ref": "../outside.json#/Secret"},
            {},
            spec_root_dir=tmp_path,
            current_doc_path=spec_file,
        )


def test_mcp004_allof_and_data_carrier_ranking_preserves_datapoints() -> None:
    composed = {
        "allOf": [
            {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string"},
                    "created_at": {"type": "string"},
                    "updated_at": {"type": "string"},
                    "deleted_at": {"type": "string"},
                },
            },
            {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "datapoints": {"type": "array", "items": {"type": "number"}},
                    "nullable_note": {
                        "anyOf": [{"type": "string"}, {"type": "null"}],
                    },
                },
            },
        ]
    }
    flat = flatten_composed_schema(composed)
    assert flat["properties"]["nullable_note"]["nullable"] is True

    top4 = rank_projected_fields(composed, max_fields=4)
    assert "id" in top4
    assert "name" in top4
    assert "datapoints" in top4


def test_mcp007_x_mcp_header_validator_catches_anyof_rfc9110_and_secrets() -> None:
    # Valid non-union primitive Idempotency-Key succeeds
    assert (
        validate_x_mcp_header_param(
            "idempotency_key",
            {"type": "string", "default": "", "x-mcp-header": "Idempotency-Key"},
        )
        == "Idempotency-Key"
    )

    # Nullable str | None (anyOf) rejected because mcp==2.3.0 drops the tool silently
    with pytest.raises(HeaderMirroringError, match="anyOf"):
        validate_x_mcp_header_param(
            "idempotency_key",
            {
                "anyOf": [{"type": "string"}, {"type": "null"}],
                "x-mcp-header": "Idempotency-Key",
            },
        )

    # Invalid RFC 9110 header name (contains space/CRLF)
    with pytest.raises(HeaderMirroringError, match="1\\*tchar"):
        validate_x_mcp_header_param(
            "trace_id",
            {"type": "string", "x-mcp-header": "X-Bad Header"},
        )

    # Sensitive token parameter blocked
    with pytest.raises(HeaderMirroringError, match="sensitive"):
        validate_x_mcp_header_param(
            "upstream_api_token",
            {"type": "string", "x-mcp-header": "X-Upstream-Auth"},
        )


def test_brand_svg_and_png_assets_are_valid() -> None:
    import xml.etree.ElementTree as ET

    png_magic = b"\x89PNG\r\n\x1a\n"
    for rel_svg in ("assets/logo.svg", "docs/assets/icon.svg", "docs/assets/logo.svg"):
        svg_text = (ROOT / rel_svg).read_text(encoding="utf-8")
        root = ET.fromstring(svg_text)  # noqa: S314
        assert root.tag.endswith("svg")
        assert "@import" not in svg_text
        stripped = svg_text.replace("http://www.w3.org/2000/svg", "")
        assert "http://" not in stripped and "https://" not in stripped

    for rel_png in (
        "assets/logo.png",
        "docs/assets/icon.png",
        "docs/assets/logo.png",
        "docs/assets/hero-illustration.png",
    ):
        raw = (ROOT / rel_png).read_bytes()
        assert len(raw) > 128
        assert raw.startswith(png_magic)
