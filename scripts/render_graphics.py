#!/usr/bin/env python3
"""Deterministic Blue-Note Prism Art-Deco Cyber-Jazz SVG + PNG generator."""

from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"
MONO = "ui-monospace, 'Cascadia Code', 'Fira Code', Menlo, Consolas, monospace"


def _defs(prefix: str) -> str:
    return f"""  <defs>
    <linearGradient id="{prefix}-bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#040714"/>
      <stop offset="52%" stop-color="#09122c"/>
      <stop offset="100%" stop-color="#050816"/>
    </linearGradient>
    <linearGradient id="{prefix}-gold" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#fde047"/>
      <stop offset="50%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#d97706"/>
    </linearGradient>
    <linearGradient id="{prefix}-prism" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00e5ff" stop-opacity="0.95"/>
      <stop offset="55%" stop-color="#0284c7" stop-opacity="0.88"/>
      <stop offset="100%" stop-color="#10b981" stop-opacity="0.92"/>
    </linearGradient>
    <pattern id="{prefix}-grid" width="32" height="32" patternUnits="userSpaceOnUse">
      <path d="M 32 0 L 0 0 0 32" fill="none" stroke="#00e5ff"
            stroke-opacity="0.11" stroke-width="1"/>
      <circle cx="0" cy="0" r="1.3" fill="#38bdf8" fill-opacity="0.24"/>
    </pattern>
    <filter id="{prefix}-glow" x="-25%" y="-25%" width="150%" height="150%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>"""


def _emblem_group(cx: float, cy: float, scale: float, prefix: str) -> str:
    # Art-Deco sunburst rays + octagonal shield + sapphire prism + 8 harmonic pattern beams
    sun_lines: list[str] = []
    for idx in range(12):
        ang = math.radians(-150 + idx * (120 / 11))
        x1 = cx + math.cos(ang) * 112 * scale
        y1 = cy + math.sin(ang) * 112 * scale
        x2 = cx + math.cos(ang) * 148 * scale
        y2 = cy + math.sin(ang) * 148 * scale
        sun_lines.append(
            f'    <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="url(#{prefix}-gold)" stroke-width="{3.2 * scale:.1f}" '
            'stroke-linecap="round"/>'
        )

    oct_pts: list[str] = []
    for i in range(8):
        a = math.radians(22.5 + i * 45)
        ox = cx + math.cos(a) * 124 * scale
        oy = cy + math.sin(a) * 124 * scale
        oct_pts.append(f"{ox:.1f},{oy:.1f}")

    # Incoming crimson ray on left -> split into 8 crisp cyan/emerald harmonic beams on right
    beams: list[str] = []
    colors = [
        "#00e5ff",
        "#38bdf8",
        "#00ff9d",
        "#fbbf24",
        "#00e5ff",
        "#38bdf8",
        "#00ff9d",
        "#fbbf24",
    ]
    for b_idx in range(8):
        y_off = (-56 + b_idx * 16) * scale
        bx1, by1 = cx + 26 * scale, cy + y_off * 0.35
        bx2, by2 = cx + 146 * scale, cy + y_off * 1.18
        beams.append(
            f'    <line x1="{bx1:.1f}" y1="{by1:.1f}" x2="{bx2:.1f}" y2="{by2:.1f}" '
            f'stroke="{colors[b_idx]}" stroke-width="{3.4 * scale:.1f}" '
            f'stroke-linecap="round" filter="url(#{prefix}-glow)"/>'
        )
        beams.append(
            f'    <circle cx="{bx2:.1f}" cy="{by2:.1f}" r="{4.2 * scale:.1f}" '
            f'fill="{colors[b_idx]}"/>'
        )

    p_top = f"{cx:.1f},{cy - 78 * scale:.1f}"
    p_right = f"{cx + 68 * scale:.1f},{cy + 46 * scale:.1f}"
    p_left = f"{cx - 68 * scale:.1f},{cy + 46 * scale:.1f}"
    p_mid = f"{cx:.1f},{cy + 10 * scale:.1f}"

    in_x1, in_y1 = cx - 148 * scale, cy + 18 * scale
    in_x2, in_y2 = cx - 32 * scale, cy - 4 * scale

    return "\n".join(
        [
            "  <g>",
            *sun_lines,
            f'    <polygon points="{" ".join(oct_pts)}" fill="#081229" fill-opacity="0.94" '
            f'stroke="url(#{prefix}-gold)" stroke-width="{5.0 * scale:.1f}"/>',
            f'    <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{98 * scale:.1f}" fill="none" '
            f'stroke="#00e5ff" stroke-opacity="0.45" stroke-width="{2.0 * scale:.1f}" '
            f'stroke-dasharray="{8 * scale:.1f} {6 * scale:.1f}"/>',
            f'    <line x1="{in_x1:.1f}" y1="{in_y1:.1f}" x2="{in_x2:.1f}" y2="{in_y2:.1f}" '
            f'stroke="#ff2a85" stroke-width="{5.5 * scale:.1f}" stroke-linecap="round" '
            f'filter="url(#{prefix}-glow)"/>',
            *beams,
            f'    <polygon points="{p_top} {p_right} {p_left}" fill="url(#{prefix}-prism)" '
            f'stroke="#f0f6fc" stroke-width="{3.5 * scale:.1f}" filter="url(#{prefix}-glow)"/>',
            f'    <polygon points="{p_top} {p_right} {p_mid}" fill="#f8fafc" fill-opacity="0.22"/>',
            f'    <circle cx="{cx:.1f}" cy="{cy - 8 * scale:.1f}" r="{8.5 * scale:.1f}" '
            f'fill="#fde047"/>',
            "  </g>",
        ]
    )


