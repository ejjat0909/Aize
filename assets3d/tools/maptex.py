"""Procedural top-down map texture in the Aize map style (for previews / the runtime simulation only).

World coordinates: (E, N) in texture pixels, origin = texture centre, N up.  Texture pixel = (T/2 + E, T/2 - N).
Everything is original and seeded; colours come from design/tokens (map.light / map.dark).
"""
import math
import random

from PIL import Image, ImageDraw

import sprite_lib as S

T = 6144
K = 2.0   # geometry scale: street ~44 px (about 15 dp at 3x) next to a ~190 px (63 dp) pointer, like a real navigation view


def _tok():
    import json
    return json.load(open(S.TOKENS))


def catmull_rom(points, samples_per_seg=24):
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(samples_per_seg):
            t = s / samples_per_seg
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(points[-1])
    return out


def to_tex(pt):
    return (T / 2 + pt[0], T / 2 - pt[1])


def build(theme="light", seed=7):
    tk = _tok()["map"][theme]
    rnd = random.Random(seed)
    rgb = S.hex_rgb
    im = Image.new("RGB", (T, T), rgb(tk["land"]))
    d = ImageDraw.Draw(im)

    # --- water: a river band across the south-east + a lake
    river = catmull_rom([(K * x, K * y) for x, y in [(-1700, -300), (-900, -700), (-200, -900), (500, -1500), (1700, -1700)]], 20)
    wl = [to_tex(p) for p in river]
    d.line(wl, fill=rgb(tk["water"]), width=int(190 * K), joint="curve")
    for p in wl:
        d.ellipse((p[0] - 95 * K, p[1] - 95 * K, p[0] + 95 * K, p[1] + 95 * K), fill=rgb(tk["water"]))
    lake = [to_tex((K * (1100 + 260 * math.cos(a / 18 * math.pi) * (1 + .18 * math.sin(a * 1.7))), K * (1050 + 190 * math.sin(a / 18 * math.pi) * (1 + .15 * math.cos(a * 1.3))))) for a in range(36)]
    d.polygon(lake, fill=rgb(tk["water"]))

    # --- street grid (jittered) -> blocks
    HALF = T // 2
    xs = [-HALF]
    while xs[-1] < HALF:
        xs.append(xs[-1] + int(K * rnd.randint(250, 340)))
    ys = [-HALF]
    while ys[-1] < HALF:
        ys.append(ys[-1] + int(K * rnd.randint(250, 340)))

    def river_dist(E, N):
        return min(math.hypot(E - p[0], N - p[1]) for p in river[::3])

    # parks: a few whole blocks
    park_cells = {(rnd.randrange(len(xs) - 1), rnd.randrange(len(ys) - 1)) for _ in range(9)}
    road_w_minor, road_w_major = int(22 * K), int(36 * K)
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            x0, x1, y0, y1 = xs[i] + 24 * K, xs[i + 1] - 24 * K, ys[j] + 24 * K, ys[j + 1] - 24 * K
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            if river_dist(cx, cy) < 150 * K:
                continue
            if (i, j) in park_cells:
                a, b = to_tex((x0, y1)), to_tex((x1, y0))
                d.rounded_rectangle((a[0], a[1], b[0], b[1]), radius=int(14 * K), fill=rgb(tk["park"]))
                continue
            nx, ny = rnd.choice((1, 2, 2, 3)), rnd.choice((1, 2, 2))
            for u in range(nx):
                for v in range(ny):
                    bx0 = x0 + (x1 - x0) * u / nx + int(K * rnd.randint(5, 14))
                    bx1 = x0 + (x1 - x0) * (u + 1) / nx - int(K * rnd.randint(5, 14))
                    by0 = y0 + (y1 - y0) * v / ny + int(K * rnd.randint(5, 14))
                    by1 = y0 + (y1 - y0) * (v + 1) / ny - int(K * rnd.randint(5, 14))
                    if bx1 - bx0 < 30 * K or by1 - by0 < 30 * K:
                        continue
                    a, b = to_tex((bx0, by1)), to_tex((bx1, by0))
                    d.rectangle((a[0], a[1], b[0], b[1]), fill=rgb(tk["building"]))

    def road(poly, w, fill, casing):
        pl = [to_tex(p) for p in poly]
        for width, col in ((w + int(8 * K), casing), (w, fill)):
            d.line(pl, fill=rgb(col), width=width, joint="curve")
            for p in pl[:: max(1, len(pl) // 400 or 1)]:
                d.ellipse((p[0] - width / 2, p[1] - width / 2, p[0] + width / 2, p[1] + width / 2), fill=rgb(col))

    for x in xs:
        road([(x, -HALF), (x, HALF)], road_w_minor, tk["roadMinor"], tk["roadMinorCasing"])
    for y in ys:
        road([(-HALF, y), (HALF, y)], road_w_minor, tk["roadMinor"], tk["roadMinorCasing"])
    # arterials (diagonal) and a highway (curved)
    road([(K * x, K * y) for x, y in [(-1536, -1000), (-400, -100), (500, 500), (1536, 1300)]], road_w_major, tk["roadMajor"], tk["roadMajorCasing"])
    road([(K * x, K * y) for x, y in [(-1536, 900), (-300, 700), (700, 1000), (1536, 700)]], road_w_major, tk["roadMajor"], tk["roadMajorCasing"])
    hw = catmull_rom([(K * x, K * y) for x, y in [(-1536, -200), (-800, 250), (0, 350), (900, 100), (1536, -300)]], 20)
    road(hw, int(52 * K), tk["highway"], tk["highwayCasing"])
    return im


def route_points():
    """The demo drive: smooth route through a handful of turns (world px)."""
    wp = [(K * x, K * y) for x, y in [(-1100, -1050), (-1100, -420), (-760, -60), (-180, 30), (330, 360), (420, 900), (760, 1180), (1250, 1230)]]
    return catmull_rom(wp, 40)
