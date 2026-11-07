#!/usr/bin/env python3
"""Draws the vertical posters in assets/posters/: pixel-art scenes in a strict Japanese style, each a
seamless loop. Needs Pillow. profile.toml picks the one the README shows.

    python3 poster.py              # every scene
    python3 poster.py tsuki ame    # only these

    tsuki  月  a torii in still water under a winter moon, Fuji behind it, snow falling
    yu     夕  ukiyo-e evening: a red sun on paper sky, Fuji, cranes, a sail on the bay
    ame    雨  night rain on a red arched bridge, a paper umbrella, lanterns, a willow
    take   竹  a bamboo grove at dawn, mist, a ronin on the path, torii further in

Scenes are drawn at 128x228 and scaled 3x with nearest neighbour. When ImageMagick is installed the
GIFs go through `-layers Optimize` to get smaller.
"""
import math
import random
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

from pixfont import text_pixels

ROOT = Path(__file__).resolve().parent
OUTDIR = ROOT / "assets/posters"

W, H, SCALE = 128, 228, 3
FRAMES, DELAY = 144, 100           # a 14.4 s loop
L, R, T, B = 5, W - 6, 5, H - 6    # inside of the frame
TAU = 2 * math.pi
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]


def hexc(s: str) -> tuple[int, int, int]:
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, t: float):
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t), round(a[2] + (b[2] - a[2]) * t))


def bayer(x: int, y: int) -> float:
    return (BAYER[y & 3][x & 3] + 0.5) / 16


MAT, FRAME_LINE = hexc("#08090d"), hexc("#3c3f50")
SEAL, SEAL_INK = hexc("#b8321f"), hexc("#efe6cf")
SHU, SHU_LIT, SHU_DARK = hexc("#c23a28"), hexc("#e0603f"), hexc("#7e2016")


def canvas(c=MAT):
    return [[c] * W for _ in range(H)]


def copy(img):
    return [row[:] for row in img]


def put(img, x, y, c):
    if L <= x <= R and T <= y <= B:
        img[y][x] = c


# ---------------------------------------------------------------- shared drawing

def gradient(img, y0, y1, stops, x0=L, x1=R):
    """Vertical bands of `stops` with a dithered seam between neighbours."""
    n = len(stops) - 1
    for y in range(y0, y1 + 1):
        v = (y - y0) / max(1, y1 - y0) * n
        i = min(int(v), n - 1)
        f = min(1.0, max(0.0, (v - i - 0.5) * 2.5 + 0.5))
        for x in range(x0, x1 + 1):
            img[y][x] = stops[i + 1] if f > bayer(x, y) else stops[i]


def halo(img, cx, cy, r, reach, color, strength=0.55):
    for y in range(max(T, int(cy - r - reach)), min(B, int(cy + r + reach)) + 1):
        for x in range(max(L, int(cx - r - reach)), min(R, int(cx + r + reach)) + 1):
            d = math.hypot(x - cx, y - cy)
            if r < d < r + reach:
                step = int((1 - (d - r) / reach) ** 1.6 * 4 + bayer(x, y) * 0.999)
                if step:
                    img[y][x] = mix(img[y][x], color, step / 4 * strength)


def kasumi(length: int, rows: int) -> list[tuple[int, int]]:
    """A suyari-gasumi band: flat, with rounded ends. Rows of (dx, length)."""
    if rows <= 2:
        return [(1, length - 2), (0, length)][:rows]
    return [(2, length - 4)] + [(0, length)] * (rows - 2) + [(1, length - 2)]


def strips(img, t, strips_, paint, skip=None):
    """Bands on strips that wrap with their period and travel one period per loop.
    strips_: [(top y, period, travel, [(x, band)])]; paint(x, y, row, rows, colour) -> colour."""
    for sy, period, travel, bands in strips_:
        shift = round(t * travel)
        for x0, band in bands:
            for dy, (dx, length) in enumerate(band):
                y = sy + dy
                for k in range(length):
                    x = L + (x0 + dx + k + shift) % period
                    while x <= R:
                        if not (skip and skip(x, y)):
                            img[y][x] = paint(x, y, dy, len(band), img[y][x])
                        x += period


def water(img, axis, y0, y1, t, top, bottom, fade=(0.42, 0.72), amp=(0.4, 3.0), ripple=None,
          sprite=None, sprite_axis=0):
    """Rows y0..y1 become water reflecting the picture above `axis` (and `sprite` above its own axis).
    Returns the sideways wobble of every row."""
    wobs = {}
    for y in range(y0, y1 + 1):
        d = (y - y0) / max(1, y1 - y0)
        base = mix(top, bottom, d)
        a = amp[0] + (amp[1] - amp[0]) * d
        wob = round(a * math.sin(TAU * t * 3 + y * 0.83) + 0.5 * a * math.sin(TAU * t * 4 - y * 0.41))
        wobs[y] = wob
        k = fade[0] + (fade[1] - fade[0]) * d
        sy = 2 * axis - 1 - y
        rip = ripple is not None and math.sin(y * 0.55 - TAU * t * 6) > 0.86
        gy = 2 * sprite_axis - y
        row = img[y]
        for x in range(L, R + 1):
            sx = min(R, max(L, x + wob))
            c = mix(img[sy][sx], base, k) if sy >= T else base
            if sprite and y > sprite_axis:
                g = sprite.get((sx, gy))
                if g:
                    c = mix(g, base, k - 0.04)
            if rip:
                c = mix(c, ripple, 0.4)
            row[x] = c
    return wobs


def mist(img, y0, y1, center, sigma, t, color, strength=(0.2, 0.32)):
    for y in range(max(T, y0), min(B, y1) + 1):
        prof = math.exp(-((y - center) / sigma) ** 2)
        for x in range(L, R + 1):
            n = (0.55 * math.sin(TAU * (x / 64 - t)) + 0.45 * math.sin(TAU * (x / 40 + t) + y * 0.4)) * 0.5 + 0.5
            v = prof * (0.35 + 0.75 * n)
            if v > 0.25 + bayer(x, y) * 0.7:
                img[y][x] = mix(img[y][x], color, strength[1] if v > 0.6 else strength[0])


