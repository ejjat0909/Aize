"""Aize map pins — original, procedural, viewport-aligned badges on a stalk (no third-party geometry or glyphs).

A pin is a coloured disc badge with a white relief glyph on a short stalk.  It is VIEWPORT-ALIGNED: the badge sits the same
distance above its anchor on screen at every camera pitch (that is how map markers work), so it is modelled lying flat and rendered
once, top-down, with +Y as screen-up.  The anchor (foot of the stalk) is the world origin.  There are no pitch buckets and no
warp: the app draws the sprite unrotated and unscaled, and the ground contact shadow is a separate, map-aligned circle layer
(`circle-pitch-alignment: map` squashes it with the pitch for free).

Units: badge radius 1 u.  Colours: design/tokens `pins.<kind>.{badge,glyph}` (contrast-audited), so a token change re-colours the pins.
Glyphs are drawn from a tiny 2-D shape vocabulary inside |x|,|y| <= 0.62 and extruded as relief.
"""
import math

import bmesh
from mathutils import Matrix

import lib_aize as L
from asset_pointer import _hard_surface, _prism

R_BADGE = 1.0
RISE = 2.0              # screen distance from the anchor to the badge centre (u)
FACE_Z = 0.15           # top face of the badge relative to its centre
HALF_U = 2.0            # square frame half extent
ANCHOR_Y = 0.88         # the anchor sits at 88 % of the frame height from the top (room for the badge above it, the foot shadow below)


# --------------------------------------------------------------------------------------------- 2-D shape vocabulary
def circle(cx, cy, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def rbar(cx, cy, w, h, r=None, n=8):
    """Rounded rectangle (stadium when r = h/2), CCW."""
    r = min(r if r is not None else h / 2, w / 2, h / 2)
    pts = []
    for (ox, oy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180), (w / 2 - r, -h / 2 + r, 270)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + ox + r * math.cos(a), cy + oy + r * math.sin(a)))
    return pts


