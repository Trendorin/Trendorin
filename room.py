"""Vertical pixel-art room: a window onto apartment blocks, plants, sunlight. python3 room.py OUT.svg"""
import math, random, sys
W, H, PX = 64, 112, 5
random.seed(11)
B = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
g = {}
def put(x, y, c):
    if 0 <= x < W and 0 <= y < H: g[(x, y)] = c
def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1):
        for x in range(x0, x1): put(x, y, c)
def mix(x, y, a, b, t):  # ordered dither between a and b, t in 0..1
    return b if t * 16 > B[y % 4][x % 4] else a
def blob(cx, cy, rx, ry, cols, hl=None):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1:
                shade = min(1, max(0, (x - cx) / rx * 0.5 + (y - cy) / ry * 0.6 + 0.5))
                put(x, y, mix(x, y, cols[0], cols[1], shade))
                if hl and d < 0.35 and (x + y) % 3 == 0 and x < cx: put(x, y, hl)

# wall
for y in range(H):
    for x in range(W):
        put(x, y, mix(x, y, "#d8b98f", "#cfae84", 0.05 + 0.22 * y / H))
# window geometry
WX0, WX1, WY0, WY1 = 11, 53, 8, 70
# sky
for y in range(WY0, WY1):
    for x in range(WX0, WX1):
        t = (y - WY0) / (WY1 - WY0)
        put(x, y, mix(x, y, "#5aa3de", "#9fd0f0", min(1, t * 1.1)) if t > 0.15 else "#5aa3de")
for cx, cy, r in [(22, 26, 5), (24, 25, 4), (44, 36, 4), (46, 35, 3), (18, 50, 4)]:
    blob(cx, cy, r + 2, r * 0.55, ("#ffffff", "#dbeaf7"))
