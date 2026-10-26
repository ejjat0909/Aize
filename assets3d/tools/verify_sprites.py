#!/usr/bin/env python3
"""Acceptance tests for the Aize pre-rendered sprite pipeline.  Exit status 1 if any REQUIRED check fails.

  python3 assets3d/tools/verify_sprites.py --frames build/frames/arrow --asset arrow [--dist assets3d/dist/arrow]
  python3 assets3d/tools/verify_sprites.py --calib build/frames/calib          # camera maths (needs the `calib` asset rendered)
  python3 assets3d/tools/verify_sprites.py --selftest                           # premultiplied resize / fringe unit test

Checks (REQ = gates, adv = advisory):
  REQ  clip        no composed frame has alpha within 2 px of its border (object + shadow fit the frame at every pitch/yaw)
  REQ  anchor      calibration dot centroid is at the frame centre (+-1 px)                       [calib]
  REQ  pitch       calibration disc height/width == cos(pitch)  (+-1 %)                           [calib]
  REQ  yaw         silhouette at yaw k equals the yaw-0 silhouette rotated by k*step (IoU >= 0.95) [pitch 0 frames]
  REQ  brand       body hue within 3 deg of the token hue, mean lightness within 0.05 of the token  [arrow/puck]
  REQ  fringe      premultiplied resize adds no dark halo (self-test)
  REQ  roundtrip   packed WebP vs composed master at the same tier: PSNR >= 38 dB (alpha-weighted)
  REQ  budget      per-tier total size <= budget
  REQ  silhouette  outline-level vertices within --max-sil-dp (1.0 flat assets; 4.0 cars = regression ceiling) at every pitch/heading (manifest, from the mesh)
  REQ  raised      all vertices within 6 dp (regression gate)
  REQ  image       mean PSNR >= 25 dB vs true renders of off-grid views (manifest, from tune-h)
  REQ  pop-pitch   image change at a pitch-bucket crossing <= 0.02 RMS (manifest, from tune-h)
  REQ  pop-yaw     image change at a heading-bucket flip <= 0.06 RMS (manifest, from tune-h)
  adv  determinism (re-render check is done by CI, not here)
"""
import argparse
import colorsys
import glob
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageChops  # noqa: E402

import sprite_lib as S  # noqa: E402

RESULTS = []


def check(name, ok, detail, required=True):
    RESULTS.append((name, ok, detail, required))
    print(("PASS " if ok else ("FAIL " if required else "warn ")) + f"{name:<10} {detail}")


