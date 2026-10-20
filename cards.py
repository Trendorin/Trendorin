#!/usr/bin/env python3
"""Project cards for the profile README: python3 cards.py (needs engine.py's dependencies)."""
import re
from pathlib import Path

from engine import font, svg, text, themes, wrap, write

ROOT = Path(__file__).resolve().parent
W, H = 420, 124

PROJECTS = [
    ("luci-theme-pixel", "A monochrome pixel theme for the OpenWrt web interface", ["OpenWrt", "LuCI", "CSS"], "luci-theme-pixel"),
    ("Engram", "Memory scanner for Linux, Wine and AI agents", ["Rust", "Slint", "MCP"], "engram"),
    ("PkgScope", "See inside Linux packages before you install them", ["C++", "Qt 6", "sandbox"], "pkgscope"),
    ("Sotto", "Voice typing for Linux, local and fast", ["C++", "Qt 6", "whisper.cpp"], "sotto"),
]


def card(name, desc, tags, slug, t):
    raw = (ROOT / "assets/projects" / f"{slug}.svg").read_text()
    vb = re.search(r'viewBox="([^"]+)"', raw).group(1)
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", raw.strip())
    for i in set(re.findall(r'id="([^"]+)"', inner)):
        inner = inner.replace(f'id="{i}"', f'id="{slug}-{t.name}-{i}"').replace(f"#{i})", f"#{slug}-{t.name}-{i})")
    body = [f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="{t.card}" stroke="{t.border}"/>',
            f'<svg x="20" y="20" width="56" height="56" viewBox="{vb}">{inner}</svg>',
            text(name, 92, 38, 17, t.title, "semibold")]
    for i, line in enumerate(wrap(desc, 13.5, W - 112)[:2]):
        body.append(text(line, 92, 60 + 19 * i, 13.5, t.text))
    x = 20
    for tag in tags:
        w = font("medium").width(tag, 11.5) + 18
        body.append(f'<rect x="{x:g}" y="{H-36}" width="{w:g}" height="22" rx="11" fill="{t.tint}"/>')
        body.append(text(tag, x + w / 2, H - 21, 11.5, t.accent, "medium", "middle"))
        x += w + 8
    return svg(W, H, "".join(body), f"{name}: {desc}")


th = themes("#5b43e0", "#a397ff")
for name, desc, tags, slug in PROJECTS:
    write(ROOT / "assets", f"card-{slug}", {k: card(name, desc, tags, slug, t) for k, t in th.items()})
