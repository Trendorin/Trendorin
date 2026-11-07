"""Pixel text: rasterizes Tiny5 (Latin, Cyrillic) and DotGothic16 (kana, kanji) without
anti-aliasing and turns the result into pixel sets or SVG paths. Needs Pillow.

Fonts are looked up with fc-match, then in assets/fonts/ and the usual font directories.
"""
import shutil
import subprocess
from functools import cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent

# family -> (file name, the size at which one font unit is one pixel)
FONTS = {
    "tiny5": ("Tiny5.ttf", 8),          # caps 5 px, x-height 4 px
    "dotgothic": ("DotGothic16-Regular.ttf", 16),  # 16 px kanji
}
SEARCH = [ROOT / "assets/fonts", Path.home() / ".local/share/fonts", Path("/usr/share/fonts")]


@cache
def _font(family: str) -> ImageFont.FreeTypeFont:
    file, size = FONTS[family]
    candidates = []
    if shutil.which("fc-match"):
        name = {"tiny5": "Tiny5", "dotgothic": "DotGothic16"}[family]
        out = subprocess.run(["fc-match", name, "--format=%{file}"], capture_output=True, text=True).stdout
        if Path(out).name == file:
            candidates.append(Path(out))
    for d in SEARCH:
        if d.exists():
            candidates += sorted(d.rglob(file))
    for c in candidates:
        if c.is_file():
            return ImageFont.truetype(str(c), size)
    raise SystemExit(f"font {file} not found: install it or put it in assets/fonts/")


def is_cjk(ch: str) -> bool:
    o = ord(ch)
    return 0x3000 <= o <= 0x30FF or 0x3400 <= o <= 0x9FFF or 0xFF00 <= o <= 0xFFEF


def text_pixels(text: str, family: str = "tiny5") -> tuple[int, int, set[tuple[int, int]]]:
    """(width, height, {(x, y)}) of `text` in the font's native pixel grid.

    Tiny5 lines are 9 px tall (caps from y=1 to y=5, descenders to y=6); DotGothic16 lines are 16 px.
    """
    font = _font(family)
    size = FONTS[family][1]
    w = max(1, int(font.getlength(text)) + 2)
    h = size + 4
    im = Image.new("1", (w, h), 0)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((0, 0), text, font=font, fill=1)
    px = im.load()
    pts = {(x, y) for y in range(h) for x in range(w) if px[x, y]}
    if family == "tiny5":
        # the em box at 8 px puts the cap line at y=2; shift so caps start at y=1
        pts = {(x, y - 1) for x, y in pts}
        h = 9
    else:
        pts = {(x, y - 4) for x, y in pts}  # DotGothic16 draws kanji at y=5..19
        h = 16
    width = int(font.getlength(text))
    return width, h, pts


def text_width(text: str, family: str = "tiny5") -> int:
    return int(_font(family).getlength(text))


def wrap(text: str, max_px: int, family: str = "tiny5") -> list[str]:
    """Greedy word wrap to a pixel width."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if cur and text_width(trial, family) > max_px:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def svg_path(pts: set[tuple[int, int]], scale: int = 1, ox: float = 0, oy: float = 0) -> str:
    """Pixels as one SVG path: horizontal runs merged, each run a scale-tall rectangle."""
    rows: dict[int, list[int]] = {}
    for x, y in pts:
        rows.setdefault(y, []).append(x)
    out = []
    for y in sorted(rows):
        xs = sorted(rows[y])
        start = prev = xs[0]
        for x in xs[1:] + [None]:
            if x is not None and x == prev + 1:
                prev = x
                continue
            n = (prev - start + 1) * scale
            out.append(f"M{ox + start * scale:g} {oy + y * scale:g}h{n}v{scale}h-{n}z")
            if x is not None:
                start = prev = x
    return "".join(out)