def falling(t, top, ground, frac, m):
    """Height of something that falls from `top` to `ground` m times per loop."""
    span = ground - top
    return top + (frac * span + t * span * m) % span


def pads(put_, pads_, color, lit=None, trunk=None):
    """Flat needle pads of a black pine: (cx, cy, half width, half height). With `trunk` (a list of
    points) every pad gets a branch from the nearest trunk point."""
    for cx, cy, rw, rh in pads_:
        if trunk:
            tx, ty = min(trunk, key=lambda q: (q[0] - cx) ** 2 + (q[1] - cy) ** 2)
            n = int(max(abs(cx - tx), abs(cy - ty)))
            for i in range(n + 1):
                put_(round(tx + (cx - tx) * i / max(1, n)), round(ty + (cy - ty) * i / max(1, n)) + (1 if 0 < i < n * 0.6 else 0), color)
        for yy in range(int(cy - rh - 1), int(cy + rh + 2)):
            for xx in range(int(cx - rw - 1), int(cx + rw + 2)):
                e = ((xx - cx) / rw) ** 2 + ((yy - cy) / rh) ** 2
                if e <= 1 or (e <= 1.35 and (xx * 7 + yy * 3) % 5 == 0):
                    put_(xx, yy, lit if lit and yy <= cy - rh + 0.6 and xx < cx + rw * 0.6 else color)


