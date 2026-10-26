#!/usr/bin/env python3
"""Error and bucket-switch 'pop' of the single-bucket + plane-warp strategy as the camera pitch sweeps 0 -> 60 (geometry only).

  python3 assets3d/tools/pitch_sweep.py --glb assets3d/dist/arrow/arrow.glb --sprites assets3d/dist/arrow/arrow.sprites.json \
          --spacings 15,10,7.5,5 --yaws 24 --h 0.5

For every pitch spacing: the worst vertex error (dp) over the sweep at the worst yaw residual, and the largest jump (dp) of any
vertex between two consecutive 0.25-degree steps (= what a bucket switch shows on screen if the switch is not dissolved).
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reproject_error as RE  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--sprites", required=True)
    ap.add_argument("--spacings", default="15,10,7.5,5")
    ap.add_argument("--yaws", type=int, default=24)
    ap.add_argument("--h", type=float, default=-1.0, help="plane height (u); default = the manifest's tuned value")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    m = json.load(open(a.sprites))
    v, _ = RE.load_glb_vertices(a.glb)
    vs = RE.subsample(v, 600)
    vb = RE.subsample(v[v[:, 2] <= 0.2 * float(v[:, 2].max())], 400)          # outline level: lowest 20 % of the mesh
    udp = m["unit_dp"]
    h = a.h if a.h >= 0 else m["reprojection"]["plane_h_u"]
    strat = f"plane:{h:.2f}"
    step = 360.0 / a.yaws
    out = {}
    print(f"{a.yaws} yaws (step {step:g} deg), strategy {strat}, 1 u = {udp:.1f} dp; sweep pitch 0..60 at 0.25 deg")
    print(f"{'pitch spacing':>14} {'buckets':>8} {'frames':>7} | {'outline worst':>14} {'all-vertex worst':>17} | {'outline pop':>12} {'all-vertex pop':>15}")
    phis = np.arange(0.0, 60.0 + 1e-9, 0.25)
    for sp in [float(x) for x in a.spacings.split(",")]:
        grid = RE.uniform_grid(step, sp)
        stats = {}
        for label, verts in (("base", vb), ("all", vs)):
            worst, pops = 0.0, []
            for psi in (0.0, step / 2.0):
                prevP = prevT = None
                for phi in phis:
                    P = RE.predicted(verts, float(phi), psi, grid, strat)
                    T = RE.project(verts, float(phi), psi)
                    worst = max(worst, float((np.linalg.norm(P - T, axis=1) * udp).max()))
                    if prevP is not None:
                        pops.append(float((np.linalg.norm((P - prevP) - (T - prevT), axis=1) * udp).max()))
                    prevP, prevT = P, T
            stats[label] = {"worst_dp": worst, "pop_dp": max(pops)}
        n = sum(x[1] for x in grid)
        out[f"{sp:g}"] = {"buckets": len(grid), "frames": n, "outline": stats["base"], "all_vertices": stats["all"]}
        print(f"{sp:>14g} {len(grid):>8} {n:>7} | {stats['base']['worst_dp']:>14.2f} {stats['all']['worst_dp']:>17.2f} | {stats['base']['pop_dp']:>12.2f} {stats['all']['pop_dp']:>15.2f}")
    if a.json:
        json.dump({"yaws": a.yaws, "plane_h_u": h, "unit_dp": udp, "by_spacing": out}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