# ---------------------------------------------------------------------------------------------- colour helpers
def oklch(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (x ** (1 / 3) for x in (l, m, s))
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b2 = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return L, math.hypot(a, b2), (math.degrees(math.atan2(b2, a)) + 360) % 360


def psnr_weighted(a, b):
    """PSNR over premultiplied RGBA (so transparent pixels don't dominate)."""
    pa, pb = S.premultiply(a), S.premultiply(b)
    diff = ImageChops.difference(pa, pb)
    h = diff.histogram()
    n = a.size[0] * a.size[1] * 4
    sse = 0
    for c in range(4):
        for v in range(256):
            sse += h[c * 256 + v] * v * v
    mse = sse / n
    return 99.0 if mse == 0 else 10 * math.log10(255 * 255 / mse)


# ---------------------------------------------------------------------------------------------- tests
def test_selftest():
    """A disc of pure colour with a soft edge, rendered 'straight alpha, black under transparent' like Blender, then
    shrunk 4x.  Naive RGBA resize darkens the edge; the premultiplied path must not."""
    n = 512
    col = (137, 55, 241)
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    px = im.load()
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - n / 2 + 0.5, y - n / 2 + 0.5)
            a = max(0.0, min(1.0, (n * 0.40 - d) / 6.0 + 0.5))
            if a > 0:
                px[x, y] = col + (int(round(a * 255)),)
    ours = S.resize_rgba(im, n // 4)
    naive = S.resize_rgba_naive(im, n // 4)

    def edge_err(img):
        p = img.load()
        worst = 0.0
        for y in range(img.size[1]):
            for x in range(img.size[0]):
                r, g, b, a = p[x, y]
                if 8 < a < 247:
                    worst = max(worst, max(abs(r - col[0]), abs(g - col[1]), abs(b - col[2])))
        return worst
    e_ours, e_naive = edge_err(ours), edge_err(naive)
    check("fringe", e_ours <= 3 and e_naive > 40, f"worst edge-colour error after a 4x shrink: float-premultiplied {e_ours:.0f}/255 (<=3); independent-channel resize {e_naive:.0f}/255 (>40, i.e. the halo it prevents is real)")


def composed_frames(frames_dir, stem, pitches, yaws):
    out = {}
    for p in pitches:
        for k in range(yaws):
            base = os.path.join(frames_dir, f"{stem}_{S.pname(p)}_y{k:02d}")
            out[(S.pkey(p), k)] = S.compose_frame(base + ".png", base + ".sh.png")
    return out


def test_clip(frames):
    worst = (0, None)
    for key, im in frames.items():
        w, h = im.size
        a = im.split()[3]
        border = 2
        edge = Image.new("L", (w, h), 0)
        edge.paste(255, (0, 0, w, border)); edge.paste(255, (0, h - border, w, h)); edge.paste(255, (0, 0, border, h)); edge.paste(255, (w - border, 0, w, h))
        m = ImageChops.multiply(a, edge)
        mx = max(m.getdata())
        if mx > worst[0]:
            worst = (mx, key)
    check("clip", worst[0] <= 3, f"{len(frames)} frames; max alpha in the 2 px border = {worst[0]} (<=3)" + (f" at {worst[1]}" if worst[0] > 3 else ""))


def test_yaw(frames_dir, stem, yaws, step):
    base = Image.open(os.path.join(frames_dir, f"{stem}_p00_y00.png")).convert("RGBA").split()[3]
    ious = []
    for k in range(1, yaws):
        cur = Image.open(os.path.join(frames_dir, f"{stem}_p00_y{k:02d}.png")).convert("RGBA").split()[3]
        rot = base.rotate(-k * step, resample=Image.BICUBIC, center=(base.size[0] / 2, base.size[1] / 2))   # PIL rotates counter-clockwise
        a = rot.point(lambda v: 255 if v > 127 else 0)
        b = cur.point(lambda v: 255 if v > 127 else 0)
        inter = sum(1 for x, y in zip(a.getdata(), b.getdata()) if x and y)
        union = sum(1 for x, y in zip(a.getdata(), b.getdata()) if x or y)
        ious.append(inter / union)
    check("yaw", min(ious) >= 0.95, f"silhouette IoU vs rotated yaw-0 at {yaws - 1} yaws: min {min(ious):.3f}, mean {sum(ious) / len(ious):.3f} (>=0.95)")


def test_brand(frames_dir, stem, token="color.purple.600"):
    tok = S.hex_rgb(S.token_hex(token))
    tL, tC, tH = oklch(tok)
    im = Image.open(os.path.join(frames_dir, f"{stem}_p00_y00.png")).convert("RGBA")
    W = im.size[0]
    px = im.load()
    left, right = [], []
    for y in range(W):
        for x in range(W):
            r, g, b, a = px[x, y]
            if a < 250:
                continue
            h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if s > 0.45 and 0.70 < h < 0.85:
                (left if x < W / 2 else right).append((r, g, b))
    if not left or not right:
        check("brand", False, "no purple body pixels found")
        return
    mean = lambda l: tuple(sum(c[i] for c in l) / len(l) for i in range(3))
    ml, mr = mean(left), mean(right)
    Ll, Cl, Hl = oklch(ml)
    Lr, Cr, Hr = oklch(mr)
    mL = (Ll + Lr) / 2
    hue_ok = abs(Hl - tH) <= 3 and abs(Hr - tH) <= 3
    check("brand", hue_ok and abs(mL - tL) <= 0.05,
          f"hue L/R {Hl:.1f}/{Hr:.1f} vs token {tH:.1f} (<=3 deg); mean lightness {mL:.3f} vs {tL:.3f} (<=0.05); facet contrast dL={Ll - Lr:.3f}")


def test_calib(frames_dir):
    """Camera maths: the white dot (world origin) must sit on the declared anchor, and the disc's AREA must scale like cos(pitch)
    (area is sub-pixel accurate, unlike a bounding box)."""
    man = json.load(open(os.path.join(frames_dir, "calib.manifest.json")))
    ax, ay = man.get("anchor", [0.5, 0.5])
    worst_a, areas = 0.0, {}
    for p in man["pitches"]:
        im = Image.open(os.path.join(frames_dir, f"calib_{S.pname(p)}_y00.png")).convert("RGBA")
        W = im.size[0]
        px = im.load()
        xs = ys = n = 0
        area = 0.0
        for y in range(W):
            for x in range(W):
                r, g, b, a = px[x, y]
                area += a / 255.0
                if a >= 128 and r > 235:
                    xs += x + 0.5; ys += y + 0.5; n += 1
        cx, cy = xs / n, ys / n
        areas[p] = area
        worst_a = max(worst_a, abs(cx - ax * W), abs(cy - ay * W))
    check("anchor", worst_a <= 1.0, f"calibration dot is within {worst_a:.2f} px of the declared anchor ({ax:g}, {ay:g}) at every pitch (<=1.0)")
    if 0 in areas or 0.0 in areas:
        a0 = areas.get(0, areas.get(0.0))
        worst = max(abs(areas[p] / a0 - math.cos(math.radians(p))) / math.cos(math.radians(p)) for p in areas)
        check("pitch", worst <= 0.01, f"disc area vs cos(pitch): worst relative error {worst * 100:.2f} % (<=1 %) over pitches {sorted(areas)}")
    else:
        check("pitch", False, "calibration needs a pitch-0 frame")


def test_dist(frames, dist_dir, stem, budget_kib, max_err_dp, max_sil_dp, min_psnr, max_pitch_pop, max_yaw_pop):
    man = json.load(open(os.path.join(dist_dir, f"{stem}.sprites.json")))
    worst = 99.0
    for tname, t in man["tiers"].items():
        px = t["frame_px"]
        for pk, sh in t["sheets"].items():
            sheet = Image.open(os.path.join(dist_dir, sh["file"])).convert("RGBA")
            cols = sh["cols"]
            for k in range(man["yaws"]):
                fr = sheet.crop(((k % cols) * px, (k // cols) * px, (k % cols) * px + px, (k // cols) * px + px))
                ref = S.resize_rgba(frames[(pk, k)], px)
                worst = min(worst, psnr_weighted(ref, fr))
    check("roundtrip", worst >= 38.0, f"packed WebP vs composed master, worst alpha-weighted PSNR {worst:.1f} dB over every frame and tier (>=38)")
    for tname, t in man["tiers"].items():
        kib = t["total_bytes"] / 1024
        check("budget", kib <= budget_kib, f"{stem} {tname}: {kib:.0f} KiB (<= {budget_kib} KiB)")
    rp = man.get("reprojection")
    if rp:
        check("silhouette", rp["base_worst_err_dp"] <= max_sil_dp,
              f"lowest {rp['base_height_frac'] * 100:.0f} % of the mesh (rim / footprint / wheels = the high-contrast outline), every pitch 0-60 and heading: worst {rp['base_worst_err_dp']:.2f} dp, p95 {rp['base_p95_err_dp']:.2f} dp (<= {max_sil_dp} dp); plane h={rp['plane_h_u']:.2f} u")
        check("raised", rp["worst_err_dp"] <= max_err_dp, f"all vertices incl. raised parts (ridge, roof): worst {rp['worst_err_dp']:.2f} dp, p95 {rp['p95_err_dp']:.2f} dp (<= {max_err_dp} dp)")
        im = rp.get("image")
        if im:
            check("image", im["psnr_mean_db"] >= min_psnr, f"vs true Blender renders of {im['views']} off-grid views: PSNR mean {im['psnr_mean_db']:.1f} dB, min {im['psnr_min_db']:.1f} dB (mean >= {min_psnr})")
            if im.get("pitch_pop_rms_max") is not None:
                check("pop-pitch", im["pitch_pop_rms_max"] <= max_pitch_pop, f"image change when the camera pitch crosses a bucket ({im.get('strategy', '?')}): RMS {im['pitch_pop_rms_max']:.4f} (<= {max_pitch_pop}; continuous - needs no dissolve)")
                check("pop-yaw", im["yaw_pop_rms_max"] <= max_yaw_pop, f"image change at a heading-bucket flip: RMS {im['yaw_pop_rms_max']:.4f} (<= {max_yaw_pop}; comparable to one frame of real rotation in a turn; an optional ~100 ms dissolve softens it)")
            else:
                check("pop", im["switch_pop_rms_max"] <= 0.035, f"largest image change at a bucket switch: RMS {im['switch_pop_rms_max']:.4f} (<= 0.035)")
        else:
            check("tuned", False, "plane height was not tuned against true renders (run simulate_runtime.py tune-h and pack with --tune)", required=False)
        check("steady", rp["scenarios"]["overview"]["max_dp"] <= 0.05, f"top-down overview error {rp['scenarios']['overview']['max_dp']:.2f} dp (exact: in-plane rotation is exact at pitch 0)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames")
    ap.add_argument("--asset")
    ap.add_argument("--variant", default="")
    ap.add_argument("--dist")
    ap.add_argument("--calib")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--budget-kib", type=int, default=3500)
    ap.add_argument("--max-err-dp", type=float, default=6.0, help="gate: all vertices incl. raised parts")
    ap.add_argument("--max-sil-dp", type=float, default=1.0, help="gate: outline-level (lowest 20 %% of the mesh) vertices. 1.0 suits flat assets (arrow, puck: the outline IS the rim). "
                    "Cars use 4.0: their image-calibrated plane sits at the body, so the wheels/underbody carry the error - a regression ceiling set from the measured 3.1-3.4 dp, not a quality claim")
    ap.add_argument("--min-psnr", type=float, default=25.0, help="gate: mean PSNR vs true renders of off-grid views")
    ap.add_argument("--max-pitch-pop", type=float, default=0.02, help="gate: RMS image change when the pitch crosses a bucket")
    ap.add_argument("--max-yaw-pop", type=float, default=0.06, help="gate: RMS image change at a heading-bucket flip (dissolved at run time)")
    ap.add_argument("--brand", action="store_true", help="run the brand-colour check (purple bodies)")
    ap.add_argument("--yaw", action="store_true", help="run the yaw-rotation check (needs pitch-0 frames)")
    ap.add_argument("--json", help="append the results of this run to a JSON list file")
    a = ap.parse_args()
    if a.selftest:
        test_selftest()
    if a.calib:
        test_calib(a.calib)
    if a.frames and a.asset:
        stem = a.asset + (("_" + a.variant) if a.variant else "")
        man = json.load(open(os.path.join(a.frames, f"{stem}.manifest.json")))
        frames = composed_frames(a.frames, stem, man["pitches"], man["yaws"])
        test_clip(frames)
        if a.yaw and 0 in man["pitches"] and man["yaws"] > 1:
            test_yaw(a.frames, stem, man["yaws"], man["yaw_step_deg"])
        if a.brand:
            test_brand(a.frames, stem)
        if a.dist:
            test_dist(frames, a.dist, stem, a.budget_kib, a.max_err_dp, a.max_sil_dp, a.min_psnr, a.max_pitch_pop, a.max_yaw_pop)
    bad = [r for r in RESULTS if r[3] and not r[1]]
    if a.json:
        prev = json.load(open(a.json)) if os.path.exists(a.json) else []
        tag = (a.asset or ("calib" if a.calib else "selftest")) + (("_" + a.variant) if a.variant else "")
        prev += [{"scope": tag, "check": n, "pass": bool(ok), "required": req, "detail": d} for n, ok, d, req in RESULTS]
        json.dump(prev, open(a.json, "w"), indent=1)
    print(f"\n{sum(1 for r in RESULTS if r[1])}/{len(RESULTS)} checks pass; {len(bad)} required failure(s)")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
