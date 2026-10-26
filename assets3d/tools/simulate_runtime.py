#!/usr/bin/env python3
"""Offline reference implementation + validation of the RUNTIME sprite selection (Pillow + numpy; no Android needed).

  python3 assets3d/tools/simulate_runtime.py validate --frames build/frames/arrow --truth build/frames/arrow_truth2 --sprites dist/arrow/arrow.sprites.json
  python3 assets3d/tools/simulate_runtime.py video    --sprites dist/arrow/arrow.sprites.json --theme light --out assets3d/preview

The algorithm below is the specification the Android overlay must implement (assets3d/README.md#runtime):
  1. nearest pitch bucket, nearest yaw bucket, residual = requested yaw - bucket yaw
  2. ONE affine matrix: unsquash by 1/cos(bucket pitch) about the plane z = h, rotate by the residual, squash to cos(true pitch)
  3. when the bucket changes, dissolve old -> new over ~100 ms

`validate` compares the reconstruction of views that are NOT on the grid against true Blender renders of those exact views.
`video` drives the pointer along a route on a perspective-correct purple map (pitch 60 -> 0 -> 45, heading-up and north-up).
"""
import argparse
import json
import math
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import sprite_lib as S  # noqa: E402

FOV = 0.6435011087932844   # MapLibre's default vertical field of view (radians)


def wrap180(a):
    return ((a + 180.0) % 360.0) - 180.0


# ------------------------------------------------------------------------------------------------ the runtime algorithm
def plane_affine(im, phib, phi, rho, h_px):
    """Re-project a bucket sprite (pitch `phib`) to pitch `phi` while rotating it by `rho` degrees clockwise about the anchor (frame
    centre).  Exact for everything on the horizontal plane z = h (h_px = h in pixels of THIS image); the rest is approximated.

    Forward map (y up):  gy = (sy - h sin(phib)) / cos(phib);  X = sx cos(rho) + gy sin(rho);  Y = -sx sin(rho) + gy cos(rho);
                         out = (X, Y cos(phi) + h sin(phi)).      PIL wants the inverse (output pixel -> source pixel).
    """
    w, h_ = im.size
    cx, cy = w / 2.0, h_ / 2.0
    cb, c = math.cos(math.radians(phib)), math.cos(math.radians(phi))
    sb = math.sin(math.radians(phib))
    r = math.radians(rho)
    cr, sr = math.cos(r), math.sin(r)
    tn = math.tan(math.radians(phi))
    a, b = cr, sr / c
    d, e = -cb * sr, cb * cr / c
    ca = h_px * tn * sr
    fa = h_px * (cb * tn * cr - sb)
    return im.transform((w, h_), Image.AFFINE, (a, b, cx - a * cx - b * cy + ca, d, e, cy - d * cx - e * cy + fa), Image.BICUBIC)


def forward_matrix(phib, phi, rho, h_px):
    """The SAME warp as `plane_affine`, as the FORWARD 2-D affine an Android Canvas needs (sprite pixel -> screen pixel).

    Coordinates are relative to the sprite frame centre (the anchor), x right, y DOWN, in pixels of the drawn sprite; h_px = h * unit_dp * density.
    Returns (A, B, C, D, E, F) with  x' = A x + B y + C,  y' = D x + E y + F.  Android: Matrix.setValues([A, B, C, D, E, F, 0, 0, 1]).
    """
    cb, c = math.cos(math.radians(phib)), math.cos(math.radians(phi))
    sb, sn = math.sin(math.radians(phib)), math.sin(math.radians(phi))
    tb = sb / cb
    r = math.radians(rho)
    cr, sr = math.cos(r), math.sin(r)
    return (cr, -sr / cb, -h_px * tb * sr,
            sr * c, cr * c / cb, h_px * (tb * cr * c - sn))


