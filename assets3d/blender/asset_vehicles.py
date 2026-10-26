"""Aize vehicle skins — original, procedural, low-poly toy-style cars (no third-party geometry).

One parametric builder, five bodies:  sedan · hatch · suv · taxi · van.   Units: 1 u ~ 1 m, +Y = forward, +X = right, +Z = up,
origin = point on the ground under the middle of the car.  Every car is built from:
  lower body  (side-profile polygon extruded across the width, plan-view taper, bevel + weighted normals)
  greenhouse  (8-vertex loft: paint roof, glass windscreen/rear/side windows with B-pillars)
  wheels (tyre + rim), headlights/taillights (emissive), mirrors, optional roof sign.
Paint colours come from the design tokens, so a token change re-colours the fleet.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

import lib_aize as L
from asset_pointer import _hard_surface

# name: (colour token path, body params)
#   L,W: length/width · belt: beltline height · roof: roof height · y_*: greenhouse corner positions along the car
#   wr: wheel radius · wb: wheelbase · cl: ground clearance · hood_z/trunk_z: heights of the bonnet and boot lids
KINDS = {
    "sedan": dict(color=("purple", "600"), L=4.50, W=1.82, belt=0.98, roof=1.44, y_fb=0.95, y_ft=0.12, y_rt=-1.00, y_rb=-1.50, wr=0.34, wb=2.70, cl=0.20, hood_z=0.90, trunk_z=0.96, taper_f=0.90, taper_r=0.93, pillars=True),
    "hatch": dict(color=("lilac", "500"), L=3.95, W=1.76, belt=0.98, roof=1.48, y_fb=0.80, y_ft=0.10, y_rt=-1.05, y_rb=-1.62, wr=0.32, wb=2.45, cl=0.20, hood_z=0.90, trunk_z=1.15, taper_f=0.90, taper_r=0.96, pillars=True),
    "suv": dict(color=("mint", "600"), L=4.70, W=1.96, belt=1.10, roof=1.78, y_fb=0.80, y_ft=0.32, y_rt=-1.45, y_rb=-1.95, wr=0.40, wb=2.80, cl=0.28, hood_z=1.04, trunk_z=1.12, taper_f=0.92, taper_r=0.95, pillars=True),
    "taxi": dict(color=("amber", "500"), L=4.50, W=1.82, belt=0.98, roof=1.44, y_fb=0.95, y_ft=0.12, y_rt=-1.00, y_rb=-1.50, wr=0.34, wb=2.70, cl=0.20, hood_z=0.90, trunk_z=0.96, taper_f=0.90, taper_r=0.93, pillars=True, sign=True),
    "van": dict(color=("neutral", "50"), L=5.20, W=2.00, belt=1.12, roof=2.05, y_fb=1.62, y_ft=1.30, y_rt=-2.45, y_rb=-2.55, wr=0.38, wb=3.20, cl=0.26, hood_z=1.02, trunk_z=1.05, taper_f=0.94, taper_r=0.98, pillars=True),
}


def _loft_body(name, p, mats, parent):
    """Lower body: side profile in the (y,z) plane extruded across the width, with plan-view taper at both ends."""
    Ln, hz, tz, cl, bz = p["L"], p["hood_z"], p["trunk_z"], p["cl"], p["belt"]
    hw = p["W"] / 2 - 0.02
    prof = [(Ln / 2, cl + 0.10), (Ln / 2, cl + 0.45), (Ln / 2 - 0.12, hz - 0.08), (Ln / 2 - 0.55, hz), (p["y_fb"], bz),
            (p["y_rb"], bz + (tz - bz) * 0.4), (-Ln / 2 + 0.35, tz), (-Ln / 2 + 0.06, tz - 0.12), (-Ln / 2, cl + 0.55), (-Ln / 2, cl + 0.10),
            (-Ln / 2 + 0.55, cl), (Ln / 2 - 0.55, cl)]
    bm = bmesh.new()
    left = [bm.verts.new((-hw, y, z)) for y, z in prof]
    right = [bm.verts.new((hw, y, z)) for y, z in prof]
    n = len(prof)
    bm.faces.new(list(reversed(left)))
    bm.faces.new(right)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((left[i], left[j], right[j], right[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for v in bm.verts:   # plan-view taper: narrower nose and tail
        if v.co.y > 0.2:
            v.co.x *= 1.0 - (1.0 - p["taper_f"]) * min(1.0, (v.co.y - 0.2) / (Ln / 2 - 0.2)) ** 1.5
        elif v.co.y < -0.2:
            v.co.x *= 1.0 - (1.0 - p["taper_r"]) * min(1.0, (-v.co.y - 0.2) / (Ln / 2 - 0.2)) ** 1.5
    ob = L.mesh_object(name, bm, mats["paint"], parent)
    _hard_surface(ob, bevel=0.13, segments=4, angle=20, profile=0.55)
    return ob


def _greenhouse(name, p, mats, parent):
    """Cabin loft with paint roof + glass; side glass is split into two windows by a paint B-pillar."""
    bz, rz = p["belt"] - 0.02, p["roof"]
    hb, ht = p["W"] / 2 - 0.13, p["W"] / 2 - 0.30
    yfb, yft, yrt, yrb = p["y_fb"], p["y_ft"], p["y_rt"], p["y_rb"]
    bm = bmesh.new()
    V = lambda x, y, z: bm.verts.new((x, y, z))
    FBL, FBR, RBL, RBR = V(-hb, yfb, bz), V(hb, yfb, bz), V(-hb, yrb, bz), V(hb, yrb, bz)
    FTL, FTR, RTL, RTR = V(-ht, yft, rz), V(ht, yft, rz), V(-ht, yrt, rz), V(ht, yrt, rz)
    faces = {}
    faces["roof"] = bm.faces.new((FTL, FTR, RTR, RTL))
    faces["wind"] = bm.faces.new((FBL, FBR, FTR, FTL))
    faces["rear"] = bm.faces.new((RBR, RBL, RTL, RTR))
    bm.faces.new((RBL, RBR, FBR, FBL))                                  # floor (hidden)

    def side(sign):
        fb, rb, ft, rt = (FBR, RBR, FTR, RTR) if sign > 0 else (FBL, RBL, FTL, RTL)
        lerp = lambda a, b, t: bm.verts.new(a.co.lerp(b.co, t))
        # three bays along the side: front window | pillar | rear window (B-pillar a bit behind the middle)
        a0, a1 = 0.52, 0.60
        bb0, bb1 = lerp(fb, rb, a0), lerp(fb, rb, a1)
        tb0, tb1 = lerp(ft, rt, a0), lerp(ft, rt, a1)
        # pillar bays are slightly proud so the glass reads as inset
        g1 = bm.faces.new((fb, bb0, tb0, ft) if sign > 0 else (ft, tb0, bb0, fb))
        pl = bm.faces.new((bb0, bb1, tb1, tb0) if sign > 0 else (tb0, tb1, bb1, bb0))
        g2 = bm.faces.new((bb1, rb, rt, tb1) if sign > 0 else (tb1, rt, rb, bb1))
        return g1, pl, g2
    sides = side(+1) + side(-1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = L.mesh_object(name, bm, None, parent)
    ob.data.materials.append(mats["paint"])    # slot 0
    ob.data.materials.append(mats["glass"])    # slot 1
    for pg in ob.data.polygons:
        pg.material_index = 1
    # paint: roof (the top-facing polygon) and the pillar bays
    for pg in ob.data.polygons:
        n = pg.normal
        c = pg.center
        if n.z > 0.9:
            pg.material_index = 0
        elif abs(n.x) > 0.5 and abs(c.y - (yfb + (yrb - yfb) * 0.56)) < abs(yrb - yfb) * 0.07:
            pg.material_index = 0
    _hard_surface(ob, bevel=0.045, segments=2, angle=25, profile=0.5)
    return ob


def _box(name, size, loc, mat, parent, bevel=0.02):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2])) + Vector(loc)
    ob = L.mesh_object(name, bm, mat, parent)
    if bevel:
        _hard_surface(ob, bevel=bevel, segments=2, angle=30)
    return ob


def _wheel(name, x, y, r, w, mats, parent):
    out = []
    for kind, rad, wid, mat, dx in (("Tyre", r, w, mats["tyre"], 0.0), ("Rim", r * 0.62, w + 0.02, mats["rim"], 0.0)):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=40, radius1=rad, radius2=rad, depth=wid,
                              matrix=Matrix.Translation((x, y, r)) @ Matrix.Rotation(math.radians(90), 4, "Y"))
        ob = L.mesh_object(f"{name}{kind}", bm, mat, parent)
        if kind == "Tyre":
            _hard_surface(ob, bevel=0.05, segments=3, angle=30)
        out.append(ob)
    return out


def build_vehicle(tk, kind, paint_hex=None):
    p = KINDS[kind]
    root = L.empty(f"Car_{kind}")
    fam, step = p["color"]
    paint_hex = paint_hex or tk["color"][fam][step]
    mats = {
        "paint": L.make_material("Paint", paint_hex, rough=0.30, coat=0.8, coat_rough=0.05, spec=0.5),
        "glass": L.make_material("Glass", tk["color"]["neutral"]["950"], rough=0.06, coat=1.0, coat_rough=0.02, spec=0.8, mul=0.9),
        "tyre": L.make_material("Tyre", "#141218", rough=0.75, spec=0.2),
        "rim": L.make_material("Rim", tk["color"]["neutral"]["200"], rough=0.28, metal=1.0, spec=0.6),
        "head": L.make_material("Head", "#FFF1D0", rough=0.2, emit_hex="#FFF1D0", emit_strength=3.0),
        "tail": L.make_material("Tail", "#FF3040", rough=0.2, emit_hex="#FF2030", emit_strength=4.0),
        "trim": L.make_material("Trim", tk["color"]["neutral"]["900"], rough=0.55, spec=0.3),
        "sign": L.make_material("Sign", tk["color"]["amber"]["400"], rough=0.3, emit_hex=tk["color"]["amber"]["300"], emit_strength=2.0),
    }
    objs = [_loft_body("Body", p, mats, root), _greenhouse("Cabin", p, mats, root)]
    Ln, W, wr, wb = p["L"], p["W"], p["wr"], p["wb"]
    ww = 0.24 if kind != "van" else 0.26
    for sx in (-1, 1):
        for sy in (-1, 1):
            objs += _wheel(f"W{sx}{sy}", sx * (W / 2 - 0.05), sy * wb / 2, wr, ww, mats, root)
    # lights, bumper strips, mirrors
    z_head = p["cl"] + 0.48
    for sx in (-1, 1):
        objs.append(_box(f"Head{sx}", (0.38, 0.07, 0.13), (sx * (W / 2 - 0.36) * p["taper_f"], Ln / 2 - 0.045, z_head), mats["head"], root, 0.02))
        objs.append(_box(f"Tail{sx}", (0.46, 0.07, 0.12), (sx * (W / 2 - 0.32) * p["taper_r"], -Ln / 2 + 0.04, p["cl"] + 0.60), mats["tail"], root, 0.02))
        objs.append(_box(f"Mirror{sx}", (0.10, 0.20, 0.12), (sx * (W / 2 + 0.05), p["y_fb"] - 0.18, p["belt"] + 0.06), mats["paint"], root, 0.025))
    objs.append(_box("FrontStrip", (W * 0.62, 0.06, 0.10), (0, Ln / 2 - 0.02, p["cl"] + 0.24), mats["trim"], root, 0.02))
    objs.append(_box("RearStrip", (W * 0.62, 0.06, 0.10), (0, -Ln / 2 + 0.02, p["cl"] + 0.24), mats["trim"], root, 0.02))
    if p.get("sign"):
        objs.append(_box("RoofSign", (0.62, 0.22, 0.15), (0, (p["y_ft"] + p["y_rt"]) / 2, p["roof"] + 0.07), mats["sign"], root, 0.03))
    return root, objs


def _wrap(kind):
    return lambda tk: build_vehicle(tk, kind)


REGISTRY = {
    f"car_{k}": dict(build=_wrap(k), yaws=24, frame_dp=84, shadow_margin=0.55, lights=True, shadow=True) for k in KINDS
}
