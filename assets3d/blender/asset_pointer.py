"""Aize position pointer — original design, built procedurally (no third-party geometry).

  arrow  "Folded Arrow": a violet faceted tent (ridge from nose to tail notch) standing on a white rim slab.
         Heading known -> the arrow is rendered at 24 yaws x N pitches.
  puck   round white-rimmed violet dome with a white centre dot: used when there is no heading (no compass, standing).
  calib  geometry-only target used by tools/verify_sprites.py to prove the camera maths (foreshortening + anchor).

All colours come from design/tokens/aize-purple.tokens.json (`color.purple.600` = brand violet).
"""
import math

import bmesh
import bpy
from mathutils import Matrix

import lib_aize as L

# footprint of the arrow seen from above, counter-clockwise; +Y = nose
NOSE, LEFT, NOTCH, RIGHT = (0.0, 1.30), (-1.0, -1.0), (0.0, -0.42), (1.0, -1.0)


def _centroid(pts):
    a = cx = cy = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def _offset(pts, d):
    """Miter offset of a CCW polygon by `d` (outward). Miters are clamped so the sharp nose does not spike."""
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        e1 = (p1[0] - p0[0], p1[1] - p0[1])
        e2 = (p2[0] - p1[0], p2[1] - p1[1])
        l1, l2 = math.hypot(*e1), math.hypot(*e2)
        n1 = (e1[1] / l1, -e1[0] / l1)
        n2 = (e2[1] / l2, -e2[0] / l2)
        k = d / (1.0 + n1[0] * n2[0] + n1[1] * n2[1])
        mx, my = (n1[0] + n2[0]) * k, (n1[1] + n2[1]) * k
        ml = math.hypot(mx, my)
        cap = 1.9 * abs(d)
        if ml > cap:
            mx, my = mx * cap / ml, my * cap / ml
        out.append((p1[0] + mx, p1[1] + my))
    return out


def _prism(name, pts, z0, z1, material, parent):
    """Straight prism over a (possibly concave) CCW polygon."""
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in pts]
    top = [bm.verts.new((x, y, z1)) for x, y in pts]
    bm.faces.new(top)
    bm.faces.new(list(reversed(bot)))
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((top[i], bot[i], bot[j], top[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return L.mesh_object(name, bm, material, parent)


def _hard_surface(ob, bevel=0.05, segments=3, angle=24, profile=0.5):
    """Bevel the edges, then weighted-normal shading: big faces stay flat (crisp facets), bevels stay smooth (highlights)."""
    L.add_modifier(ob, "BEVEL", width=bevel, segments=segments, limit_method="ANGLE", angle_limit=math.radians(angle), profile=profile)
    L.bake_modifiers(ob)
    for p_ in ob.data.polygons:
        p_.use_smooth = True
    L.add_modifier(ob, "WEIGHTED_NORMAL", mode="FACE_AREA", weight=60, keep_sharp=False, thresh=0.01)
    L.bake_modifiers(ob)


def build_arrow(tk, variant="", tune="", h_tip=0.85, h_notch=0.44, h_wing=0.06, rim=0.18, rim_h=0.15, body_hex=None, rim_hex="#FFFFFF"):
    kv = dict(x.split("=") for x in tune.split(";") if "=" in x)
    h_tip, h_notch, h_wing = float(kv.get("h_tip", h_tip)), float(kv.get("h_notch", h_notch)), float(kv.get("h_wing", h_wing))
    rim, rim_h = float(kv.get("rim", rim)), float(kv.get("rim_h", rim_h))
    root = L.empty("ArrowRoot")
    body_hex = body_hex or tk["color"]["purple"]["600"]
    mat_body = L.make_material("ArrowBody", body_hex, rough=0.30, coat=0.65, coat_rough=0.08, spec=0.5)
    mat_rim = L.make_material("ArrowRim", rim_hex, rough=0.42, coat=0.20, spec=0.4, mul=0.96)

    pts = [NOSE, LEFT, NOTCH, RIGHT]
    cx, cy = _centroid(pts)
    pts = [(x - cx, y - cy) for x, y in pts]

    slab = _prism("ArrowRim", _offset(pts, rim), 0.0, rim_h, mat_rim, root)
    _hard_surface(slab, bevel=0.055, segments=3, angle=30)

    z0 = rim_h - 0.02
    bm = bmesh.new()
    tops = [bm.verts.new((x, y, z0 + h)) for (x, y), h in zip(pts, [h_tip, h_wing, h_notch, h_wing])]
    bots = [bm.verts.new((x, y, z0)) for x, y in pts]
    T, Lf, N, R = tops
    Tb, Lb, Nb, Rb = bots
    bm.faces.new((T, Lf, N))
    bm.faces.new((T, N, R))
    bm.faces.new((Tb, Rb, Nb))
    bm.faces.new((Tb, Nb, Lb))
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new((tops[i], bots[i], bots[j], tops[j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    tent = L.mesh_object("ArrowTent", bm, mat_body, root)
    _hard_surface(tent, bevel=0.070, segments=4, angle=14, profile=0.55)
    return root, [slab, tent]


def build_puck(tk, body_hex=None):
    root = L.empty("PuckRoot")
    body_hex = body_hex or tk["color"]["purple"]["600"]
    mat_body = L.make_material("PuckBody", body_hex, rough=0.26, coat=0.75, coat_rough=0.05, spec=0.55)
    mat_rim = L.make_material("PuckRim", "#FFFFFF", rough=0.38, coat=0.25, spec=0.4, mul=0.97)

    def cyl(name, r, z0, z1, mat, seg=72):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r, radius2=r, depth=z1 - z0,
                              matrix=Matrix.Translation((0, 0, (z0 + z1) / 2)))
        return L.mesh_object(name, bm, mat, root)

    slab = cyl("PuckRim", 1.0, 0.0, 0.14, mat_rim)
    _hard_surface(slab, bevel=0.055, segments=3, angle=30)

    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=36, radius=1.0)
    # only the upper hemisphere exists: the lower half would be buried in the rim slab (and below the ground), never visible
    bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), plane_co=(0, 0, 0), plane_no=(0, 0, 1), clear_inner=True)
    bmesh.ops.scale(bm, vec=(0.78, 0.78, 0.40), verts=bm.verts)
    bmesh.ops.translate(bm, vec=(0, 0, 0.14), verts=bm.verts)
    dome = L.mesh_object("PuckDome", bm, mat_body, root)
    L.smooth_by_angle(dome, 80)

    dot = cyl("PuckDot", 0.20, 0.14 + 0.40 - 0.045, 0.14 + 0.40 + 0.012, mat_rim, seg=48)
    _hard_surface(dot, bevel=0.02, segments=2, angle=30)
    return root, [slab, dome, dot]


def build_calibration(tk):
    """Flat unit disc (grey) + small centre dot (white), both emissive: aspect must equal cos(pitch), dot must sit at
    the frame centre. Used only by the verifier."""
    root = L.empty("CalibRoot")
    grey = L.make_material("CalGrey", "#808080", emit_hex="#808080", emit_strength=1.0)
    white = L.make_material("CalWhite", "#FFFFFF", emit_hex="#FFFFFF", emit_strength=1.0)
    objs = []
    for name, r, z, mat in (("CalDisc", 0.8, 0.0005, grey), ("CalDot", 0.05, 0.001, white)):
        bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=128, radius=r, matrix=Matrix.Translation((0, 0, z)))
        objs.append(L.mesh_object(name, bm, mat, root))
    return root, objs
