#!/usr/bin/env python3
"""Merge a second render run (extra pitch buckets, same asset/rig/seed) into the main frames directory.

  python3 assets3d/tools/merge_frames.py --src build/frames/arrow_extra --dst build/frames/arrow --asset arrow [--variant v]

Copies every <stem>_p*_y*.png / .sh.png, unions the manifests' pitch lists and refuses to merge runs that differ in anything
that would make frames inconsistent (yaw count, render size, frame extent, samples, Blender version, rig).
"""
import argparse
import json
import os
import shutil

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True)
ap.add_argument("--dst", required=True)
ap.add_argument("--asset", required=True)
ap.add_argument("--variant", default="")
a = ap.parse_args()
stem = a.asset + (("_" + a.variant) if a.variant else "")
ms = json.load(open(os.path.join(a.src, f"{stem}.manifest.json")))
md = json.load(open(os.path.join(a.dst, f"{stem}.manifest.json")))
for key in ("yaws", "render_px", "frame_half_extent_u", "object_radius_u", "object_height_u", "samples", "shadow_samples", "blender", "rig", "frame_dp"):
    assert ms.get(key) == md.get(key), f"cannot merge: {key} differs ({ms.get(key)!r} vs {md.get(key)!r})"
n = 0
for f in sorted(os.listdir(a.src)):
    if f.startswith(stem + "_p") and f.endswith(".png"):
        shutil.copy2(os.path.join(a.src, f), os.path.join(a.dst, f))
        n += 1
md["pitches"] = sorted(set(md["pitches"]) | set(ms["pitches"]))
json.dump(md, open(os.path.join(a.dst, f"{stem}.manifest.json"), "w"), indent=1)
print(f"merged {n} files; pitches now {md['pitches']}")
