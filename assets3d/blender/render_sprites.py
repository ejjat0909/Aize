"""Render pre-rendered sprite frames (pitch x yaw) for one Aize 3D asset, headlessly, in TWO layers per frame.

  blender -b --factory-startup -P assets3d/blender/render_sprites.py -- \
      --asset arrow --pitches 0,15,30,45,60 --size 416 --samples 48 --out build/frames [--glb out/arrow.glb]

Per frame it writes
    <asset>_p<PP>_y<KK>.png      the object only (RGBA, straight alpha, no ground)
    <asset>_p<PP>_y<KK>.sh.png   the ground shadow only (black, alpha = shadow density; rendered at half resolution)
tools/pack_atlas.py composites them (tint, opacity and blur of the shadow are tuned there without re-rendering).

PP = pitch degrees (from nadir, MapLibre convention); KK = yaw index, yaw = KK * 360 / yaws (clockwise from screen-up).
The world origin (the object's ground anchor) is the exact centre of every frame and every frame has the same
pixels-per-world-unit, so the app can pick any frame without re-scaling.
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402

import asset_pointer as AP  # noqa: E402
import lib_aize as L  # noqa: E402

# builder, default yaw count, nominal frame size on screen (dp), shadow margin (world units), key lighting on?
def pname(p):
    """File-name token for a pitch: 'p30' for 30, 'p07d50' for 7.5 (same function as tools/sprite_lib.pname)."""
    p = float(p)
    return f"p{int(p):02d}" if p.is_integer() else f"p{int(p):02d}d{int(round((p - int(p)) * 100)):02d}"


REGISTRY = {
    "arrow": dict(build=AP.build_arrow, takes_params=True, yaws=24, frame_dp=104, shadow_margin=0.42, lights=True, shadow=True),
    "puck": dict(build=AP.build_puck, yaws=1, frame_dp=104, shadow_margin=0.42, lights=True, shadow=True),
    "calib": dict(build=AP.build_calibration, yaws=1, frame_dp=104, shadow_margin=0.0, lights=False, shadow=False, half_u=2.4),
}
try:  # map pins (billboard assets)
    import asset_pins as APIN  # noqa: E402

    REGISTRY.update(APIN.REGISTRY)
except ImportError:
    pass
except Exception as exc:
    print('WARNING: asset_pins failed to import:', repr(exc))
try:  # vehicles are optional (phase B)
    import asset_vehicles as AV  # noqa: E402

    REGISTRY.update(AV.REGISTRY)
except ImportError:
    pass
except Exception as exc:  # a broken optional module must not take the pointer pipeline down, but must be visible
    print('WARNING: asset_vehicles failed to import:', repr(exc))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset", required=True)
    ap.add_argument("--pitches", default="0,15,30,45,60")
    ap.add_argument("--yaws", type=int, default=0, help="override yaw count (0 = asset default)")
    ap.add_argument("--frames", default="", help="explicit list 'pitch:yawIndex,...' (debug / re-render)")
    ap.add_argument("--size", type=int, default=416)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--shadow-samples", type=int, default=24)
    ap.add_argument("--out", required=True)
    ap.add_argument("--glb", default="")
    ap.add_argument("--variant", default="", help="asset variant that becomes part of the file names (vehicles: body colour key)")
    ap.add_argument("--anchor-y", type=float, default=-1.0, help="override the asset's anchor (fraction of frame height from the top); used by the calibration test")
    ap.add_argument("--tune", default="", help="builder experiment parameters 'k=v;k=v' (never part of file names)")
    a = ap.parse_args(L.script_args())

    if a.asset not in REGISTRY:
        raise SystemExit(f"unknown asset {a.asset!r}; known: {sorted(REGISTRY)}")
    spec = REGISTRY[a.asset]
    yaws = a.yaws or spec["yaws"]
    L.reset_scene()
    L.setup_render(a.size, samples=a.samples, denoise=spec["lights"])
    tk = L.tokens()
    if spec["lights"]:
        L.studio_rig()
    else:
        L.set_world_gradient("#000000", "#000000", strength=0.0)
    root, objs = spec["build"](tk, variant=a.variant, tune=a.tune) if spec.get("takes_params") else spec["build"](tk)
    ground = L.add_ground_catcher()

    R, H = L.mesh_radius_height(objs)
    half = spec.get("half_u") or L.frame_half_extent(R, H, spec["shadow_margin"])
    anchor_y = a.anchor_y if a.anchor_y >= 0 else spec.get("anchor_y", 0.5)
    pitches = [float(p) for p in a.pitches.split(",") if p != ""]
    cam = L.add_camera(pitches[0], half, anchor_y=anchor_y)

    jobs = []
    if a.frames:
        for item in a.frames.split(","):
            p, k = item.split(":")
            jobs.append((float(p), int(k)))
    else:
        jobs = [(p, k) for p in pitches for k in range(yaws)]

    os.makedirs(a.out, exist_ok=True)
    sc = bpy.context.scene
    for p, k in jobs:
        L.set_camera_pitch(cam, p)
        root.rotation_euler.z = -math.radians(k * 360.0 / yaws)
        if spec.get("on_frame"):
            spec["on_frame"](root, p, k)
        base = os.path.join(a.out, f"{a.asset}{('_' + a.variant) if a.variant else ''}_{pname(p)}_y{k:02d}")
        # --- layer 1: the object
        L.shadow_pass(objs, ground, False)
        L.key_for_shadow(False)
        sc.render.resolution_percentage = 100
        sc.cycles.samples = a.samples
        L.render_to(base + ".png")
        # --- layer 2: the ground shadow only (soft, so half resolution is plenty)
        if spec["shadow"]:
            L.shadow_pass(objs, ground, True)
            L.key_for_shadow(True)
            sc.render.resolution_percentage = 50
            sc.cycles.samples = a.shadow_samples
            L.render_to(base + ".sh.png")
    sc.render.resolution_percentage = 100

    manifest = {
        "asset": a.asset, "variant": a.variant or None, "pitches": sorted({(int(p) if float(p).is_integer() else round(float(p), 2)) for p, _ in jobs}), "yaws": yaws,
        "yaw_step_deg": 360.0 / yaws, "render_px": a.size, "frame_dp": spec["frame_dp"],
        "frame_half_extent_u": half, "anchor": [0.5, anchor_y], "kind": spec.get("kind", "solid"), "badge_height_u": spec.get("badge_height_u"),
        "px_per_unit": a.size / (2 * half), "unit_dp": spec["frame_dp"] / (2 * half),
        "object_radius_u": R, "object_height_u": H, "shadow_margin_u": spec["shadow_margin"],
        "rig": L.RIG, "samples": a.samples, "shadow_samples": a.shadow_samples, "blender": bpy.app.version_string,
        "camera": {"model": "perspective, long lens (distance = 28 x half extent), looks at the origin; origin = frame centre",
                   "pitch": "degrees from nadir (MapLibre convention)", "yaw": "clockwise from up-the-screen"},
    }
    with open(os.path.join(a.out, f"{a.asset}{('_' + a.variant) if a.variant else ''}.manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)

    if a.glb:
        L.shadow_pass(objs, ground, False)
        root.rotation_euler.z = 0
        L.export_glb(L.descendants(root)[1:], a.glb)
    print("RENDERED", len(jobs), "frames ->", a.out, "| R=%.3f H=%.3f half=%.3f" % (R, H, half))


main()