def build_square_icon_svg() -> str:
    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" '
            'width="512" height="512">',
            _defs("sdp-sq"),
            '  <rect width="512" height="512" rx="92" fill="url(#sdp-sq-bg)"/>',
            '  <rect width="512" height="512" rx="92" fill="url(#sdp-sq-grid)"/>',
            '  <rect x="22" y="22" width="468" height="468" rx="74" fill="none" '
            'stroke="url(#sdp-sq-gold)" stroke-width="4" stroke-opacity="0.85"/>',
            _emblem_group(256.0, 266.0, 1.42, "sdp-sq"),
            "</svg>",
            "",
        ]
    )


def build_hero_banner_svg() -> str:
    # Art-Deco jazz equalizer bars along bottom-right
    eq_bars: list[str] = []
    heights = [18, 34, 52, 28, 64, 42, 74, 38, 56, 26, 46, 20]
    for i, h in enumerate(heights):
        bx = 945 + i * 18
        by = 324 - h
        col = "#fbbf24" if i % 3 == 0 else ("#00e5ff" if i % 2 == 0 else "#00ff9d")
        eq_bars.append(
            f'  <rect x="{bx}" y="{by}" width="10" height="{h}" rx="3" '
            f'fill="{col}" fill-opacity="0.82"/>'
        )

    return "\n".join(
        [
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 360" '
            'width="1200" height="360">',
            _defs("sdp-hero"),
            '  <rect width="1200" height="360" rx="24" fill="url(#sdp-hero-bg)"/>',
            '  <rect width="1200" height="360" rx="24" fill="url(#sdp-hero-grid)"/>',
            '  <rect x="14" y="14" width="1172" height="332" rx="18" fill="none" '
            'stroke="url(#sdp-hero-gold)" stroke-width="2.5" stroke-opacity="0.8"/>',
            '  <path d="M 30 54 L 30 30 L 66 30 M 1170 54 L 1170 30 L 1134 30 '
            'M 30 306 L 30 330 L 66 330 M 1170 306 L 1170 330 L 1134 330" '
            'fill="none" stroke="#00e5ff" stroke-width="3"/>',
            _emblem_group(196.0, 186.0, 1.02, "sdp-hero"),
            f'  <text x="380" y="92" fill="#fbbf24" font-family="{MONO}" font-size="14" '
            'font-weight="700">BLUE-NOTE PRISM CATALOG  //  MCP 2026-07-28</text>',
            f'  <text x="378" y="152" fill="#f8fafc" font-family="{SANS}" font-size="44" '
            'font-weight="800">SECURE DESIGN PATTERNS</text>',
            f'  <text x="380" y="196" fill="#94a3b8" font-family="{SANS}" font-size="19" '
            'font-weight="500">Specification-Derived Authorities, Anti-Patterns &amp; '
            "Runnable Python Proofs</text>",
            '  <g transform="translate(380, 232)">',
            '    <rect width="192" height="40" rx="8" fill="#0b1936" '
            'stroke="#00e5ff" stroke-width="1.5"/>',
            f'    <text x="96" y="25" text-anchor="middle" fill="#00e5ff" font-family="{MONO}" '
            'font-size="13" font-weight="700">8 MCP-SERVE PATTERNS</text>',
            "  </g>",
            '  <g transform="translate(584, 232)">',
            '    <rect width="208" height="40" rx="8" fill="#0b1936" '
            'stroke="#00ff9d" stroke-width="1.5"/>',
            f'    <text x="104" y="25" text-anchor="middle" fill="#00ff9d" font-family="{MONO}" '
            'font-size="13" font-weight="700">13 NORMATIVE AUTHORITIES</text>',
            "  </g>",
            '  <g transform="translate(804, 232)">',
            '    <rect width="198" height="40" rx="8" fill="#0b1936" '
            'stroke="#fbbf24" stroke-width="1.5"/>',
            f'    <text x="99" y="25" text-anchor="middle" fill="#fde047" font-family="{MONO}" '
            'font-size="13" font-weight="700">JSON SCHEMA 2020-12</text>',
            "  </g>",
            f'  <text x="380" y="314" fill="#5eead4" font-family="{MONO}" font-size="13">'
            "$ python3 scripts/validate_patterns.py  -&gt;  [PASS] 8/8 canonical patterns"
            "</text>",
            *eq_bars,
            "</svg>",
            "",
        ]
    )