# buildings (khrushchyovka blocks)
def building(x0, x1, top, wall, wall2, win, rows, cols):
    for y in range(top, WY1):
        for x in range(x0, x1): put(x, y, mix(x, y, wall, wall2, (x - x0) / (x1 - x0) * 0.8))
    rect(x0, top, x1, top + 1, "#9b7f5a")
    ww = (x1 - x0 - 2) // cols
    for r in range(rows):
        for c in range(cols):
            wx, wy = x0 + 2 + c * ww, top + 3 + r * 5
            if wy + 3 < WY1:
                rect(wx, wy, wx + 2, wy + 3, win)
                put(wx, wy, "#cfe6f7")
    for k in range(1, rows // 2 + 1):  # balconies
        for c in range(0, cols, 2):
            put(x0 + 2 + c * ww, top + 3 + k * 10 - 2, "#8a7a62")
building(14, 27, 30, "#e5cf9c", "#c9b27d", "#5e9ad0", 7, 3)
building(33, 51, 18, "#ead7a6", "#cdb584", "#5e9ad0", 10, 4)
building(24, 36, 44, "#d9c590", "#bba974", "#5e9ad0", 5, 3)
# trees in front of the blocks
for cx, cy, rx, ry in [(21, 62, 6, 7), (45, 60, 8, 8), (31, 66, 5, 5), (14, 58, 3, 5)]:
    blob(cx, cy, rx, ry, ("#5aa04a", "#2f6b30"), "#8fd070")
for x in range(WX0, WX1): put(x, WY1 - 1, mix(x, WY1 - 1, "#3b7a38", "#2f6b30", .5))
# window frame + bars
FR, FR2 = "#e6cda0", "#b98c58"
rect(WX0 - 3, WY0 - 3, WX1 + 3, WY0, FR); rect(WX0 - 3, WY1, WX1 + 3, WY1 + 4, FR)
rect(WX0 - 3, WY0 - 3, WX0, WY1 + 4, FR); rect(WX1, WY0 - 3, WX1 + 3, WY1 + 4, FR)
rect(31, WY0, 33, WY1, FR); rect(WX0, 26, WX1, 28, FR)
for y in range(WY0 - 3, WY1 + 4): put(WX0 - 3, y, FR2); put(WX1 + 2, y, FR2)
for x in range(WX0 - 3, WX1 + 3): put(x, WY1 + 3, FR2)
# sill
rect(WX0 - 6, WY1 + 4, WX1 + 6, WY1 + 8, "#d9b784"); rect(WX0 - 6, WY1 + 8, WX1 + 6, WY1 + 9, "#a47a49")
# books and a toy plane on the sill
rect(34, 70, 52, 74, "#2a6f7c"); rect(34, 70, 52, 71, "#3d8c99"); rect(36, 66, 50, 70, "#1f4f63"); rect(36, 66, 50, 67, "#2f6f86")
rect(38, 62, 49, 66, "#f2ece0"); rect(40, 63, 47, 64, "#5d7fb5"); rect(43, 59, 45, 62, "#f2ece0"); rect(36, 64, 51, 65, "#cfc6b4")  # toy plane
# radiator
for x in range(14, 50):
    if (x // 2) % 2 == 0:
        rect(x, 80, x + 1, 100, "#cfc8bf")
    else:
        rect(x, 80, x + 1, 100, "#a69f96")
rect(13, 78, 51, 80, "#b9b1a7"); rect(13, 100, 51, 102, "#8b847b")
# floor
for y in range(104, H):
    for x in range(W):
        put(x, y, "#8a5a33" if (x + (y // 4) * 7) % 16 else "#6f4626")
rect(0, 102, W, 104, "#5b3a20")
# sun shafts across everything except the sky
for y in range(H):
    for x in range(W):
        if WY0 <= y < WY1 and WX0 <= x < WX1: continue
        v = ((x + y * 0.55) % 26)
        edge = 1.5
        if 6 < v < 13 or (5 < v <= 6 and B[y % 4][x % 4] < 8) or (13 <= v < 14 and B[y % 4][x % 4] < 8):
            c = g[(x, y)]
            g[(x, y)] = {"#d8b98f": "#f1dfb6", "#cfae84": "#e8cf9f"}.get(c, {"#cfc8bf": "#efe6d4", "#a69f96": "#cfc6b6", "#b9b1a7": "#dcd3c4", "#d9b784": "#ecd2a0", "#8a5a33": "#a87444", "#6f4626": "#8a5a33"}.get(c, c))
# hanging plant top right
def leaf(cx, cy, ang, ln):
    for i in range(ln):
        x = cx + math.cos(ang) * i; y = cy + math.sin(ang) * i
        w = 1 + int(2.2 * math.sin(math.pi * i / ln))
        for k in range(-w, w + 1):
            px, py = int(x - math.sin(ang) * k), int(y + math.cos(ang) * k)
            put(px, py, "#3c7d38" if k > 0 else ("#5fae4c" if k < 0 else "#2a5a2c"))
for ang, ln, cx, cy in [(1.9, 14, 57, 2), (1.3, 16, 60, 4), (2.4, 12, 55, 5), (1.0, 18, 63, 8), (1.7, 20, 58, 6), (2.7, 10, 54, 9), (0.8, 14, 62, 14)]:
    leaf(cx, cy, ang, ln)
rect(54, 0, 64, 2, "#7a4a2a")
# left plant in a pot
for ang, ln, cx, cy in [(-1.2, 16, 4, 100), (-0.9, 14, 3, 98), (-1.6, 18, 2, 99), (-0.5, 12, 4, 97), (-2.0, 11, 3, 100)]:
    leaf(cx, cy, ang, ln)
rect(0, 100, 9, 104, "#b0592f"); rect(0, 100, 9, 101, "#cf7a49")
runs = []
for y in range(H):
    x = 0
    while x < W:
        c = g[(x, y)]; n = 1
        while x + n < W and g[(x + n, y)] == c: n += 1
        runs.append((c, x, y, n)); x += n
rects = "".join(f'<rect x="{x*PX}" y="{y*PX}" width="{n*PX}" height="{PX}" fill="{c}"/>' for c, x, y, n in sorted(runs))
open(sys.argv[1], "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*PX}" height="{H*PX}" viewBox="0 0 {W*PX} {H*PX}" shape-rendering="crispEdges" role="img"><title>A sunlit window</title>{rects}</svg>\n')