def pagoda(put_, px, base, color, lit=None, tiers=((7, 21), (6, 18), (5, 15), (5, 13), (4, 11))):
    y = base
    for i, (body, roof) in enumerate(tiers):
        h = 4 if i else 5
        for yy in range(y - h + 1, y + 1):
            for xx in range(px - body // 2, px + body // 2 + 1):
                put_(xx, yy, color)
        y -= h
        for xx in range(px - roof // 2, px + roof // 2 + 1):  # roof, with upturned eaves
            put_(xx, y, color)
            put_(xx, y - 1, lit if lit and xx < px else color)
        put_(px - roof // 2 - 1, y - 1, color)
        put_(px + roof // 2 + 1, y - 1, color)
        y -= 2
    for yy in range(y - 9, y + 1):  # spire with rings
        put_(px, yy, color)
        if yy % 2 == 0 and yy < y - 1:
            put_(px - 1, yy, color)
            put_(px + 1, yy, color)


BIRD = [["X.....X", ".XX.XX.", "...X..."], [".......", "XXXXXXX", "...X..."],
        [".......", ".XXXXX.", "X..X..X"], [".......", "XXXXXXX", "...X..."]]


def bird(img, x, y, phase, color):
    for dy, row in enumerate(BIRD[phase % 4]):
        for dx, ch in enumerate(row):
            if ch == "X":
                put(img, x + dx - 3, y + dy - 1, color)


def overlay(title, ink, sign, cartouche=None):
    """Mat, frame line, the title written top to bottom with a seal under it, and a signature."""
    o = {}
    for y in range(H):
        for x in range(W):
            if x < L - 1 or x > R + 1 or y < T - 1 or y > B + 1:
                o[(x, y)] = MAT
            elif x in (L - 1, R + 1) or y in (T - 1, B + 1):
                o[(x, y)] = FRAME_LINE
    for cx, cy in ((L - 1, T - 1), (R + 1, T - 1), (L - 1, B + 1), (R + 1, B + 1)):
        o[(cx, cy)] = MAT
    tx, ty = R - 18, T + 4
    if cartouche:  # a paper slip behind the title, as on a woodblock print
        paper, edge = cartouche
        y1 = ty + len(title) * 17 + 1
        for y in range(ty - 3, y1 + 1):
            for x in range(tx - 3, tx + 20):
                o[(x, y)] = edge if x in (tx - 3, tx + 19) or y in (ty - 3, y1) else paper
    for i, ch in enumerate(title):
        for x, y in text_pixels(ch, "dotgothic")[2]:
            o[(tx + x, ty + i * 17 + y)] = ink
    sy = ty + len(title) * 17 + (5 if cartouche else 3)
    pts = text_pixels("闇", "dotgothic")[2]
    for y in range(sy, sy + 18):
        for x in range(tx, tx + 18):
            if (x, y) not in ((tx, sy), (tx + 17, sy), (tx, sy + 17), (tx + 17, sy + 17)):
                o[(x, y)] = SEAL_INK if (x - tx - 1, y - sy - 1) in pts else SEAL
    for x, y in text_pixels("TRENDON", "tiny5")[2]:
        o[(L + 4 + x, B - 8 + y)] = sign
    return o


def finish(img, top):
    for (x, y), c in top.items():
        img[y][x] = c
    return img


# ---------------------------------------------------------------- 月 tsuki

def tsuki():
    HZ, TB = 150, 158
    SKY = [hexc(c) for c in ("#07090f", "#0b0e17", "#10141f", "#161b2a", "#1d2336", "#262d44")]
    HALO = hexc("#4a5170")
    MOON, MOON_LIMB, MOON_SPOT = hexc("#ebe4cf"), hexc("#d3cab0"), hexc("#c9bfa3")
    STAR_DIM, STAR = hexc("#5d6382"), hexc("#d8d4c6")
    CLOUD, CLOUD_LIT = hexc("#262b40"), hexc("#454b68")
    CLOUD_MOON, CLOUD_MOON_LIT = hexc("#5a5c6c"), hexc("#b4ae9e")
    FUJI, FUJI_LIT, FUJI_HAZE = hexc("#181c2c"), hexc("#2a3150"), hexc("#262c42")
    SNOW_LIT, SNOW_SHADE, SNOW_RIDGE = hexc("#c9cad3"), hexc("#626986"), hexc("#9599b0")
    RIDGE = hexc("#141826")
    NEAR = hexc("#0b0c13")
    RIM, RIM_HI = hexc("#5e6582"), hexc("#a3a8be")
    STONE, STONE_LIT = hexc("#22242f"), hexc("#3a3d4c")
    GLOW_HI, GLOW, GLOW_LO = hexc("#f2c870"), hexc("#d79a44"), hexc("#7a4a24")
    KASAGI, SNOW_TOP = hexc("#16121a"), hexc("#d6d6de")
    WATER_TOP, WATER_BOT = hexc("#161b2b"), hexc("#07080d")
    RIPPLE, MIST = hexc("#323a55"), hexc("#4a5170")
    FLAKE, FLAKE_FAR = hexc("#e4e0d4"), hexc("#7c8098")
    FINGERS = [(38, 5), (43, 9), (47, 6), (51, 13), (55, 8), (59, 11), (63, 4), (67, 12), (71, 7),
               (75, 14), (79, 6), (83, 10), (88, 5), (92, 8)]
    PEAK = 88
    mx, my, mr = 64, 56, 17

    img = canvas()
    near = [[False] * W for _ in range(H)]
    gradient(img, T, HZ - 1, SKY)
    halo(img, mx, my, mr, 13, HALO)
    for y in range(my - mr, my + mr + 1):
        for x in range(mx - mr, mx + mr + 1):
            d = math.hypot(x - mx, y - my)
            if d <= mr:
                img[y][x] = MOON_LIMB if d > mr - 1.6 or (x - mx) + (y - my) > mr * 1.05 else MOON
    for cx, cy, r in ((57, 51, 3.4), (60, 54, 2.6), (69, 60, 3.6), (66, 63, 2.4), (70, 48, 1.7), (55, 60, 1.3)):
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                if math.hypot(x - cx, y - cy) <= r and math.hypot(x - mx, y - my) < mr - 1:
                    img[y][x] = MOON_SPOT

    for x in range(L, R + 1):  # Fuji: concave slopes, snow running down the gullies
        d = abs(x - 64)
        top = PEAK if d <= 3 else PEAK + 0.33 * (d - 3) ** 1.3
        snow_line = PEAK + 9 + max(0, max(n - abs(x - cx) * 2.2 for cx, n in FINGERS))
        for y in range(int(math.ceil(top)), HZ):
            haze = (y - top) / max(1, HZ - top)
            c = FUJI_LIT if x < 64 - (y - PEAK) * 0.08 else FUJI
            if haze > 0.55 + bayer(x, y) * 0.45:
                c = FUJI_HAZE
            elif x % 6 == 2 and haze < 0.5 and y > top + 2:
                c = mix(c, FUJI, 0.6)
            if y < snow_line:
                c = SNOW_LIT if x < 64 else SNOW_SHADE
                if any(x - cx == 1 for cx, _ in FINGERS) and y > PEAK + 4:
                    c = SNOW_RIDGE if x < 64 else mix(SNOW_SHADE, FUJI, 0.4)
                if y > snow_line - 2 and (x + y) % 2:
                    c = FUJI
            img[y][x] = c
    for x in range(L, R + 1):  # a low far ridge across the foot of the mountain
        for y in range(int(141 + 2.2 * math.sin(x / 9) + 1.3 * math.sin(x / 3.7)), HZ):
            img[y][x] = RIDGE

    def p(x, y, c=NEAR):
        if L <= x <= R and T <= y <= B:
            img[y][x] = c
            near[y][x] = True

    for x in range(L, R + 1):  # near shores
        hill = 130 - 2 * math.sin(x / 7) if x <= 24 else 130 + ((x - 24) / 26) ** 1.6 * 20 if x < 50 else HZ + 1
        for y in range(int(hill), HZ):
            p(x, y)
        shore = HZ - 5 * ((x - 96) / 32) ** 0.8 if x >= 96 else HZ + 1
        for y in range(int(shore), HZ):
            p(x, y)
    pagoda(p, 16, 129, NEAR)
    trunk = [(int(118 - (i / 34) ** 1.4 * 12), HZ - 1 - i) for i in range(34)]
    for tx, ty in trunk:  # black pine on the right shore
        p(tx, ty)
        p(tx + 1, ty)
    pads(p, ((107, 116, 9, 2.5), (100, 123, 6, 2), (114, 125, 7, 2.2), (110, 108, 6, 2), (119, 132, 5, 1.8),
             (104, 131, 4, 1.5)), NEAR, trunk=trunk)
    lx, lb = 39, 137  # stone lantern
    for yy, half in ((lb, 3), (lb - 1, 2), (lb - 2, 1), (lb - 3, 1), (lb - 4, 1), (lb - 5, 3), (lb - 6, 2),
                     (lb - 7, 2), (lb - 8, 2), (lb - 9, 4), (lb - 10, 3), (lb - 11, 1), (lb - 12, 0)):
        for xx in range(lx - half, lx + half + 1):
            p(xx, yy, STONE_LIT if xx == lx - half else STONE)
    for x in range(L, R + 1):  # snow lying on everything near
        for y in range(T + 1, HZ):
            if near[y][x] and not near[y - 1][x]:
                img[y][x] = RIM_HI if (x + y) % 3 else RIM
    img[128][16] = GLOW_LO  # one lamp left on in the pagoda
    window = [(38, 130), (39, 130), (40, 130), (38, 129), (39, 129), (40, 129)]

    gate = {}

    def bar(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            gate[(x, y)] = c

    bar(44, 46, 110, KASAGI)
    bar(82, 84, 110, KASAGI)
    for y in (111, 112):
        bar(45, 83, y, KASAGI)
    bar(46, 82, 113, KASAGI)
    bar(48, 80, 114, SHU_LIT)
    bar(48, 80, 115, SHU_DARK)
    for y in range(116, 121):
        bar(62, 66, y, SHU if y > 116 else SHU_DARK)
    bar(63, 65, 118, KASAGI)
    bar(49, 79, 121, SHU_LIT)
    bar(49, 79, 122, SHU)
    bar(49, 79, 123, SHU_DARK)
    for px in (53, 73):
        for y in range(116, TB + 1):
            if y in (121, 122, 123):
                continue
            gate[(px, y)], gate[(px + 1, y)], gate[(px + 2, y)] = SHU_LIT, SHU, SHU_DARK
        for y in (TB - 1, TB):
            for dx in range(3):
                gate[(px + dx, y)] = SHU_DARK
    for (x, y) in list(gate):  # snow on the top beams
        if y in (110, 111, 121) and (x, y - 1) not in gate:
            gate[(x, y)] = SNOW_TOP

    clouds = [(64, 64, -64, [(0, kasumi(30, 4)), (40, kasumi(12, 2))]),
              (97, 56, 56, [(0, kasumi(24, 3)), (34, kasumi(9, 2))]),
              (127, 40, -40, [(0, kasumi(14, 2))])]

    def cloud(x, y, row, rows, c):
        lit = row == 0
        if math.hypot(x - mx, y - my) <= mr:
            return CLOUD_MOON_LIT if lit else CLOUD_MOON
        if y > 90:
            return mix(FUJI_HAZE, MIST, 0.7 if lit else 0.4)
        return CLOUD_LIT if lit else CLOUD

    top = overlay("静寂", hexc("#d9d0b8"), hexc("#6d6a63"))
    rng = random.Random(7)
    stars = []
    while len(stars) < 46:
        x, y = rng.randint(L + 1, R - 1), int(T + 1 + (rng.random() ** 1.5) * 95)
        if img[y][x] not in SKY or math.hypot(x - mx, y - my) < 31 or (x, y) in top or (x > R - 22 and y < 70):
            continue
        stars.append((x, y, rng.random(), rng.choice((1, 1, 2, 3)), len(stars) < 4))
    flakes = [(rng.uniform(L, R), rng.random(), rng.uniform(HZ + 2, B), rng.random(), rng.choice((1, 1, 2)), i % 3 == 0)
              for i in range(60)]

    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = copy(img)
        for x, y, ph, m, big in stars:
            b = 0.5 + 0.5 * math.sin(TAU * (m * t + ph))
            im[y][x] = STAR if b > 0.66 else mix(STAR_DIM, STAR, 0.4) if b > 0.3 else STAR_DIM
            if big and b > 0.75:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    im[y + dy][x + dx] = STAR_DIM
        strips(im, t, clouds, cloud, skip=lambda x, y: near[y][x])
        flick = 0.5 + 0.25 * math.sin(TAU * 4 * t) + 0.25 * math.sin(TAU * 9 * t + 1.3)
        for x, y in window:
            im[y][x] = GLOW_HI if flick > 0.6 and y == 130 else GLOW if flick > 0.3 else GLOW_LO
        wobs = water(im, HZ, HZ, B, t, WATER_TOP, WATER_BOT, ripple=RIPPLE, sprite=gate, sprite_axis=TB)
        for y in range(HZ + 3, B + 1, 2):  # the moon's path on the water
            d = (y - HZ) / (B - HZ)
            n = math.sin(y * 1.9 + TAU * t * 4) + math.sin(y * 0.7 - TAU * t * 3)
            half = int(d * 5 + n * 1.4)
            if half > 0 and n > -0.6:
                cx = 64 + wobs[y]
                for x in range(max(L, cx - half), min(R, cx + half) + 1):
                    core = abs(x - cx) < half * 0.4
                    im[y][x] = (MOON_LIMB if core else mix(HALO, MOON_LIMB, 0.35)) if d < 0.7 else mix(HALO, im[y][x], 0.3)
        for (x, y), c in gate.items():
            im[y][x] = c
        mist(im, HZ - 16, HZ + 4, HZ - 4, 5.5, t, MIST)
        for fx, fy, ground, ph, m, close in flakes:
            y = falling(t, T, ground, fy, m)
            x = fx + 2.2 * math.sin(TAU * (t * 2 * m + ph)) + (y - T) * 0.06
            xi, yi = int(x), int(y)
            put(im, xi, yi, FLAKE if close else FLAKE_FAR)
            if close and (xi + yi) % 2 and L <= xi <= R and T <= yi + 1 <= B:
                im[yi + 1][xi] = mix(FLAKE, im[yi + 1][xi], 0.5)
        frames.append(finish(im, top))
    return frames


# ---------------------------------------------------------------- 夕 yu

def yu():
    HZ = 146
    IND, IND2, PAPER, WARM, PEACH = (hexc(c) for c in ("#1f2d52", "#4e5c80", "#e8dec6", "#ebcfa8", "#e2a982"))
    SUN, SUN_RIM = hexc("#cf4630"), hexc("#b5382a")
    KAS, KAS_SH = hexc("#f4eddd"), hexc("#d8c6a4")
    FAR, FAR_SH = hexc("#9a9cb2"), hexc("#8a8ca4")
    FUJI_SH, FUJI_LIT = hexc("#2b3962"), hexc("#43548c")
    SNOW, SNOW_SH = hexc("#f1ebdc"), hexc("#b4b8cc")
    CLIFF, CLIFF_LIT = hexc("#1b2140"), hexc("#3a4470")
    INK = hexc("#15171f")
    SEA_TOP, SEA_BOT = hexc("#5a6b92"), hexc("#16204a")
    CREST = hexc("#ebe3cf")
    SAIL, SAIL_LINE = hexc("#e6dbc1"), hexc("#9c8f74")
    FINGERS = [(14, 4), (18, 7), (22, 5), (26, 11), (30, 6), (34, 9), (38, 4), (42, 10), (46, 6), (50, 12),
               (54, 5), (58, 7)]
    sx, sy, sr = 80, 98, 18

    img = canvas()
    gradient(img, T, HZ - 1, [IND, IND2, PAPER, PAPER, WARM, PEACH])
    for y in range(sy - sr, sy + sr + 1):
        for x in range(sx - sr, sx + sr + 1):
            d = math.hypot(x - sx, y - sy)
            if d <= sr:
                img[y][x] = SUN_RIM if d > sr - 1 else SUN
    for x in range(L, R + 1):  # far hills, pale with distance
        for y in range(int(128 + 4 * math.sin(x / 10) + 2.5 * math.sin(x / 4.3 + 1)), HZ):
            img[y][x] = FAR if y > 138 or (x + y) % 5 else FAR_SH
    for x in range(L, R + 1):  # Fuji, lit from the sun on the right
        d = abs(x - 36)
        top = 92 if d <= 2 else 92 + 0.43 * (d - 2) ** 1.3
        snow_line = 100 + max(0, max(n - abs(x - cx) * 2.2 for cx, n in FINGERS))
        for y in range(int(math.ceil(top)), HZ):
            lit = x >= 36 + (y - 92) * 0.05
            c = FUJI_LIT if lit else FUJI_SH
            if (y - top) / max(1, HZ - top) > 0.6 + bayer(x, y) * 0.4:
                c = mix(c, FAR, 0.4)
            if y < snow_line:
                c = SNOW if lit else SNOW_SH
                if any(x - cx == 1 for cx, _ in FINGERS) and y > 96:
                    c = SNOW_SH if lit else mix(SNOW_SH, FUJI_SH, 0.4)
                if y > snow_line - 2 and (x + y) % 2:
                    c = FUJI_LIT if lit else FUJI_SH
            img[y][x] = c

    def p(x, y, c=INK):
        put(img, x, y, c)

    for x in range(96, R + 1):  # a cliff on the right with layered rock
        top = HZ - 30 * ((x - 96) / 26) ** 0.55
        for y in range(int(top), HZ):
            c = CLIFF_LIT if y == int(top) else CLIFF
            if y % 5 == 0 and (x + y) % 3:
                c = mix(CLIFF, CLIFF_LIT, 0.45)
            p(x, y, c)
    trunk = [(round(116 - (i / 30) ** 1.3 * 18 + math.sin(i / 5) * 1.5), round(127 - i * 0.85)) for i in range(31)]
    for tx, ty in trunk:  # a pine leaning out from the cliff over the water
        p(tx, ty)
        p(tx + 1, ty)
        if ty > 114:
            p(tx + 2, ty)
    pads(p, ((93, 101, 7, 2), (103, 96, 6, 1.8), (86, 107, 5, 1.6), (106, 106, 5, 1.6), (97, 110, 4, 1.4),
             (112, 113, 4, 1.4)), INK, trunk=trunk)

    bands = [(66, 80, -80, [(0, kasumi(36, 4)), (50, kasumi(16, 3))]),
             (101, 64, 64, [(0, kasumi(30, 3))]),
             (123, 72, -72, [(0, kasumi(40, 4)), (52, kasumi(12, 2))])]
    paint = lambda x, y, row, rows, c: KAS_SH if row == rows - 1 else KAS
    top = overlay("夕凪", SEAL_INK, hexc("#8e93ad"))
    boat = []  # (dx, dy from the water line, colour)
    for dx in range(0, 16):
        boat.append((dx, -1, INK))
    for dx in range(1, 15):
        boat.append((dx, 0, INK))
    for dx in range(3, 13):
        boat.append((dx, 1, INK))
    for dy in range(-16, -1):
        boat.append((6, dy, INK))
    for dy in range(-15, -4):
        for dx in range(2, 11):
            if dx != 6:
                boat.append((dx, dy, SAIL_LINE if dx in (2, 10) or (dy + 15) % 3 == 0 else SAIL))
    boat += [(13, -7, INK), (12, -6, INK), (13, -6, INK), (12, -5, INK), (13, -5, INK), (12, -4, INK),
             (13, -4, INK), (12, -3, INK), (12, -2, INK), (14, -2, INK)]
    boat += [(14 + i, -6 + i * 2, INK) for i in range(5)]  # the pole
    flock = [(0, 0, 0), (7, -3, 1), (13, 2, 2), (19, -1, 3)]

    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = copy(img)
        strips(im, t, bands, paint)
        lead = R + 8 - (t * (W + 40)) % (W + 40)
        for dx, dy, ph in flock:
            bird(im, round(lead + dx), 72 + dy, f // 3 + ph, INK)
        water(im, HZ, HZ, B, t, SEA_TOP, SEA_BOT, fade=(0.5, 0.75), amp=(0.6, 3.2))
        for row, y in enumerate(range(HZ + 3, B + 1, 5)):  # wave crests drifting both ways
            d = (y - HZ) / (B - HZ)
            period = 22 + (row % 3) * 6
            shift = round(t * (period if row % 2 else -period))
            for x0 in (0, period // 2 + row % 5):
                for k in range(1 + int(d * 4)):
                    x = L + (x0 + k + shift) % period
                    while x <= R:
                        im[y][x] = mix(CREST, im[y][x], 0.55 - d * 0.4)
                        x += period
        bx, by = 50, 178 + (1 if math.sin(TAU * t * 4) > 0.2 else 0)
        for dx, dy, c in boat:
            put(im, bx + dx, by + dy, c)
        for dx in range(1, 15):  # the hull's reflection
            for dy in (2, 3):
                if T <= by + dy <= B:
                    put(im, bx + dx + (1 if (dy + f // 6) % 2 else 0), by + dy, mix(INK, im[by + dy][bx + dx], 0.5))
        frames.append(finish(im, top))
    return frames


# ---------------------------------------------------------------- 雨 ame

def ame():
    HZ = 150
    SKY = [hexc(c) for c in ("#080b12", "#0c1019", "#111722", "#18202d")]
    FAR, FAR_WIN = hexc("#1f2836"), hexc("#8a6236")
    PAG = hexc("#2a3446")
    FAR_WATER = hexc("#0d121b")
    WATER_TOP, WATER_BOT = hexc("#121822"), hexc("#05070b")
    BR, BR_LIT, BR_DARK = hexc("#b63a28"), hexc("#d85d3e"), hexc("#6a1c13")
    KNOB = hexc("#a8894e")
    LANT, LANT_LIT, LANT_DARK, CAP = hexc("#d2482e"), hexc("#f39a5c"), hexc("#8a2a1c"), hexc("#1a1414")
    GLOW = hexc("#e9a057")
    UMB, UMB_RIB, UMB_SH = hexc("#e2d4b4"), hexc("#a8977a"), hexc("#b9a888")
    KIMONO, OBI = hexc("#1c1d26"), hexc("#9a7a44")
    WIL, WIL_LIT = hexc("#22322b"), hexc("#3a5244")
    TRUNK, TRUNK_LIT = hexc("#14120f"), hexc("#2c2722")
    STONE, STONE_LIT, STONE_GAP = hexc("#252930"), hexc("#363b45"), hexc("#14161b")
    RAIN, RAIN_FAR = hexc("#8a9cb2"), hexc("#3e4a5c")
    RING = hexc("#56657c")
    rng = random.Random(5)

    img = canvas()
    gradient(img, T, 137, SKY)

    def p(x, y, c):
        put(img, x, y, c)

    pagoda(p, 92, 132, PAG)
    x = L
    while x <= R:  # the far bank: roofs and a few lit windows
        w = rng.randint(9, 17)
        roof = rng.randint(118, 126)
        for xx in range(x, min(R, x + w) + 1):
            for yy in range(roof + (1 if xx in (x, x + w) else 0), 138):
                if not (88 <= xx <= 96 and yy < roof + 2):
                    p(xx, yy, FAR)
        for _ in range(rng.randint(0, 2)):
            wx, wy = rng.randint(x + 2, x + max(2, w - 4)), rng.randint(roof + 4, 133)
            for xx in range(wx, wx + 2):
                for yy in range(wy, wy + 2):
                    p(xx, yy, FAR_WIN)
        x += w + 1
    for y in range(138, HZ):  # far water under the bridge, streaked by the windows
        for x in range(L, R + 1):
            c = FAR_WATER
            if img[2 * 138 - 1 - y][x] == FAR_WIN and (y + x) % 2:
                c = mix(FAR_WIN, FAR_WATER, 0.55)
            img[y][x] = c

    deck = lambda x: 106 + 26 * ((x - 64) / 64) ** 2
    for px in (22, 30, 98, 106):  # piers
        for y in range(int(deck(px)) + 4, HZ + 2):
            p(px, y, BR)
            p(px + 1, y, BR_DARK)
    for a, b_ in ((22, 31), (98, 107)):
        for x in range(a, b_ + 1):
            p(x, 140, BR_DARK)
    figure = [(63, 95), (64, 95), (65, 95)] + [(x, y) for y in range(96, 106) for x in range(62 + (y < 98), 67 - (y < 98))]
    for x, y in figure:
        p(x, y, OBI if y == 100 else KIMONO)
    for x in range(L, R + 1):  # deck, railing, posts
        d = int(deck(x))
        for y, c in ((d, BR_LIT), (d + 1, BR), (d + 2, BR), (d + 3, BR_DARK), (d + 4, BR_DARK)):
            p(x, y, c)
        p(x, d - 7, BR_LIT)
        p(x, d - 4, BR)
        if (x - 59) % 10 == 0:
            for y in range(d - 7, d):
                p(x, y, BR)
            if (x - 59) % 20 == 0:
                p(x, d - 8, KNOB)
                p(x - 1, d - 8, KNOB)
                p(x + 1, d - 8, KNOB)
                p(x, d - 9, KNOB)
    umbrella = {89: (61, 67), 90: (59, 69), 91: (58, 70), 92: (57, 71), 93: (57, 71)}
    for y, (a, b_) in umbrella.items():
        for x in range(a, b_ + 1):
            p(x, y, UMB_SH if y == 93 else UMB)
    for x, y in ((61, 91), (67, 91), (60, 92), (64, 92), (68, 92), (59, 93), (62, 93), (66, 93), (69, 93)):
        p(x, y, UMB_RIB)
    p(64, 88, CAP)
    lamps = [(39, int(deck(39))), (89, int(deck(89)))]
    for lx, d in lamps:  # lamp posts
        for y in range(d - 21, d):
            p(lx, y, BR_DARK)
        p(lx + 1, d - 21, BR_DARK)
        p(lx + 2, d - 21, BR_DARK)

    for x in range(L, 40):  # the near bank under the willow
        for y in range(int(192 + (x - L) * 1.1), B + 1):
            c = STONE_GAP if y % 4 == 0 or (x + (y // 4) * 3) % 7 == 0 else STONE_LIT if (y % 4 == 1) else STONE
            p(x, y, c)
    for y in range(60, B + 1):  # willow trunk, leaning toward the water
        k = (B - y) / (B - 60)
        cx = 7 + k * k * 6
        w = 4 - int(k * 2)
        for x in range(int(cx), int(cx) + w):
            p(x, y, TRUNK_LIT if x == int(cx) + w - 1 else TRUNK)
    branch = lambda x: 50 + ((x - 12) / 44) ** 1.6 * 16
    for x in range(12, 57):  # boughs: two arcs from the top of the trunk
        p(x, int(branch(x)), TRUNK)
        if x < 34:
            p(x, int(branch(x)) - 1, TRUNK)
        p(x - 4, int(branch(x) * 0.8 + 6), TRUNK)
    strands = []
    x0 = 6
    while x0 < 58:
        y0 = int(branch(max(12, x0))) + rng.randint(0, 3)
        ln = int(24 + rng.random() * 34 + (58 - x0) * 0.7)
        strands.append((x0, y0, ln, rng.random(), [k for k in range(3, ln) if rng.random() < 0.22]))
        x0 += rng.choice((2, 3, 3, 4))

    top = overlay("雨音", SEAL_INK, hexc("#5c6272"))
    drops = []
    for i in range(110):
        close = i % 3 == 0
        drops.append((rng.uniform(L, R + 40), rng.random(), rng.uniform(HZ + 2, B) if close else rng.uniform(100, HZ),
                      rng.choice((7, 8, 9)) if close else rng.choice((5, 6)), close))
    rings = [(rng.randint(L + 4, R - 4), rng.randint(HZ + 6, B - 4), rng.random(), rng.choice((2, 3, 4))) for _ in range(26)]

    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = copy(img)
        for i, (lx, d) in enumerate(lamps):  # paper lanterns, swaying and glowing
            sway = round(0.8 * math.sin(TAU * (2 * t + i * 0.37)))
            flick = 0.75 + 0.15 * math.sin(TAU * 5 * t + i) + 0.1 * math.sin(TAU * 11 * t)
            cx, cy = lx + 2 + sway, d - 16
            halo(im, cx, cy, 3, 7, GLOW, 0.35 * flick)
            for yy in range(cy - 3, cy + 4):
                half = 1 if yy in (cy - 3, cy + 3) else 2
                for xx in range(cx - half, cx + half + 1):
                    if yy in (cy - 3, cy + 3):
                        c = CAP
                    elif abs(xx - cx) == 2:
                        c = LANT_DARK
                    elif yy in (cy - 1, cy + 1) and xx != cx:
                        c = LANT
                    else:
                        c = LANT_LIT if flick > 0.8 else mix(LANT, LANT_LIT, 0.6)
                    put(im, xx, yy, c)
            put(im, cx, cy - 4, CAP)
        for x0, y0, ln, ph, dabs in strands:  # willow strands in the wind
            for k in range(ln):
                s = (k / ln) ** 1.5
                x = x0 + round(3 * s * math.sin(TAU * (2 * t) + ph * 6) + 1.2 * s * math.sin(TAU * 3 * t + x0))
                put(im, x, y0 + k, WIL)
                if k in dabs:
                    put(im, x + (1 if (k + x0) % 2 else -1), y0 + k, WIL_LIT)
        water(im, HZ, HZ, B, t, WATER_TOP, WATER_BOT, fade=(0.38, 0.7), amp=(0.6, 2.4))
        for rx, ry, ph, m in rings:  # rain rings on the water
            age = ((t * m + ph) % 1) * 10
            if age < 6:
                r = 1 + age * 0.6
                c = mix(RING, WATER_TOP, age / 7)
                for a in range(0, 360, 30):
                    put(im, round(rx + r * 1.7 * math.cos(math.radians(a))), round(ry + r * 0.5 * math.sin(math.radians(a))), c)
        for x0, frac, ground, m, close in drops:  # rain, slanting with the wind
            y = falling(t, T - 8, ground, frac, m)
            x = x0 - (y - T) / 3
            for k in range(6 if close else 3):
                xx, yy = round(x + k / 3), int(y) - k
                if L <= xx <= R and T <= yy <= B:
                    im[yy][xx] = mix(im[yy][xx], RAIN if close else RAIN_FAR, 0.6 if close else 0.5)
        frames.append(finish(im, top))
    return frames


# ---------------------------------------------------------------- 竹 take

def take():
    HO = 126  # where the ground meets the mist
    MISTS = [hexc(c) for c in ("#e2e3d1", "#d4d9c3", "#c3ccb3", "#b2bfa3")]
    G_FAR, G_NEAR = hexc("#a9b598"), hexc("#3e4c37")
    PATH, PATH_LIT, PATH_GAP = hexc("#9a9c88"), hexc("#b7b8a2"), hexc("#6a7060")
    BMB, BMB_LIT, BMB_SH = hexc("#3f6142"), hexc("#7a9c68"), hexc("#28402c")
    NODE, NODE_LIT = hexc("#1e3022"), hexc("#a3ba86")
    LEAF, LEAF_LIT = hexc("#2f4c33"), hexc("#5f8253")
    INK, CLOAK_LIT = hexc("#1d1f22"), hexc("#34373b")
    STRAW, STRAW_LIT, STRAW_SH = hexc("#9c8459"), hexc("#c2a876"), hexc("#64553b")
    OBI = hexc("#b23a26")
    FALL, FALL2 = hexc("#b5b26a"), hexc("#8d9a55")
    LIGHT = hexc("#f6efcc")
    rng = random.Random(3)
    hw = lambda y: 1.5 + (y - HO) * 0.42

    img = canvas()
    gradient(img, T, HO + 4, MISTS)
    for y in range(HO, B + 1):  # ground and the stone path, both fading into the mist
        d = (y - HO) / (B - HO)
        for x in range(L, R + 1):
            g = mix(G_FAR, G_NEAR, min(1, d * 1.4))
            if abs(x - 64) <= hw(y):
                course = int(60 / (y - HO + 2) * 1.6)
                col = int(((x - 64) / hw(y) + 1) * 2.5 + (course % 2) * 0.5)
                edge = int(60 / (y - HO + 1) * 1.6) != course or abs(x - 64) > hw(y) - 1
                g = PATH_GAP if edge else (PATH_LIT if (course * 7 + col * 3) % 5 < 2 else PATH)
                if not edge and int(((x - 1 - 64) / hw(y) + 1) * 2.5 + (course % 2) * 0.5) != col:
                    g = PATH_GAP
            elif (x * 5 + y * 3) % 17 == 0 and d > 0.3:
                g = mix(g, G_NEAR, 0.5)
            fog = max(0.0, 1 - d * 3.2)
            img[y][x] = mix(g, MISTS[-1], fog * 0.85) if fog > bayer(x, y) * 0.3 else g

    def torii(cx, base, half, height, fade):
        col = lambda c: mix(c, MISTS[2], fade)
        top_ = base - height
        for x in range(cx - half - 2, cx + half + 3):
            put(img, x, top_, col(INK))
            put(img, x, top_ + 1, col(INK))
        put(img, cx - half - 3, top_ - 1, col(INK))
        put(img, cx + half + 3, top_ - 1, col(INK))
        nuki = top_ + max(3, height // 4)
        for x in range(cx - half - 1, cx + half + 2):
            put(img, x, top_ + 2, col(SHU_DARK))
            put(img, x, nuki, col(SHU))
        pw = 1 if half < 8 else 2
        for x0 in (cx - half, cx + half - pw + 1):
            for y in range(top_ + 2, base + 1):
                for x in range(x0, x0 + pw):
                    put(img, x, y, col(SHU_LIT if x == x0 and pw > 1 else SHU))

    stalks = []  # (x, width, base, tier); tier 0 far .. 3 at the frame edge
    for tier, n, (b0, b1), (w0, w1) in ((0, 36, (HO + 1, HO + 8), (1, 2)), (1, 18, (HO + 10, HO + 32), (2, 3)),
                                        (2, 7, (HO + 46, B), (4, 6))):
        placed = 0
        while placed < n:
            base, w = rng.randint(b0, b1), rng.randint(w0, w1)
            x = rng.randint(L - 2, R - w + 2)
            if abs(x + w / 2 - 64) < hw(base) + w + 3 or (tier == 2 and x > R - 26):
                continue
            stalks.append((x, w, base, tier))
            placed += 1
    stalks += [(L - 2, 9, B + 4, 3), (R - 30, 7, B + 4, 3)]

    tier_col = [mix(BMB, MISTS[1], 0.72), mix(BMB, MISTS[1], 0.45)]
    for x, w, base, tier in stalks:  # the far stalks do not move
        if tier == 0:
            for y in range(T, base + 1):
                for xx in range(x, x + w):
                    put(img, xx, y, mix(tier_col[0], NODE, 0.3) if (base - y) % 9 == 0 else tier_col[0])
    torii(64, 136, 6, 13, 0.6)
    torii(64, 151, 10, 24, 0.38)

    leaves = {}
    for i, (x, w, base, tier) in enumerate(stalks):
        if tier == 0:
            continue
        node = (14, 20, 26)[tier - 1]
        sprays = []
        for y in range(base - node, T, -node):
            if y < (100 if tier == 1 else 112) and rng.random() < 0.8:
                side = rng.choice((-1, 1))
                for j in range((3, 4, 5)[tier - 1]):
                    sprays.append((y + j * 2, side, j, (3, 5, 6)[tier - 1] + rng.randint(-1, 1)))
        leaves[i] = sprays

    figure = []  # a ronin seen from behind, straw hat and dark coat
    fx, fy = 64, 200
    for row, (a, b_) in enumerate(((63, 65), (61, 67), (59, 69), (57, 71), (56, 72))):
        for x in range(a, b_ + 1):
            figure.append((x, fy - 36 + row, STRAW_LIT if row < 2 and x < 64 else STRAW_SH if row == 4 else STRAW))
    for y in range(fy - 31, fy - 9):
        half = int(4 + (y - (fy - 31)) / 22 * 3)
        for x in range(fx - half, fx + half + 1):
            figure.append((x, y, CLOAK_LIT if x == fx - half else INK))
    for x in range(fx - 6, fx + 7):
        figure.append((x, fy - 20, OBI))
    for i in range(10):
        figure.append((fx - 6 - i, fy - 20 + i // 2, INK))  # the scabbard behind the left hip
    figure.append((fx - 7, fy - 19, OBI))
    for y in range(fy - 9, fy + 1):
        for x in (fx - 4, fx - 3, fx - 2, fx + 2, fx + 3, fx + 4):
            figure.append((x, y, INK))
        if y < fy - 5:
            for x in range(fx - 1, fx + 2):
                figure.append((x, y, INK))

    top = overlay("竹林", INK, hexc("#c9cfb7"), cartouche=(hexc("#ece8d6"), INK))
    falls = [(rng.uniform(L, R), rng.random(), rng.uniform(HO + 6, B), rng.random(), rng.choice((1, 1, 2))) for _ in range(18)]
    shafts = [(-14, 10), (22, 7), (58, 12)]

    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        im = copy(img)
        for i, (x, w, base, tier) in enumerate(stalks):  # stalks that sway, nearer ones further
            if tier == 0:
                continue
            amp = (1.0, 2.0, 2.4)[tier - 1]
            ph = (x * 0.13) % 1
            node = (14, 20, 26)[tier - 1]
            sway = lambda y: round(amp * ((base - y) / (base - T)) ** 2 * math.sin(TAU * (t + ph)))
            for y in range(T, min(B, base) + 1):
                dx = sway(y)
                for k in range(w):
                    if tier == 1:
                        c = tier_col[1]
                        if (base - y) % node == 0:
                            c = mix(c, NODE, 0.35)
                    else:
                        c = BMB_LIT if k == 0 else BMB_SH if k == w - 1 else BMB
                        if (base - y) % node == 0:
                            c = NODE
                        elif (base - y) % node == node - 1 and k < w - 1:
                            c = NODE_LIT
                    put(im, x + k + dx, y, c)
            for y, side, j, ln in leaves[i]:
                x0 = x + (w if side > 0 else -1) + sway(y)
                for k in range(ln):
                    c = LEAF_LIT if k < ln // 2 else LEAF
                    put(im, x0 + side * (k + j), y + k // 2 + j // 2, mix(c, MISTS[1], 0.45) if tier == 1 else c)
        mist(im, HO - 22, HO + 18, HO - 2, 9, t, MISTS[0], (0.25, 0.45))
        for i, (c0, width) in enumerate(shafts):  # light falling through the canopy
            b = round((0.5 + 0.5 * math.sin(TAU * t + i * 2.1)) * 2) / 2
            if not b:
                continue
            for y in range(T, HO + 30):
                for x in range(L, R + 1):
                    u = x - (y - T) * 0.55 - c0
                    if 0 <= u < width and bayer(x, y) < 0.35 * b * (1 - (y - T) / (HO + 40 - T)):
                        im[y][x] = mix(im[y][x], LIGHT, 0.35)
        for x in range(fx - 8, fx + 9):  # the figure's shadow
            put(im, x, fy + 1, mix(im[fy + 1][x], G_NEAR, 0.6))
        for x, y, c in figure:
            put(im, x, y, c)
        for i in range(-6, 6):  # the coat's hem catching the wind
            if (i + f // 4) % 3 == 0:
                put(im, fx + i, fy - 10, INK)
        for lx, frac, ground, ph, m in falls:
            y = falling(t, T, ground, frac, m)
            x = lx + 4 * math.sin(TAU * (t * 2 * m + ph))
            xi, yi = int(x), int(y)
            spin = (f // 6 + int(ph * 4)) % 3
            c = FALL if ph > 0.5 else FALL2
            put(im, xi, yi, c)
            put(im, xi + (1 if spin == 0 else -1 if spin == 1 else 0), yi + (1 if spin < 2 else 0), c)
        frames.append(finish(im, top))
    return frames


# ---------------------------------------------------------------- output

def save(name: str, frames) -> Path:
    flat = Image.new("RGB", (W, H * len(frames)))
    flat.putdata([p for img in frames for row in img for p in row])
    pal = flat.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    out = []
    for img in frames:
        im = Image.new("RGB", (W, H))
        im.putdata([p for row in img for p in row])
        out.append(im.quantize(palette=pal, dither=Image.Dither.NONE).resize((W * SCALE, H * SCALE), Image.Resampling.NEAREST))
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / f"{name}.gif"
    out[0].save(path, save_all=True, append_images=out[1:], duration=DELAY, loop=0, disposal=1, optimize=False)
    if shutil.which("magick"):
        subprocess.run(["magick", str(path), "-layers", "Optimize", str(path)], check=True)
    print(f"{path.relative_to(ROOT)}: {len(out)} frames, {path.stat().st_size / 1e6:.2f} MB")
    return path


SCENES = {"tsuki": tsuki, "yu": yu, "ame": ame, "take": take}

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCENES)
    for n in names:
        if n not in SCENES:
            raise SystemExit(f"unknown scene {n!r}; scenes: {', '.join(SCENES)}")
        save(n, SCENES[n]())