class SpriteSet:
    """Reads the packed atlas exactly as the app would (manifest + per-pitch sheets) and implements the selection."""

    def __init__(self, manifest_path, tier="xxhdpi"):
        self.m = json.load(open(manifest_path))
        self.dir = os.path.dirname(manifest_path)
        self.t = self.m["tiers"][tier]
        self.px = self.t["frame_px"]
        self.pitches = [float(p) for p in self.m["pitches"]]
        self.yaws, self.step = self.m["yaws"], self.m["yaw_step_deg"]
        self.h_px = self.m["reprojection"]["plane_h_u"] * self.m["unit_dp"] * self.t["scale"] if self.m.get("reprojection") else 0.0
        self._sheet, self._frame = {}, {}

    def frame(self, pitch, k):
        key = (S.pkey(pitch), k)
        if key not in self._frame:
            sh = self.t["sheets"][key[0]]
            if key[0] not in self._sheet:
                self._sheet[key[0]] = Image.open(os.path.join(self.dir, sh["file"])).convert("RGBA")
            c = sh["cols"]
            x, y = (k % c) * self.px, (k // c) * self.px
            self._frame[key] = self._sheet[key[0]].crop((x, y, x + self.px, y + self.px))
        return self._frame[key]

    def pair(self, phi):
        """The two pitch buckets that bracket `phi` and the fraction t of the way from the lower to the upper (t = 0 on a bucket)."""
        lo = max([p for p in self.pitches if p <= phi + 1e-9] or [self.pitches[0]])
        hi = min([p for p in self.pitches if p >= phi - 1e-9] or [self.pitches[-1]])
        return lo, hi, (0.0 if hi == lo else (phi - lo) / (hi - lo))

    def select(self, phi, rel_yaw):
        """-> (lower pitch bucket, upper pitch bucket, t, yaw index k, residual degrees)"""
        lo, hi, t = self.pair(phi)
        k = int(round(rel_yaw / self.step)) % self.yaws
        return lo, hi, t, k, wrap180(rel_yaw - k * self.step)

    def draw(self, phi, rel_yaw, k=None, plane_h=None):
        """The sprite for the requested view: each of the two bracketing pitch buckets is warped to the TRUE pitch and residual yaw by one
        affine matrix, then blended linearly by t (premultiplied).  On a bucket pitch (t ~ 0 or 1) that is a single draw.
        `k` forces a yaw bucket (used while dissolving a heading-bucket change)."""
        lo, hi, t, k0, _ = self.select(phi, rel_yaw)
        k = k0 if k is None else k
        res = wrap180(rel_yaw - k * self.step)
        hp = self.h_px if plane_h is None else plane_h
        phi = min(max(phi, 0.0), 89.0)
        A = plane_affine(self.frame(lo, k), lo, phi, res, hp)
        if hi == lo or t < 1e-3:
            return A
        B = plane_affine(self.frame(hi, k), hi, phi, res, hp)
        return B if t > 1 - 1e-3 else blend_premult(A, B, t)


# ------------------------------------------------------------------------------------------------ validation
def psnr_alpha(a, b):
    A = np.asarray(S.premultiply(a), np.float32) / 255.0
    B = np.asarray(S.premultiply(b), np.float32) / 255.0
    mse = float(np.mean((A - B) ** 2))
    return 99.0 if mse == 0 else 10 * math.log10(1 / mse)


def blend_premult(A, B, t):
    """Exact linear blend (1-t) A + t B in premultiplied space (Android: draw A at alpha 1-t, B at alpha t with BlendMode.Plus)."""
    a = np.asarray(S.premultiply(A), np.float32)
    b = np.asarray(S.premultiply(B), np.float32)
    m = (1 - t) * a + t * b
    al = m[..., 3:4] / 255.0
    rgb = np.where(al > 1e-4, m[..., :3] / np.maximum(al, 1e-4), 0.0)
    return Image.fromarray(np.clip(np.concatenate([rgb, m[..., 3:4]], axis=-1), 0, 255).astype(np.uint8), "RGBA")


class Recon:
    """Reconstruction of arbitrary views from master-size frames (the same maths as the runtime, at render resolution)."""

    def __init__(self, frames_dir, asset, subset=None):
        self.man = json.load(open(os.path.join(frames_dir, f"{asset}.manifest.json")))
        allp = sorted(float(p) for p in self.man["pitches"])
        self.pitches = [p for p in allp if (subset is None or any(abs(p - q) < 1e-6 for q in subset))]
        self.yaws, self.step, self.px = self.man["yaws"], self.man["yaw_step_deg"], self.man["render_px"]
        self.ppu = self.px / (2.0 * self.man["frame_half_extent_u"])             # master pixels per world unit
        self.fr = {(S.pkey(p), k): S.compose_frame(os.path.join(frames_dir, f"{asset}_{S.pname(p)}_y{k:02d}.png"), os.path.join(frames_dir, f"{asset}_{S.pname(p)}_y{k:02d}.sh.png"))
                   for p in self.pitches for k in range(self.yaws)}

    def yaw_bucket(self, psi):
        k = int(round(psi / self.step)) % self.yaws
        return k, wrap180(psi - k * self.step)

    def pair(self, phi):
        lo = max([p for p in self.pitches if p <= phi + 1e-9] or [self.pitches[0]])
        hi = min([p for p in self.pitches if p >= phi - 1e-9] or [self.pitches[-1]])
        return lo, hi, (0.0 if hi == lo else (phi - lo) / (hi - lo))

    def single(self, phi, psi, h):
        phib = min(self.pitches, key=lambda p: (abs(p - phi), -p))
        k, res = self.yaw_bucket(psi)
        return plane_affine(self.fr[(S.pkey(phib), k)], phib, phi, res, h * self.ppu)

    def blend(self, phi, psi, h):
        lo, hi, t = self.pair(phi)
        k, res = self.yaw_bucket(psi)
        if hi == lo or t < 1e-6:
            return plane_affine(self.fr[(S.pkey(lo), k)], lo, phi, res, h * self.ppu)
        if t > 1 - 1e-6:
            return plane_affine(self.fr[(S.pkey(hi), k)], hi, phi, res, h * self.ppu)
        return blend_premult(plane_affine(self.fr[(S.pkey(lo), k)], lo, phi, res, h * self.ppu), plane_affine(self.fr[(S.pkey(hi), k)], hi, phi, res, h * self.ppu), t)


def load_truth(truth_dir, asset):
    tman = json.load(open(os.path.join(truth_dir, f"{asset}.manifest.json")))
    out = []
    for name in sorted(os.listdir(truth_dir)):
        if name.startswith(asset + "_p") and name.endswith(".png") and ".sh." not in name:
            tok = name[len(asset) + 1:name.index("_y")][1:]
            phi = float(tok.replace("d", ".")) if "d" in tok else float(tok)
            kk = int(name.split("_y")[1].split(".")[0])
            base = os.path.join(truth_dir, name[:-4])
            out.append((phi, kk * tman["yaw_step_deg"], S.compose_frame(base + ".png", base + ".sh.png")))
    return out


def subset_arg(text):
    return [float(x) for x in text.split(",")] if text else None


def run_validate(a):
    rc = Recon(a.frames, a.asset, subset_arg(a.pitches))
    sp = json.load(open(a.sprites))
    h_star = a.h if a.h >= 0 else (sp["reprojection"]["plane_h_u"] if sp.get("reprojection") else 0.1)
    truths = load_truth(a.truth, a.asset)
    modes = {
        "A. nearest bucket, as is": lambda phi, psi: rc.fr[(S.pkey(min(rc.pitches, key=lambda p: (abs(p - phi), -p))), rc.yaw_bucket(psi)[0])],
        "B. + rotate in the screen plane": lambda phi, psi: (lambda b, k_r: (rc.fr[(S.pkey(b), k_r[0])].rotate(-k_r[1], resample=Image.BICUBIC) if abs(k_r[1]) > 1e-3 else rc.fr[(S.pkey(b), k_r[0])]))(min(rc.pitches, key=lambda p: (abs(p - phi), -p)), rc.yaw_bucket(psi)),
        "C. + ground-plane warp (h = 0)": lambda phi, psi: rc.single(phi, psi, 0.0),
        "D. + plane warp at h* (one bucket)": lambda phi, psi: rc.single(phi, psi, h_star),
        "E. two buckets, each warped at h*, blended by pitch": lambda phi, psi: rc.blend(phi, psi, h_star),
    }
    rows = {m: [] for m in modes}
    for phi, psi, truth in truths:
        for m, f in modes.items():
            rows[m].append(psnr_alpha(f(phi, psi), truth))
    out = {m: {"min": min(v), "mean": sum(v) / len(v), "n": len(v)} for m, v in rows.items()}
    json.dump({"asset": a.asset, "pitch_buckets": rc.pitches, "h_star_u": h_star, "views": [(p, y) for p, y, _ in truths], "psnr_db_vs_true_render": out}, open(a.json or os.path.join(a.truth, "validation.json"), "w"), indent=1)
    print(f"{a.asset}: {len(truths)} off-grid views vs true renders; pitch buckets {rc.pitches}; h* = {h_star:g} u. Alpha-weighted PSNR:")
    for m in modes:
        print(f"  {m:<56s} min {out[m]['min']:5.1f} dB   mean {out[m]['mean']:5.1f} dB")
    if a.sheet:
        pick = [truths[i] for i in (0, len(truths) // 4, len(truths) // 2, len(truths) - 1)]
        tiles = []
        for phi, psi, truth in pick:
            rec = rc.blend(phi, psi, h_star)
            t = np.asarray(S.over((243, 241, 247), truth), np.float32)
            r = np.asarray(S.over((243, 241, 247), rec), np.float32)
            d = np.clip(np.abs(t - r).max(axis=2) * 3, 0, 255).astype(np.uint8)
            diff = Image.fromarray(np.stack([255 - d, 255 - d, 255 - d // 2], axis=2), "RGB")
            tiles.append((S.over((243, 241, 247), truth), S.over((243, 241, 247), rec), diff, f"pitch {phi:g}, yaw {psi:g}: {psnr_alpha(rec, truth):.1f} dB"))
        W = tiles[0][0].size[0]
        sheet = Image.new("RGB", (W * 3, W * len(tiles)), (255, 255, 255))
        dr = ImageDraw.Draw(sheet)
        for r_, (x, y, z, lab) in enumerate(tiles):
            for c_, im in enumerate((x, y, z)):
                sheet.paste(im, (c_ * W, r_ * W))
            dr.text((6, r_ * W + 6), lab + "   [true render | reconstruction (blend) | |difference| x3]", fill=(60, 40, 100))
        sheet = sheet.resize((sheet.width * 3 // 5, sheet.height * 3 // 5), Image.LANCZOS)
        sheet.save(a.sheet)
        print("wrote", a.sheet, sheet.size)


def run_tune_h(a):
    """Choose the re-projection plane height in IMAGE space for the chosen strategy (single bucket or blend).  For each candidate h:
    PSNR against true renders of off-grid views, and the visible 'pop' (RMS image change beyond smooth motion) of a pitch sweep 0 -> 60
    at three heading offsets AND of heading sweeps across bucket boundaries at several pitches.  The geometric minimax (reproject_error)
    over-weights the interior ridge; the eye is dominated by the high-contrast silhouette."""
    rc = Recon(a.frames, a.asset, subset_arg(a.pitches))
    truths = load_truth(a.truth, a.asset)
    view = rc.blend if a.strategy == "blend" else rc.single
    if a.hs:
        hs = [float(x) for x in a.hs.split(",")]
    else:       # fractions of the asset's own height: the optimum was 0.10 H (arrow), 0.18 H (puck), 0.55 H (cars)
        H = float(rc.man["object_height_u"])
        hs = [round(H * f, 3) for f in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)]
    out = {}
    print(f"{a.asset}  strategy={a.strategy}  pitch buckets={rc.pitches}  candidates h = {hs}")
    print(f"{'h (u)':>6} | {'PSNR vs truth: mean':>20} {'min':>6} | {'pitch pop max':>14} {'x med':>6} | {'yaw pop max':>12} {'x med':>6}")
    for h in hs:
        ps = [psnr_alpha(view(phi, psi, h), t) for phi, psi, t in truths]

        def sweep(items):
            prev, vals = None, []
            for phi, psi in items:
                cur = np.asarray(S.over((128, 128, 128), view(phi, psi, h)), np.float32) / 255.0
                if prev is not None:
                    vals.append(float(np.sqrt(np.mean((cur - prev) ** 2))))
                prev = cur
            return vals
        pp = []
        for psi in (0.0, rc.step / 2.0, rc.step / 4.0):
            pp += sweep([(float(phi), psi) for phi in np.arange(0.0, 60.0 + 1e-9, 0.5)])
        yy = []
        if rc.yaws > 1:
            for phi in (rc.pitches[0], rc.pitches[len(rc.pitches) // 2], rc.pitches[-1], 0.5 * (rc.pitches[-1] + rc.pitches[-2])):
                yy += sweep([(float(phi), float(psi)) for psi in np.arange(0.0, rc.step + 1e-9, 0.5)])
        else:
            yy = [float(np.min(pp))] * 3          # a rotationally symmetric asset has no heading bucket to flip
        pp, yy = np.array(pp), np.array(yy)
        out[f"{h:g}"] = {"psnr_mean": float(np.mean(ps)), "psnr_min": float(np.min(ps)), "pop_max_rms": float(max(pp.max(), yy.max())), "pitch_pop_max_rms": float(pp.max()),
                         "yaw_pop_max_rms": float(yy.max()), "pitch_pop_ratio": float(pp.max() / np.median(pp)), "yaw_pop_ratio": float(yy.max() / np.median(yy)),
                         "pop_ratio": float(max(pp.max() / np.median(pp), yy.max() / np.median(yy)))}
        print(f"{h:>6g} | {np.mean(ps):>20.2f} {np.min(ps):>6.1f} | {pp.max():>14.4f} {pp.max() / np.median(pp):>5.1f}x | {yy.max():>12.4f} {yy.max() / np.median(yy):>5.1f}x")
    best = max(out, key=lambda k: out[k]["psnr_mean"] - 40.0 * out[k]["pop_max_rms"])
    print(f"=> chosen h = {best} u (maximises mean PSNR - 40 x max switch pop)")
    json.dump({"asset": a.asset, "strategy": a.strategy, "pitch_buckets": rc.pitches, "candidates": out, "chosen_h_u": float(best), "chosen": out[best], "views": len(truths)}, open(a.out, "w"), indent=1)


# ------------------------------------------------------------------------------------------------ camera (MapLibre-like) + video
class Camera:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.f = (H / 2) / math.tan(FOV / 2)

    def set(self, centre, bearing, pitch, scale):
        self.c, self.b, self.p, self.s = centre, math.radians(bearing), math.radians(pitch), scale
        self.D = self.f / scale
        return self

    def project(self, E, N):
        dE, dN = E - self.c[0], N - self.c[1]
        u = dE * math.cos(self.b) - dN * math.sin(self.b)
        v = dE * math.sin(self.b) + dN * math.cos(self.b)
        z = self.D + v * math.sin(self.p)
        k = self.f / z
        return self.W / 2 + u * k, self.H / 2 - v * math.cos(self.p) * k, self.D / z

    def homography(self, T):
        t = math.tan(self.p)
        corners = [(0, 0), (self.W, 0), (self.W, self.H), (0, self.H)]
        src = []
        for xo, yo in corners:
            X, Y = (xo - self.W / 2) / self.f, (self.H / 2 - yo) / self.f
            z = self.D / (1 - Y * t)
            u, v = X * z, Y * z / math.cos(self.p)
            E = self.c[0] + u * math.cos(self.b) + v * math.sin(self.b)
            N = self.c[1] - u * math.sin(self.b) + v * math.cos(self.b)
            src.append((T / 2 + E, T / 2 - N))
        A, B = [], []
        for (x, y), (X_, Y_) in zip(corners, src):
            A.append([x, y, 1, 0, 0, 0, -x * X_, -y * X_]); B.append(X_)
            A.append([0, 0, 0, x, y, 1, -x * Y_, -y * Y_]); B.append(Y_)
        return tuple(np.linalg.solve(np.array(A, float), np.array(B, float)))


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


class Programme:
    """The 14 s camera programme shared by the video and the headless metrics: pitch 60 -> 0 -> 45, heading-up with a lagging camera
    bearing, then north-up.  `step(n)` returns the state of frame n (call it for n = 0, 1, 2, ... in order)."""
    FPS, SECONDS = 30, 14

    def __init__(self, pts, t0=0.0):
        self.pts = pts
        self.seg = np.hypot(*np.diff(pts, axis=0).T)
        self.cum = np.concatenate([[0], np.cumsum(self.seg)])
        self.speed = self.cum[-1] / (self.SECONDS + 1.0) * 0.98
        self.bearing_cam, self.t0 = None, t0

    def at(self, sdist):
        pts, seg, cum = self.pts, self.seg, self.cum
        i = int(min(max(np.searchsorted(cum, sdist) - 1, 0), len(pts) - 2))
        f = (sdist - cum[i]) / seg[i]
        p = pts[i] * (1 - f) + pts[i + 1] * f
        d = pts[min(i + 3, len(pts) - 1)] - pts[max(i - 3, 0)]
        return p, math.degrees(math.atan2(d[0], d[1])) % 360.0

    def step(self, n):
        tsec = n / self.FPS + self.t0
        p, hdg = self.at(self.speed * tsec)
        if tsec < 4.5:
            pitch, mode = 60.0, "heading-up"
        elif tsec < 7.5:
            pitch, mode = 60.0 * (1 - ease((tsec - 4.5) / 3.0)), "heading-up"
        elif tsec < 10.5:
            pitch, mode = 0.0, "north-up"
        else:
            pitch, mode = 45.0 * ease((tsec - 10.5) / 3.0), "heading-up"
        scale = 1.0 - 0.40 * (1 - pitch / 60.0)
        if self.bearing_cam is None:
            self.bearing_cam = hdg
        self.bearing_cam = (self.bearing_cam + wrap180((hdg if mode == "heading-up" else 0.0) - self.bearing_cam) * (0.07 if mode == "heading-up" else 0.10)) % 360.0
        return {"t": tsec, "p": p, "hdg": hdg, "pitch": pitch, "mode": mode, "scale": scale, "bearing": self.bearing_cam, "rel": (hdg - self.bearing_cam) % 360.0}


class Dissolver:
    """~100 ms cross-fade when the heading bucket changes (the runtime rule); returns (shown sprite, hard sprite, switched?)."""
    FADE = 3

    def __init__(self, ss):
        self.ss, self.prev_k, self.old_k, self.left = ss, None, None, 0

    def frame(self, pitch, rel):
        ss = self.ss
        _, _, _, k, _ = ss.select(pitch, rel)
        switched = self.prev_k is not None and k != self.prev_k
        if switched:
            self.left, self.old_k = self.FADE, self.prev_k
        self.prev_k = k
        new = ss.draw(pitch, rel)
        shown = new
        if self.left > 0 and self.old_k is not None:
            alpha = (self.FADE - self.left + 1) / self.FADE
            old = ss.draw(pitch, rel, k=self.old_k)
            top = new.copy()
            top.putalpha(top.split()[3].point(lambda v, al=alpha: int(v * al)))
            shown = old.copy()
            shown.alpha_composite(top)
            self.left -= 1
        return shown, new, switched


def run_metrics(a):
    """Headless: the same camera programme without a map; RMS change of the drawn sprite between frames, split into the motion floor
    (frames without a bucket flip) and the flip frames, for a hard switch vs the 100 ms dissolve."""
    import maptex
    ss = SpriteSet(a.sprites, a.tier)
    prog = Programme(np.array(maptex.route_points()))
    dis = Dissolver(ss)
    prev_hard = prev_dis = None
    floor, hard_sw, dis_sw = [], [], []
    n = prog.FPS * prog.SECONDS
    for i in range(n):
        st = prog.step(i)
        shown, new, switched = dis.frame(st["pitch"], st["rel"])
        h = np.asarray(S.over((128, 128, 128), new), np.float32) / 255.0
        d = np.asarray(S.over((128, 128, 128), shown), np.float32) / 255.0
        if prev_hard is not None:
            rh = float(np.sqrt(np.mean((h - prev_hard) ** 2)))
            rd = float(np.sqrt(np.mean((d - prev_dis) ** 2)))
            if switched:
                hard_sw.append(rh)
                dis_sw.append(rd)
            else:
                floor.append(rh)
        prev_hard, prev_dis = h, d
    res = {"frames": n, "fps": prog.FPS, "heading_flips": len(hard_sw),
           "motion_floor_rms": {"median": float(np.median(floor)), "p95": float(np.percentile(floor, 95)), "max": float(np.max(floor))},
           "flip_frame_rms": {"hard": {"mean": float(np.mean(hard_sw)), "max": float(np.max(hard_sw))}, "dissolve": {"mean": float(np.mean(dis_sw)), "max": float(np.max(dis_sw))}}}
    json.dump(res, open(a.out, "w"), indent=1)
    print(f"{res['heading_flips']} heading flips in {n} frames; motion floor median {res['motion_floor_rms']['median']:.4f} (p95 {res['motion_floor_rms']['p95']:.4f}); "
          f"flip frames: hard mean {res['flip_frame_rms']['hard']['mean']:.4f} max {res['flip_frame_rms']['hard']['max']:.4f} -> dissolve mean {res['flip_frame_rms']['dissolve']['mean']:.4f} max {res['flip_frame_rms']['dissolve']['max']:.4f}")


def run_video(a):
    import maptex
    W, H = 1080, 1920                                              # a 360 x 640 dp phone at 3x density
    ss = SpriteSet(a.sprites, a.tier)
    tk = json.load(open(S.TOKENS))
    land = S.hex_rgb(tk["map"][a.theme]["land"])
    tex = maptex.build(a.theme)
    pts = np.array(maptex.route_points())
    prog = Programme(pts, t0=a.t0)
    dis = Dissolver(ss)
    rt = tk["route"][a.theme]
    # dense copy of the route for drawing (circles every ~3 texture px merge into a smooth stroke)
    dp, dc = [pts[0]], [0.0]
    for i in range(len(pts) - 1):
        n = max(1, int(math.ceil(prog.seg[i] / 3.0)))
        for j in range(1, n + 1):
            dp.append(pts[i] + (pts[i + 1] - pts[i]) * (j / n))
            dc.append(prog.cum[i] + prog.seg[i] * (j / n))
    dpts, dcum = np.array(dp), np.array(dc)
    cam = Camera(W, H)
    os.makedirs(a.out, exist_ok=True)
    fdir = os.path.join(a.out, f"_frames_{a.theme}")
    os.makedirs(fdir, exist_ok=True)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)
    still_times = [float(x) for x in a.stills.split(",")] if a.stills else []
    saved = set()
    nframes = a.limit if a.limit else prog.FPS * prog.SECONDS
    for n in range(nframes):
        st = prog.step(n)
        pitch, mode, scale, p = st["pitch"], st["mode"], st["scale"], st["p"]
        hdg = st["hdg"]
        ahead = 260.0 * (pitch / 60.0) / scale
        cam.set((p[0] + ahead * math.sin(math.radians(hdg)), p[1] + ahead * math.cos(math.radians(hdg))), st["bearing"], pitch, scale)
        img = tex.transform((W, H), Image.PERSPECTIVE, cam.homography(maptex.T), Image.BICUBIC, fillcolor=land).convert("RGBA")
        if pitch > 5:                                              # haze towards the horizon (the real map is endless; this texture is not)
            fog = Image.new("RGBA", (W, H), land + (0,))
            fa = Image.linear_gradient("L").resize((W, int(H * 0.30))).rotate(180)
            fa = fa.point(lambda v: int(v * min(1.0, pitch / 40.0)))
            fog.paste(Image.merge("RGBA", (Image.new("L", fa.size, land[0]), Image.new("L", fa.size, land[1]), Image.new("L", fa.size, land[2]), fa)), (0, 0))
            img.alpha_composite(fog)
        dr = ImageDraw.Draw(img)
        s_here = int(np.searchsorted(dcum, prog.speed * st["t"]))
        for rng, fill, casing in ((range(min(len(dpts) - 1, s_here), len(dpts)), rt["selected"], rt["selectedCasing"]), (range(0, min(len(dpts), s_here + 1)), rt["passed"], rt["passed"])):
            ps = [(x, y, k) for x, y, k in (cam.project(dpts[i][0], dpts[i][1]) for i in rng) if -60 < x < W + 60 and -60 < y < H + 60 and 0.05 < k < 6]
            for width, color in ((40.0, casing), (30.0, fill)):
                col = S.hex_rgb(color)
                for x, y, k in ps:
                    r = width * k * scale / 2
                    dr.ellipse((x - r, y - r, x + r, y + r), fill=col)
        # the pointer exactly as the app draws it: two bracketing pitch buckets, one affine matrix each, blended; dissolve on a heading flip
        x, y, _ = cam.project(p[0], p[1])
        shown, _, _ = dis.frame(pitch, st["rel"])
        img.alpha_composite(shown, (int(round(x - ss.px / 2)), int(round(y - ss.px / 2))))
        lo, hi, tt, k, res = ss.select(pitch, st["rel"])
        d2 = ImageDraw.Draw(img)
        d2.rectangle((0, 0, W, 96), fill=(0, 0, 0, 120) if a.theme == "dark" else (255, 255, 255, 170))
        ink = (235, 230, 245, 255) if a.theme == "dark" else (50, 40, 80, 255)
        d2.text((20, 10), f"{mode:10s} pitch {pitch:4.1f}  zoom x{scale:.2f}", font=font, fill=ink)
        d2.text((20, 52), f"pitch buckets {lo:g}->{hi:g} t={tt:.2f}  yaw k={k:2d} res {res:+5.1f}", font=font, fill=ink)
        small = img.convert("RGB").resize((W // 2, H // 2), Image.LANCZOS)
        small.save(os.path.join(fdir, f"f{n:04d}.png"))
        for t_ in still_times:
            if abs(st["t"] - t_) < 0.5 / prog.FPS and t_ not in saved:
                saved.add(t_)
                small.save(os.path.join(a.out, f"pointer-runtime-{a.theme}-t{t_:04.1f}.png"))
    mp4 = os.path.join(a.out, f"pointer-runtime-sim-{a.theme}{a.name}.mp4")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(prog.FPS), "-i", os.path.join(fdir, "f%04d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", mp4], check=True)
    for f in os.listdir(fdir):
        os.remove(os.path.join(fdir, f))
    os.rmdir(fdir)
    print("wrote", mp4)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("video")
    v.add_argument("--sprites", required=True)
    v.add_argument("--tier", default="xxhdpi")
    v.add_argument("--theme", default="light", choices=["light", "dark"])
    v.add_argument("--out", required=True)
    v.add_argument("--stills", default="1.0,6.0,9.0,13.0")
    v.add_argument("--limit", type=int, default=0, help="render only the first N frames (testing)")
    v.add_argument("--t0", type=float, default=0.0, help="start time in the camera programme (testing)")
    v.add_argument("--name", default="", help="output name suffix (testing)")
    c = sub.add_parser("validate")
    c.add_argument("--asset", default="arrow")
    c.add_argument("--pitches", default="", help="restrict to these bucket pitches (emulate a coarser grid), e.g. 0,15,30,45,60")
    c.add_argument("--h", type=float, default=-1.0)
    c.add_argument("--json", default="", help="where to write the result (default: <truth>/validation.json)")
    c.add_argument("--frames", required=True)
    c.add_argument("--truth", required=True)
    c.add_argument("--sprites", required=True)
    c.add_argument("--sheet", default="")
    m = sub.add_parser("metrics")
    m.add_argument("--sprites", required=True)
    m.add_argument("--tier", default="xxhdpi")
    m.add_argument("--out", required=True)
    t = sub.add_parser("tune-h")
    t.add_argument("--asset", default="arrow")
    t.add_argument("--pitches", default="", help="restrict to these bucket pitches (emulate a coarser grid)")
    t.add_argument("--strategy", default="blend", choices=["single", "blend"])
    t.add_argument("--frames", required=True)
    t.add_argument("--truth", required=True)
    t.add_argument("--hs", default="", help="comma list of plane heights (u); default = fractions 0-0.8 of the asset's own height")
    t.add_argument("--out", required=True)
    a = ap.parse_args()
    {"video": run_video, "validate": run_validate, "tune-h": run_tune_h, "metrics": run_metrics}[a.cmd](a)


if __name__ == "__main__":
    main()
