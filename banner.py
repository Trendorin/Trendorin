"""Pixel-art banner: dithered night sky, moon, stars, layered mountains. python3 banner.py OUT.svg"""
import math, random, sys
W, H, PX = 172, 40, 5          # grid cells, cell size → 860 x 200
random.seed(7)
BAYER = [[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
SKY = ["#0b1020","#111a33","#18254a","#22336a"]          # top → horizon
RIDGES = [("#1c2b52", 0.42, 3.2, 0.9), ("#141f3d", 0.58, 2.6, 2.1), ("#0c142b", 0.74, 2.0, 4.0)]
cells = {}
def put(x, y, c): 
    if 0 <= x < W and 0 <= y < H: cells[(x, y)] = c
# dithered sky
for y in range(H):
    t = y / (H * 0.8)
    for x in range(W):
        v = min(t, 0.999) * (len(SKY) - 1)
        i = int(v); f = v - i
        c = SKY[min(i + (1 if f * 16 > BAYER[y % 4][x % 4] else 0), len(SKY) - 1)]
        put(x, y, c)
# stars
for _ in range(46):
    x, y = random.randrange(W), random.randrange(int(H * 0.55))
    put(x, y, random.choice(["#c9d3ff", "#8fa0e8", "#e8ecff"]))
# moon
mx, my, r = 138, 11, 5
for y in range(my - r, my + r + 1):
    for x in range(mx - r, mx + r + 1):
        d = math.hypot(x - mx, y - my)
        if d <= r:
            shade = math.hypot(x - mx + 2, y - my + 1) > r - 0.5
            put(x, y, "#cfd6f5" if shade else "#f4f6ff")
for (dx, dy) in [(-1, -1), (2, 1), (0, 2)]:
    put(mx + dx, my + dy, "#b6bfe6")
# ridges
for col, base, amp, ph in RIDGES:
    for x in range(W):
        h = base * H + amp * 2.2 * math.sin(x / 11 + ph) + amp * 1.4 * math.sin(x / 4.3 + ph * 2) + amp * math.sin(x / 27 + ph)
        for y in range(int(h), H): put(x, y, col)
runs = []
for y in range(H):
    x = 0
    while x < W:
        c = cells[(x, y)]; n = 1
        while x + n < W and cells[(x + n, y)] == c: n += 1
        runs.append((c, x, y, n)); x += n
rects = "".join(f'<rect x="{x*PX}" y="{y*PX}" width="{n*PX}" height="{PX}" fill="{c}"/>' for c, x, y, n in sorted(runs))
open(sys.argv[1], "w").write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W*PX}" height="{H*PX}" viewBox="0 0 {W*PX} {H*PX}" shape-rendering="crispEdges" role="img"><title>Trendorin</title>{rects}</svg>\n')