def _rasterize(svg_path: Path, png_path: Path, width: int) -> None:
    import tempfile

    magick = shutil.which("magick")
    if not magick:
        raise RuntimeError("ImageMagick 'magick' binary required to rasterize PNG assets.")
    clean = (
        svg_path.read_text(encoding="utf-8")
        .replace(f'font-family="{SANS}"', 'font-family="Helvetica"')
        .replace(f'font-family="{MONO}"', 'font-family="Menlo"')
    )
    with tempfile.NamedTemporaryFile(suffix=".svg", mode="w", encoding="utf-8") as tmp:
        tmp.write(clean)
        tmp.flush()
        cmd = [
            magick,
            "-font",
            "/System/Library/Fonts/Helvetica.ttc",
            "-background",
            "none",
            tmp.name,
            "-resize",
            f"{width}x",
            str(png_path),
        ]
        subprocess.run(cmd, check=True)  # noqa: S603


def main() -> int:
    sq = build_square_icon_svg()
    for rel_svg, rel_png in [
        ("assets/logo.svg", "assets/logo.png"),
        ("docs/assets/icon.svg", "docs/assets/icon.png"),
    ]:
        sp = ROOT / rel_svg
        pp = ROOT / rel_png
        sp.parent.mkdir(parents=True, exist_ok=True)
        sp.write_text(sq, encoding="utf-8")
        _rasterize(sp, pp, 512)

    hero_svg = ROOT / "docs" / "assets" / "logo.svg"
    hero_png = ROOT / "docs" / "assets" / "logo.png"
    hero_svg.write_text(build_hero_banner_svg(), encoding="utf-8")
    _rasterize(hero_svg, hero_png, 1200)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
