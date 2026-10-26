#!/usr/bin/env python3
"""Pack rendered frames into per-pitch sprite sheets (one WebP per pitch per density tier) + a runtime manifest.

  python3 assets3d/tools/pack_atlas.py --frames build/frames/arrow --asset arrow --glb dist/arrow/arrow.glb --out dist/arrow \
          [--variant violet] [--webp lossy:92|lossless] [--tiers xxxhdpi:4,xxhdpi:3,xhdpi:2]

Input  : <asset>[_<variant>]_<pitch>_y<KK>.png (+ .sh.png)  and  <asset>[_<variant>].manifest.json   (render_sprites.py)
Output : <asset>[_<variant>]_<pitch>@<tier>.webp   sheets, grid = cols x rows of frame_px squares (row-major, yaw index k)
         <asset>[_<variant>].sprites.json         schema "aize-sprites/2" (see assets3d/README.md)
With --glb the manifest also records the MEASURED reconstruction error of the grid (worst / p95 / bucket-switch pop, in dp) and the
best re-projection plane height, computed from the actual mesh by reproject_error.py - the runtime and CI read those numbers.
"""
import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image  # noqa: E402

import reproject_error as RE  # noqa: E402
import sprite_lib as S  # noqa: E402


def grid_for(n):
    """cols x rows for n frames: the divisor pair of n closest to a square, wider than tall."""
    best = (n, 1)
    for r in range(1, n + 1):
        if n % r == 0 and n // r >= r and (n // r) - r < best[0] - best[1]:
            best = (n // r, r)
    return best


def save_webp(im, path, mode):
    if mode == "lossless":
        im.save(path, format="WEBP", lossless=True, quality=100, method=6, exact=False)
    else:
        q = int(mode.split(":")[1]) if ":" in mode else 92
        im.save(path, format="WEBP", lossless=False, quality=q, alpha_quality=100, method=6, exact=False)


def reprojection_block(v, unit_dp, grid, tune_path, symmetric=False):
    tune = json.load(open(tune_path)) if tune_path else None
    rep = RE.grid_report(v, unit_dp, grid, h=(tune["chosen_h_u"] if tune else None), symmetric=symmetric)
    if tune:
        c = tune["chosen"]
        rep["tuned_in"] = "image space: maximises mean PSNR - 40 x max switch pop over true renders of off-grid views"
        rep["strategy"] = ("two bracketing pitch buckets, each warped to the true pitch/yaw by one affine matrix (plane z=h), blended by pitch" if tune.get("strategy") == "blend"
                           else "nearest bucket + exact affine re-projection of the plane z=h")
        rep["strategy_kind"] = tune.get("strategy", "single")
        rep["note_geometry"] = "the geometric error figures (base_*, worst_*, scenarios) describe the single-bucket fallback; blending improves on them (see image)"
        rep["image"] = {"psnr_mean_db": round(c["psnr_mean"], 2), "psnr_min_db": round(c["psnr_min"], 2), "switch_pop_rms_max": round(c["pop_max_rms"], 4),
                        "switch_pop_over_median": round(c["pop_ratio"], 2), "pitch_pop_rms_max": round(c.get("pitch_pop_max_rms", c["pop_max_rms"]), 4),
                        "yaw_pop_rms_max": round(c.get("yaw_pop_max_rms", c["pop_max_rms"]), 4), "views": tune.get("views"), "strategy": tune.get("strategy", "single")}
    else:
        rep["tuned_in"] = "geometry only (vertex minimax) - no true renders were available; prefer tune-h"
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True)
    ap.add_argument("--asset", required=True)
    ap.add_argument("--variant", default="")
    ap.add_argument("--glb", default="", help="the asset's glTF binary: enables the measured error bounds in the manifest")
    ap.add_argument("--out", required=True)
    ap.add_argument("--webp", default="lossy:92")
    ap.add_argument("--tiers", default="xxxhdpi:4,xxhdpi:3,xhdpi:2")
    ap.add_argument("--tune", default="", help="JSON written by `simulate_runtime.py tune-h`: the image-space plane height (and its measured image errors) to record")
    ap.add_argument("--only-manifest", action="store_true", help="keep the existing sheets; recompute the measured error bounds in the manifest only")
    a = ap.parse_args()

    stem = a.asset + (("_" + a.variant) if a.variant else "")
    man = json.load(open(os.path.join(a.frames, f"{stem}.manifest.json")))
    if a.only_manifest:
        mp = os.path.join(a.out, f"{stem}.sprites.json")
        cur = json.load(open(mp))
        v, _ = RE.load_glb_vertices(a.glb)
        cur["reprojection"] = reprojection_block(v, cur["unit_dp"], [(float(p), cur["yaws"]) for p in cur["pitches"]], a.tune, symmetric=cur["yaws"] == 1)
        json.dump(cur, open(mp, "w"), indent=1)
        r = cur["reprojection"]
        print(f"refreshed {stem}: plane h={r['plane_h_u']:.2f} u | silhouette (base) worst {r['base_worst_err_dp']:.2f} dp, p95 {r['base_p95_err_dp']:.2f} dp | all vertices worst {r['worst_err_dp']:.2f} dp | image PSNR {r.get('image', {}).get('psnr_mean_db', float('nan')):.1f} dB")
        return
    pitches, yaws, master = sorted(man["pitches"]), man["yaws"], man["render_px"]
    cols, rows = grid_for(yaws)
    frame_dp = man["frame_dp"]
    kind = man.get("kind", "solid")
    tiers = [(t.split(":")[0], int(t.split(":")[1])) for t in a.tiers.split(",")]
    os.makedirs(a.out, exist_ok=True)

    comp = {}
    for p in pitches:
        for k in range(yaws):
            base = os.path.join(a.frames, f"{stem}_{S.pname(p)}_y{k:02d}")
            comp[(S.pkey(p), k)] = S.compose_frame(base + ".png", base + ".sh.png")

    out_tiers, total = {}, {}
    for tname, scale in tiers:
        px = int(round(frame_dp * scale))
        sheets, tsum = {}, 0
        for p in pitches:
            sheet = Image.new("RGBA", (cols * px, rows * px), (0, 0, 0, 0))
            for k in range(yaws):
                sheet.paste(S.resize_rgba(comp[(S.pkey(p), k)], px), ((k % cols) * px, (k // cols) * px))
            fn = f"{stem}_{S.pname(p)}@{tname}.webp"
            path = os.path.join(a.out, fn)
            save_webp(sheet, path, a.webp)
            data = open(path, "rb").read()
            tsum += len(data)
            sheets[S.pkey(p)] = {"file": fn, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "cols": cols, "rows": rows, "size": [cols * px, rows * px]}
        out_tiers[tname] = {"scale": scale, "frame_px": px, "sheets": sheets, "total_bytes": tsum}
        total[tname] = tsum

    reproj = None
    if a.glb:
        v, _ = RE.load_glb_vertices(a.glb)
        grid = [(float(p), yaws) for p in pitches]
        reproj = reprojection_block(v, man["unit_dp"], grid, a.tune, symmetric=yaws == 1)

    manifest = {
        "schema": "aize-sprites/2",
        "asset": a.asset, "variant": a.variant or None,
        "frame_dp": frame_dp, "unit_dp": man["unit_dp"], "anchor": man.get("anchor", [0.5, 0.5]),
        "pitches": pitches, "yaws": yaws, "yaw_step_deg": man["yaw_step_deg"],
        "frame_index": "k = row * cols + col; yaw = k * yaw_step_deg, clockwise from screen-up",
        "pitch_definition": "degrees from nadir (0 = looking straight down, 60 = towards the horizon) - the same as MapLibre `pitch`",
        "kind": kind,
        "selection": ({
            "bucket": "single frame (viewport-aligned billboard: identical at every pitch and map bearing)",
            "warp": "none - draw unrotated and unscaled, anchor at `anchor`",
            "ground": "the stalk's foot contact shadow is NOT baked as a ground ellipse: draw a separate map-aligned circle (circle-pitch-alignment: map) so it squashes with the pitch",
            "scale": "constant on screen: draw the frame at frame_dp, independent of zoom and pitch",
        } if kind == "billboard" else {
            "bucket": "the two pitch buckets that bracket the camera pitch (t = fractional position, 0 on a bucket) and the nearest yaw bucket; residual yaw = requested - bucket yaw",
            "warp": "per bucket, ONE affine matrix: unsquash by 1/cos(bucket pitch) about the plane z = reprojection.plane_h_u, rotate by the yaw residual about the anchor, squash to cos(TRUE pitch)",
            "blend": "draw the lower bucket at alpha (1 - t) and the upper at alpha t with BlendMode.Plus on premultiplied pixels (exact linear blend); on a bucket pitch (t ~ 0 or 1) draw ONE cell",
            "switch": "pitch is continuous (blend) and needs no dissolve; on a heading-bucket change an optional ~100 ms dissolve old -> new softens the flip (measured: mean frame change at flip frames about 30 % lower)",
            "single_bucket_fallback": "nearest bucket + the same warp, no blend: cheaper (always one draw), about 3 dB worse on off-grid pitches (reprojection.image_single_bucket)",
            "scale": "constant on screen: draw the frame at frame_dp, independent of zoom and pitch",
            "steady_state": "make the camera presets (overview, browse, drive, navigate) coincide with bucket pitches: then the only error left is the yaw residual",
        }),
        "reprojection": reproj,
        "shadow": {"baked": True, "light": "upper-left, fixed to the screen (soft drop shadow of the object itself)", "tint": S.SHADOW["tint_token"], "opacity": S.SHADOW["opacity"]},
        "webp": a.webp,
        "tiers": out_tiers,
        "source": {"renderer": man["blender"] + " Cycles (CPU, OIDN)", "samples": man["samples"], "render_px": master,
                   "generator": "assets3d/blender/render_sprites.py", "rig": man.get("rig"), "frame_half_extent_u": man["frame_half_extent_u"],
                   "object_radius_u": man["object_radius_u"], "object_height_u": man["object_height_u"]},
        "licence": "original procedural model built in Blender from primitives; no third-party geometry, textures or fonts",
    }
    with open(os.path.join(a.out, f"{stem}.sprites.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    extra = ""
    if reproj:
        extra = f" | plane h={reproj['plane_h_u']:.2f} u, silhouette worst {reproj['base_worst_err_dp']:.2f} dp, all-vertex worst {reproj['worst_err_dp']:.2f} dp"
    print(f"packed {stem}: {len(pitches)} pitches x {yaws} yaws, grid {cols}x{rows}; " + ", ".join(f"{t}: {total[t] / 1024:.0f} KiB" for t in total) + extra)


if __name__ == "__main__":
    main()
