"""Vertical pixel-art night shrine: Fuji, moon, torii gate, lanterns, sakura. python3 torii.py OUT.svg"""
import math, random, sys
W, H, PX = 64, 112, 5
random.seed(5)
B = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
g = {}
def put(x, y, c):
    if 0 <= x < W and 0 <= y < H: g[(x, y)] = c
def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1):
        for x in range(x0, x1): put(x, y, c)
def mix(x, y, a, b, t): return b if t * 16 > B[y % 4][x % 4] else a
def blob(cx, cy, rx, ry, a, b):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1: put(x, y, mix(x, y, a, b, min(1, max(0, (x - cx) / rx * .5 + (y - cy) / ry * .5 + .5))))
# sky: deep indigo to a violet glow at the horizon
SKY = ["#070914", "#0d1024", "#161638", "#2a1d4a", "#4a2a5c"]
for y in range(H):
    t = min(1, y / 62) * (len(SKY) - 1); i = int(t); f = t - i
    for x in range(W): put(x, y, SKY[min(i + (1 if f * 16 > B[y % 4][x % 4] else 0), len(SKY) - 1)])
for _ in range(40):
    put(random.randrange(W), random.randrange(34), random.choice(["#c8cff5", "#7f88c8", "#eef0ff"]))
# red moon
mx, my, r = 44, 17, 8
for y in range(my - r, my + r + 1):
    for x in range(mx - r, mx + r + 1):
        d = math.hypot(x - mx, y - my)
        if d <= r + .5: put(x, y, mix(x, y, "#e8453c", "#f2765a", (y - (my - r)) / (2 * r)))
        elif d <= r + 2.5 and B[y % 4][x % 4] < 4: put(x, y, "#5a2a55")
# Fuji
def fuji(cx, base, h, w, col, snow):
    for y in range(base - h, base):
        half = (y - (base - h)) / h * w
        for x in range(int(cx - half), int(cx + half) + 1):
            put(x, y, col)
            if y - (base - h) < h * .22 and abs(x - cx) < half * .8 + (1 if (x + y) % 3 == 0 else -1):
                put(x, y, snow)
fuji(18, 62, 28, 30, "#1b1840", "#8b86c4")
for x in range(W):
    h = 3 * math.sin(x / 6 + 1) + 2 * math.sin(x / 2.7)
    for y in range(int(58 - h), 64): put(x, y, "#10102a")
# distant pagoda
for (x0, y0, w) in [(8, 50, 8), (9, 46, 6), (10, 43, 4)]:
    rect(x0, y0, x0 + w, y0 + 3, "#0a0a1a"); rect(x0 - 1, y0 - 1, x0 + w + 1, y0, "#0a0a1a")
rect(11, 40, 12, 43, "#0a0a1a")
# ground and steps
rect(0, 64, W, H, "#0a0b18")
for i, y in enumerate(range(70, 112, 3)):
    half = 8 + i * 2
    for x in range(32 - half, 32 + half):
        put(x, y, mix(x, y, "#3a3552", "#2b2740", .4)); put(x, y + 1, "#1d1a30"); put(x, y + 2, "#13122a")
# torii
R1, R2, RD = "#d8372f", "#a5231f", "#1a0a12"
def pillar(x0):
    rect(x0, 46, x0 + 5, 86, R1); rect(x0 + 3, 46, x0 + 5, 86, R2)
    rect(x0 - 1, 84, x0 + 6, 87, RD); rect(x0 - 1, 83, x0 + 6, 84, "#3a3552")
pillar(15); pillar(44)
rect(10, 34, 54, 38, RD); rect(10, 35, 54, 37, R1)            # kasagi
for k in range(7): put(8 + k, 33 - k // 3, RD); put(55 - k, 33 - k // 3, RD)
rect(7, 31, 12, 35, R1); rect(52, 31, 57, 35, R1)
rect(12, 40, 52, 43, R1); rect(12, 43, 52, 44, R2)            # nuki
rect(29, 38, 35, 46, "#e9c46a"); rect(30, 39, 34, 45, "#1a0a12")  # plaque
for yy in range(40, 45): put(31, yy, "#e9c46a") if yy % 2 else None
# stone lanterns with glow
def lantern(cx, base):
    rect(cx - 2, base - 3, cx + 3, base, "#4a4666"); rect(cx - 1, base - 9, cx + 2, base - 3, "#5a5678")
    rect(cx - 3, base - 12, cx + 4, base - 9, "#3a3656"); rect(cx - 1, base - 8, cx + 2, base - 5, "#ffc86b")
    rect(cx - 2, base - 15, cx + 3, base - 12, "#2e2b4a"); rect(cx - 1, base - 16, cx + 2, base - 15, "#4a4666")
    for dy in range(-12, 4):
        for dx in range(-9, 10):
            d = math.hypot(dx, dy * 1.3)
            if 2.5 < d < 9 and B[(base + dy) % 4][(cx + dx) % 4] < int(9 - d):
                x, y = cx + dx, base - 6 + dy
                if g.get((x, y), "#0a0b18") in ("#0a0b18", "#13122a", "#1d1a30", "#2b2740", "#3a3552", "#0d1024", "#161638"):
                    put(x, y, "#6a4a42")
lantern(7, 92); lantern(57, 92)
# sakura branch, top left, with drifting petals
for x, y in [(0, 4), (4, 6), (8, 5), (12, 8), (16, 7), (20, 10), (24, 9)]:
    rect(x, y, x + 5, y + 1, "#3a1f2a")
for cx, cy in [(4, 8), (9, 11), (14, 12), (19, 14), (3, 15), (24, 13), (11, 4), (17, 3)]:
    for dx in range(-3, 4):
        for dy in range(-2, 3):
            if dx * dx / 9 + dy * dy / 4 <= 1 and B[(cy + dy) % 4][(cx + dx) % 4] < 12:
                put(cx + dx, cy + dy, "#f4b6c8" if (dx + dy) % 2 else "#e58ba8")
for _ in range(16):
    x, y = random.randrange(W), random.randrange(24, 100)
    put(x, y, "#f4b6c8"); put(x + 1, y, "#e58ba8")
runs = []
for y in range(H):
    x = 0
    while x < W:
        c = g[(x, y)]; n = 1
        while x + n < W and g[(x + n, y)] == c: n += 1
        runs.append((c, x, y, n)); x += n
rects = "".join(f'<rect x="{x*PX}" y="{y*PX}" width="{n*PX}" height="{PX}" fill="{c}"/>' for c, x, y, n in sorted(runs))
open(sys.argv[1], "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*PX}" height="{H*PX}" viewBox="0 0 {W*PX} {H*PX}" shape-rendering="crispEdges" role="img"><title>A shrine gate at night</title>{rects}</svg>\n')
