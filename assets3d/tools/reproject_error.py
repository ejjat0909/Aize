#!/usr/bin/env python3
"""How wrong is a pre-rendered sprite grid, in dp?  Geometry-only, resolution-independent (numpy).

Loads the asset's exported glTF binary (this also validates the deliverable), then for every test view (pitch phi, yaw psi)
compares the TRUE screen position of every vertex with the position predicted by the runtime strategy that starts from the
nearest pre-rendered bucket:

  snap      : use the nearest bucket as is (no correction)
  rotate    : rotate the bucket image in the screen plane by the yaw residual
  affine    : rotate by the residual in the GROUND plane and squash to the true pitch (exact for z = 0, approximate above it)

Screen model (matches Blender's camera in render_sprites.py, long lens ~ orthographic):  sx = x,  sy = y*cos(phi) + z*sin(phi),
object yawed clockwise by psi about +Z.  1 world unit = unit_dp dp (from the manifest).

  python3 assets3d/tools/reproject_error.py --glb assets3d/dist/arrow/arrow.glb --sprites assets3d/dist/arrow/arrow.sprites.json
  python3 assets3d/tools/reproject_error.py --glb ... --sprites ... --grid "15x15,10x15,7.5x15,15x10,10x10,7.5x7.5"
"""
import argparse
import json
import math
import struct

import numpy as np

COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load_glb_vertices(path):
    """All mesh vertices of a .glb in the ORIGINAL Blender convention (Z up, +Y forward): glTF is Y-up, so (x, y, z) = (gx, -gz, gy)."""
    data = open(path, "rb").read()
    magic, ver, length = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF" and ver == 2 and length == len(data), "not a valid GLB 2.0 file"
    off, js, binchunk = 12, None, None
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        body = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(body)
        elif ctype == 0x004E4942:
            binchunk = body
        off += 8 + clen + (-clen % 4)
    assert js is not None and binchunk is not None

    def accessor(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = COMP[a["componentType"]]
        n = NCOMP[a["type"]]
        stride = bv.get("byteStride", 0) or dt().itemsize * n
        base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        if stride == dt().itemsize * n:
            return np.frombuffer(binchunk, dtype=dt, count=a["count"] * n, offset=base).reshape(a["count"], n).astype(np.float64)
        rows = [np.frombuffer(binchunk, dtype=dt, count=n, offset=base + r * stride) for r in range(a["count"])]
        return np.array(rows, dtype=np.float64)

    def node_matrix(nd):
        if "matrix" in nd:
            return np.array(nd["matrix"], dtype=np.float64).reshape(4, 4).T
        t = np.array(nd.get("translation", [0, 0, 0]), dtype=np.float64)
        q = nd.get("rotation", [0, 0, 0, 1])
        s = np.array(nd.get("scale", [1, 1, 1]), dtype=np.float64)
        x, y, z, w = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        M = np.eye(4)
        M[:3, :3] = R * s
        M[:3, 3] = t
        return M

    verts = []

    def walk(ni, parent):
        nd = js["nodes"][ni]
        M = parent @ node_matrix(nd)
        if "mesh" in nd:
            for prim in js["meshes"][nd["mesh"]]["primitives"]:
                P = accessor(prim["attributes"]["POSITION"])
                verts.append((np.c_[P, np.ones(len(P))] @ M.T)[:, :3])
        for c in nd.get("children", []):
            walk(c, M)

    for r in js["scenes"][js.get("scene", 0)]["nodes"]:
        walk(r, np.eye(4))
    g = np.vstack(verts)
    out = np.c_[g[:, 0], -g[:, 2], g[:, 1]]
    return out[out[:, 2] >= -1e-4], len(js["meshes"])        # below-ground vertices (buried geometry) are invisible: never measure them


def project(v, phi, psi):
    """world vertices (N,3) -> screen (N,2) in world units; object yawed clockwise by psi (deg), camera pitch phi (deg)."""
    p, s = math.radians(phi), math.radians(psi)
    c, si = math.cos(s), math.sin(s)
    x = v[:, 0] * c + v[:, 1] * si       # clockwise rotation by psi about +Z
    y = -v[:, 0] * si + v[:, 1] * c
    return np.c_[x, y * math.cos(p) + v[:, 2] * math.sin(p)]


def wrap180(a):
    return ((a + 180.0) % 360.0) - 180.0


def predicted(v, phi, psi, grid, strat):
    """screen positions of the strategy's approximation of view (phi, psi).
    grid: sorted list of (bucket_pitch, yaw_count).  The bucket is the nearest pitch (ties -> the higher one); yaw is
    quantised with that bucket's own step."""
    pitches = [g[0] for g in grid]
    if len(pitches) == 1:
        b = 0
    else:
        i = max(0, min(int(np.searchsorted(pitches, phi, side="right")) - 1, len(pitches) - 2))
        b = i if (phi - pitches[i]) < (pitches[i + 1] - phi) else i + 1
    phib, nyaw = grid[b]
    ystep = 360.0 / nyaw
    k = round(psi / ystep)
    psib = k * ystep
    rho = wrap180(psi - psib)
    sb = project(v, phib, psib)
    if strat == "snap":
        return sb
    r = math.radians(rho)
    cr, sr = math.cos(r), math.sin(r)
    if strat == "rotate":
        return np.c_[sb[:, 0] * cr + sb[:, 1] * sr, -sb[:, 0] * sr + sb[:, 1] * cr]
    if strat == "affine" or strat.startswith("plane"):
        h = 0.0 if strat == "affine" else float(strat.split(":")[1])
        cb, c = math.cos(math.radians(phib)), math.cos(math.radians(phi))
        sinb, sin_ = math.sin(math.radians(phib)), math.sin(math.radians(phi))
        gy = (sb[:, 1] - h * sinb) / max(cb, 1e-6)            # where the point would be on the plane z = h
        X = sb[:, 0] * cr + gy * sr                              # rotate about the vertical axis through the anchor
        Y = -sb[:, 0] * sr + gy * cr
        return np.c_[X, Y * c + h * sin_]                        # re-project to the true pitch
    raise ValueError(strat)


SCENARIOS = {
    "nav":        dict(phis=[45.0, 50.0, 55.0, 60.0], psis=np.arange(-15.0, 15.01, 1.0), note="heading-up guidance: pitch near its preset, relative yaw within +-15 deg"),
    "overview":   dict(phis=[0.0], psis=np.arange(0.0, 360.0, 3.0), note="top-down, north-up: any heading"),
    "transition": dict(phis=list(np.arange(0.0, 60.01, 2.0)), psis=np.arange(-15.0, 15.01, 3.0), note="camera easing between presets (~0.5 s)"),
    "worst":      dict(phis=list(np.arange(0.0, 60.01, 0.5)), psis=np.arange(0.0, 360.0, 2.5), note="every pitch (0.5 deg steps) x every heading (2.5 deg steps): uniform, pessimistic"),
}


def scenario_error(vs, unit_dp, grid, strat, sc, max_verts=None):
    if max_verts and len(vs) > max_verts:
        vs = vs[:: max(1, len(vs) // max_verts)]
    worst, p95s = 0.0, []
    for phi in sc["phis"]:
        for psi in sc["psis"]:
            q = psi % 360.0
            d = np.linalg.norm(predicted(vs, phi, q, grid, strat) - project(vs, phi, q), axis=1) * unit_dp
            worst = max(worst, float(d.max()))
            p95s.append(float(np.percentile(d, 95)))
    return worst, float(np.percentile(p95s, 95))


def uniform_grid(ystep, pstep, top=60.0):
    return [(p, int(round(360.0 / ystep))) for p in grid_pitches(pstep, top)]


def parse_grid(text):
    """'0:1,15:8,30:16' -> [(0.0, 1), (15.0, 8), (30.0, 16)]"""
    return sorted((float(a), int(b)) for a, b in (x.split(":") for x in text.split(",")))


def grid_str(grid):
    return ",".join(f"{p:g}:{n}" for p, n in grid)


YAW_OPTIONS = [1, 4, 6, 8, 10, 12, 16, 20, 24, 32, 36, 48, 64, 72]


def design_grid(vs, unit_dp, pitches, eps, strat, step_phi=2.0, step_psi=3.0, top=60.0):
    """For a given set of pitch buckets, give each the fewest yaws such that EVERY view it serves (all headings, the pitches for
    which it is the nearest bucket) is reconstructed within eps dp.  Returns (grid, worst_error_dp)."""
    pitches = sorted(pitches)
    grid = [(p, YAW_OPTIONS[-1]) for p in pitches]
    out = []
    for b, p in enumerate(pitches):
        lo = (pitches[b - 1] + p) / 2.0 if b > 0 else 0.0
        hi = (p + pitches[b + 1]) / 2.0 if b + 1 < len(pitches) else top
        phis = list(np.arange(lo, hi + 1e-6, step_phi))
        sc = dict(phis=phis, psis=np.arange(0.0, 360.0, step_psi))
        chosen = YAW_OPTIONS[-1]
        for n in YAW_OPTIONS:
            trial = [(q, (n if i == b else m)) for i, (q, m) in enumerate(grid)]
            w, _ = scenario_error(vs, unit_dp, trial, strat, sc)
            if w <= eps:
                chosen = n
                break
        grid[b] = (p, chosen)
    worst, _ = scenario_error(vs, unit_dp, grid, strat, dict(phis=list(np.arange(0.0, top + 1e-6, 2.0)), psis=np.arange(0.0, 360.0, 3.0)))
    return grid, worst


def subsample(v, n=1000):
    rng = np.random.default_rng(1)
    return v[rng.choice(len(v), size=min(len(v), n), replace=False)]


def grid_pitches(step, top=60.0):
    p = list(np.arange(0.0, top + 1e-6, step))
    if p[-1] < top - 1e-6:
        p.append(top)
    return p


def switch_pop(vs, unit_dp, grid, strat, step=0.25, top=60.0, symmetric=False):
    """Largest on-screen jump (dp) of any vertex, beyond the true motion, between two consecutive pitch steps of a sweep 0..top at the two
    extreme yaw residuals: what a bucket switch shows if it is not dissolved."""
    ystep = 360.0 / min(n for _, n in grid)
    pops = []
    for psi in ((0.0,) if symmetric else (0.0, ystep / 2.0)):
        prevP = prevT = None
        for phi in np.arange(0.0, top + 1e-9, step):
            P = predicted(vs, float(phi), psi, grid, strat)
            T = project(vs, float(phi), psi)
            if prevP is not None:
                pops.append(float((np.linalg.norm((P - prevP) - (T - prevT), axis=1) * unit_dp).max()))
            prevP, prevT = P, T
    return max(pops)


def grid_report(v, unit_dp, grid, h=None, candidates=None, base_frac=0.2, symmetric=False):
    """Everything the manifest records about a sprite grid's GEOMETRY: errors (dp) at the plane height `h` (given, or the geometric
    minimax if None - prefer an image-space `h`, see simulate_runtime tune-h).  `base_*` are the lowest `base_frac` of the mesh height
    (rim / footprint / wheels: the high-contrast silhouette); `worst_*` are all vertices, dominated by raised parts like the ridge."""
    vs = subsample(v)
    scen = SCENARIOS
    if symmetric:      # rotationally symmetric asset (one yaw): heading cannot be wrong, evaluate pitch only
        scen = {k: dict(sc, psis=np.array([0.0])) for k, sc in SCENARIOS.items()}
    cand = candidates or [float(x) for x in np.arange(0.0, 1.21, 0.05)]
    if h is None:
        h = min(cand, key=lambda x: scenario_error(vs, unit_dp, grid, f"plane:{x:.2f}", scen["transition"])[0])
    strat = f"plane:{h:.2f}"
    zmax = float(v[:, 2].max())
    vb = subsample(v[v[:, 2] <= base_frac * zmax])
    rep = {"plane_h_u": round(float(h), 3), "strategy": "nearest bucket + exact affine re-projection of the plane z=h (rotate by the yaw residual about the vertical axis, re-pitch to the true camera)",
           "scenarios": {}}
    for name, sc in scen.items():
        w, p95 = scenario_error(vs, unit_dp, grid, strat, sc, max_verts=400 if name == "worst" else None)
        wb, pb = scenario_error(vb, unit_dp, grid, strat, sc, max_verts=400 if name == "worst" else None)
        rep["scenarios"][name] = {"max_dp": round(w, 3), "p95_dp": round(p95, 3), "base_max_dp": round(wb, 3), "base_p95_dp": round(pb, 3), "note": sc["note"]}
    wr = rep["scenarios"]["worst"]
    rep["worst_err_dp"], rep["p95_err_dp"] = wr["max_dp"], wr["p95_dp"]
    rep["base_worst_err_dp"], rep["base_p95_err_dp"] = wr["base_max_dp"], wr["base_p95_dp"]
    rep["base_height_frac"] = base_frac
    rep["switch_pop_dp"] = round(switch_pop(vs, unit_dp, grid, strat, symmetric=symmetric), 3)
    rep["symmetric"] = bool(symmetric)
    rep["unit_dp"] = round(float(unit_dp), 3)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb", required=True)
    ap.add_argument("--sprites", required=True, help="the asset's .sprites.json (for unit_dp and the shipped grid)")
    ap.add_argument("--shipped-grid", default="", help="grid under test as 'pitch:yaws,...' (default: read from the .sprites.json)")
    ap.add_argument("--compare", default="", help="more grids to tabulate, ';'-separated, each 'pitch:yaws,...'")
    ap.add_argument("--design", default="", help="comma list of eps (dp): search the cheapest non-uniform grid for each")
    ap.add_argument("--h", type=float, default=-1.0, help="reprojection plane height (u); default = optimise")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    m = json.load(open(a.sprites))
    v, nmesh = load_glb_vertices(a.glb)
    unit_dp = m["unit_dp"]
    R = float(np.hypot(v[:, 0], v[:, 1]).max())
    H = float(v[:, 2].max())
    print(f"GLB ok: {nmesh} meshes, {len(v)} vertices, R={R:.3f} u, H={H:.3f} u (manifest {m['source']['object_radius_u']:.3f}/{m['source']['object_height_u']:.3f}); 1 u = {unit_dp:.2f} dp")
    shipped = parse_grid(a.shipped_grid) if a.shipped_grid else (
        [(float(p), m["yaws"]) for p in m["pitches"]] if "yaws_by_pitch" not in m else [(float(p), n) for p, n in sorted((float(k), v) for k, v in m["yaws_by_pitch"].items())])
    vs = subsample(v)
    cand = [float(h) for h in np.arange(0.0, 0.81, 0.05)]
    hz = a.h if a.h >= 0 else min(cand, key=lambda h: scenario_error(vs, unit_dp, shipped, f"plane:{h:.2f}", SCENARIOS["transition"])[0])
    strat = f"plane:{hz:.2f}"
    print(f"reprojection plane height h = {hz:.2f} u ({'given' if a.h >= 0 else 'optimised for the transition scenario on the shipped grid'})")
    named = {"shipped " + grid_str(shipped): shipped}
    for g in a.compare.split(";") if a.compare else []:
        named["grid " + g] = parse_grid(g)
    res = {"h": hz, "scenarios": {}, "design": {}}
    print(f"\nscenario errors for strategy '{strat}' (dp; max / p95 of per-view p95)")
    hdr = f"{'grid (pitch:yaws)':<46} {'frames':>6}  " + "  ".join(f"{k:>14}" for k in SCENARIOS)
    print(hdr)
    for name, g in named.items():
        row = {k: scenario_error(vs, unit_dp, g, strat, sc) for k, sc in SCENARIOS.items()}
        res["scenarios"][name] = {"frames": sum(n for _, n in g), **{k: {"max_dp": r[0], "p95_dp": r[1]} for k, r in row.items()}}
        print(f"{name[:46]:<46} {sum(n for _, n in g):>6}  " + "  ".join(f"{row[k][0]:6.2f}/{row[k][1]:<6.2f}" for k in SCENARIOS))
    if a.design:
        print(f"\ngrid design (fewest yaws per pitch bucket so that every served view is within eps), strategy '{strat}':")
        psets = {"0,15,30,45,60": [0, 15, 30, 45, 60], "0,20,40,50,60": [0, 20, 40, 50, 60], "0,30,45,60": [0, 30, 45, 60], "0,10,20,30,40,50,60": [0, 10, 20, 30, 40, 50, 60],
                 "0,25,40,50,60": [0, 25, 40, 50, 60], "0,20,35,45,53,60": [0, 20, 35, 45, 53, 60]}
        for eps in [float(x) for x in a.design.split(",")]:
            best = None
            for pname, ps in psets.items():
                g, w = design_grid(vs, unit_dp, ps, eps, strat)
                n = sum(x[1] for x in g)
                print(f"  eps {eps:>4g} dp  pitches {pname:<22} -> {grid_str(g):<46} {n:>4} frames, worst {w:5.2f} dp")
                if w <= eps + 1e-9 and (best is None or n < best[1]):
                    best = (g, n, w, pname)
            if best:
                res["design"][f"{eps:g}"] = {"grid": grid_str(best[0]), "frames": best[1], "worst_dp": best[2], "pitches": best[3]}
                print(f"  => eps {eps:g}: cheapest = {best[3]} : {grid_str(best[0])}  ({best[1]} frames)")
    if a.json:
        json.dump({"unit_dp": unit_dp, "R_u": R, "H_u": H, "results": res, "shipped": grid_str(shipped)}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