def star(cx, cy, r_out, r_in, n):
    pts = []
    for i in range(2 * n):
        a = math.pi / 2 + math.pi * i / n
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def teardrop(cx, cy, r, tip_dy, n=28):
    """Circle of radius r at (cx, cy) with a pointed tip `tip_dy` above its centre (tangent lines), CCW, starting at the tip."""
    alpha = math.degrees(math.acos(r / tip_dy))                    # tangent points sit at 90 +- alpha degrees
    a0, a1 = 90.0 + alpha, 90.0 - alpha + 360.0
    pts = [(cx, cy + tip_dy)]
    for i in range(n + 1):
        a = math.radians(a0 + (a1 - a0) * i / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _glyph_layers(kind):
    """-> list of (polygon, layer) with layer 0 = glyph-coloured relief, 1 = badge-coloured relief on top of layer 0."""
    G, D = 0, 1
    if kind == "hazard":
        return [([(0.0, 0.58), (-0.60, -0.42), (0.60, -0.42)], G), (rbar(0.0, 0.02, 0.11, 0.42, 0.055), D), (circle(0.0, -0.27, 0.07, 20), D)]
    if kind == "police":
        return [([(-0.46, 0.55), (0.46, 0.55), (0.46, 0.02), (0.0, -0.62), (-0.46, 0.02)], G), (star(0.0, 0.10, 0.27, 0.11, 5), D)]
    if kind == "accident":
        return [(star(0.0, 0.0, 0.64, 0.38, 9), G), (rbar(0.0, 0.07, 0.11, 0.34, 0.055), D), (circle(0.0, -0.22, 0.065, 20), D)]
    if kind == "jam":
        return [(rbar(0.0, 0.34, 0.92, 0.24), G), (rbar(-0.08, 0.0, 0.76, 0.24), G), (rbar(-0.16, -0.34, 0.60, 0.24), G), (circle(0.46, -0.34, 0.10, 20), G)]
    if kind == "closure":
        return [(circle(0.0, 0.0, 0.56, 48), G), (rbar(0.0, 0.0, 0.80, 0.20, 0.05), D)]
    if kind == "camera":
        return [(rbar(0.0, -0.02, 1.00, 0.66, 0.14), G), ([(-0.20, 0.30), (0.20, 0.30), (0.12, 0.46), (-0.12, 0.46)], G), (circle(0.0, -0.02, 0.24, 36), D), (circle(0.0, -0.02, 0.11, 24), G)]
    if kind == "gas":
        return [(teardrop(0.0, -0.10, 0.44, 0.74), G), (rbar(-0.14, -0.14, 0.10, 0.30, 0.05), D)]
    if kind == "parking":
        stem = rbar(-0.20, 0.0, 0.22, 1.16, 0.06)
        bowl = [(-0.12, 0.58), (0.10, 0.58)] + [(0.10 + 0.34 * math.sin(math.radians(a)), 0.24 + 0.34 * math.cos(math.radians(a))) for a in range(0, 181, 15)] + [(0.10, -0.10), (-0.12, -0.10)]
        hole = [(-0.02, 0.43), (0.10, 0.43)] + [(0.10 + 0.19 * math.sin(math.radians(a)), 0.24 + 0.19 * math.cos(math.radians(a))) for a in range(0, 181, 15)] + [(0.10, 0.05), (-0.02, 0.05)]
        return [(stem, G), (bowl, G), (hole, D)]
    if kind == "destination":
        # a chequered pennant on a pole
        pole = rbar(-0.34, -0.02, 0.12, 1.22, 0.06)
        flag = [(-0.28, 0.58), (0.52, 0.58), (0.52, -0.06), (-0.28, -0.06)]
        checks = [([(x0, y0), (x0 + 0.2, y0), (x0 + 0.2, y0 + 0.2), (x0, y0 + 0.2)], D) for (x0, y0) in ((-0.28, 0.38), (0.12, 0.38), (-0.08, 0.18), (0.32, 0.18), (-0.28, -0.02), (0.12, -0.02))
                  if y0 > -0.04 or True]
        checks = [c for c in checks if c[0][2][1] <= 0.58 + 1e-6 and c[0][1][0] <= 0.52 + 1e-6]
        return [(pole, G), (flag, G)] + checks
    raise KeyError(kind)


KINDS = ["police", "hazard", "accident", "jam", "closure", "camera", "gas", "parking", "destination"]


def build_pin(tk, kind):
    root = L.empty(f"Pin_{kind}")
    pc = tk["pins"][kind]
    mats = {"body": L.make_material("Badge", pc["badge"], rough=0.32, coat=0.7, coat_rough=0.07, spec=0.5),
            "rim": L.make_material("Rim", "#FFFFFF", rough=0.38, coat=0.25, spec=0.4, mul=0.97),
            "glyph": L.make_material("Glyph", pc["glyph"], rough=0.36, coat=0.2, spec=0.4, mul=0.97),
            "dark": L.make_material("GlyphDark", pc["badge"], rough=0.34, coat=0.5, spec=0.4, mul=0.80),
            "stalk": L.make_material("Stalk", tk["color"]["neutral"]["700"], rough=0.45, spec=0.3),
            "foot": L.make_material("Foot", tk["color"]["neutral"]["900"], rough=0.5, spec=0.3)}
    objs = []

    def cyl(name, r, z0, z1, cx, cy, mat, seg=64):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=z1 - z0, matrix=Matrix.Translation((cx, cy, (z0 + z1) / 2)))
        return L.mesh_object(name, bm, mat, root)

    # everything lies flat: z is the relief height, +Y is screen-up, the anchor is the origin
    zb = 0.17                                                           # badge rim bottom sits on the ground; badge centre height
    stalk = _prism("Stalk", rbar(0.0, (RISE - 0.35) / 2, 0.17, RISE - 0.35, 0.085), 0.0, 0.17, mats["stalk"], root)
    _hard_surface(stalk, bevel=0.03, segments=2, angle=30)
    foot = cyl("Foot", 0.27, 0.0, 0.07, 0.0, 0.0, mats["foot"], 36)
    _hard_surface(foot, bevel=0.02, segments=2, angle=30)
    rim = cyl("BadgeRim", R_BADGE + 0.13, 0.0, 0.25, 0.0, RISE, mats["rim"], 72)
    _hard_surface(rim, bevel=0.06, segments=3, angle=30)
    body = cyl("BadgeBody", R_BADGE, 0.07, zb + FACE_Z, 0.0, RISE, mats["body"], 72)
    _hard_surface(body, bevel=0.07, segments=3, angle=30)
    objs += [stalk, foot, rim, body]
    top = zb + FACE_Z - 0.01
    for i, (pts, layer) in enumerate(_glyph_layers(kind)):
        z0, z1 = (top, top + 0.085) if layer == 0 else (top + 0.07, top + 0.14)
        g = _prism(f"Glyph{i}", [(x, y + RISE) for x, y in pts], z0, z1, mats["glyph"] if layer == 0 else mats["dark"], root)
        _hard_surface(g, bevel=0.018, segments=2, angle=35)
        objs.append(g)
    return root, objs


def _wrap(kind):
    return lambda tk: build_pin(tk, kind)


REGISTRY = {
    f"pin_{k}": dict(build=_wrap(k), yaws=1, frame_dp=64, shadow_margin=0.0, lights=True, shadow=True, half_u=HALF_U, anchor_y=ANCHOR_Y, kind="billboard")
    for k in KINDS
}
