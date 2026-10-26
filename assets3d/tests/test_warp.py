#!/usr/bin/env python3
"""Unit tests for the runtime warp (simulate_runtime.plane_affine) against independent vector maths (reproject_error.project/predicted).

  python3 assets3d/tests/test_warp.py

1. exactness: dots lying ON the warp plane (z = h) land on the true projection of the target view (<= 0.6 px) - checks signs, the
   clockwise convention, PIL's continuous pixel coordinates and the anchor handling in the image-space implementation.
2. agreement: for dots OFF the plane, the image-space displacement equals the geometry-only prediction (<= 0.6 px) - the two
   implementations (image warp and vertex maths) describe the same thing, so the error bounds in the manifests are the real ones.
3. identity: bucket == target view -> the sprite is unchanged.
"""
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import reproject_error as RE  # noqa: E402
import simulate_runtime as SR  # noqa: E402

N, SCALE = 512, 100.0            # frame px, px per world unit
C = N / 2.0
R_DOT = 5


def dot_image(pts_screen):
    arr = np.zeros((N, N), np.float32)
    yy, xx = np.mgrid[0:N, 0:N]
    for sx, sy in pts_screen:
        px, py = C + SCALE * sx, C - SCALE * sy
        arr = np.maximum(arr, np.exp(-(((xx + 0.5 - px) ** 2 + (yy + 0.5 - py) ** 2) / (2 * (R_DOT / 2.0) ** 2))))
    return Image.fromarray((arr * 255).astype(np.uint8), "L").convert("RGBA")


def centroid_near(im, sx, sy, win=14):
    a = np.asarray(im.convert("L"), np.float32) / 255.0
    px, py = C + SCALE * sx, C - SCALE * sy
    x0, x1, y0, y1 = int(px) - win, int(px) + win, int(py) - win, int(py) + win
    sub = a[max(y0, 0):y1, max(x0, 0):x1]
    yy, xx = np.mgrid[max(y0, 0):y1, max(x0, 0):x1]
    w = sub.sum()
    return ((xx + 0.5) * sub).sum() / w, ((yy + 0.5) * sub).sum() / w


def check(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + f"{name}: {detail}")
    return ok



def test_forward_matrix():
    """The forward affine documented for Android reproduces the true projection of on-plane points and is the inverse of the PIL warp."""
    ok = True
    phib, psib, rho, phi, h = 37.5, 45.0, -6.0, 41.0, 0.1
    rnd2 = random.Random(11)
    pts = np.array([[rnd2.uniform(-1.2, 1.2), rnd2.uniform(-1.2, 1.2), h] for _ in range(10)])
    A, B, Cc, D, E, F = SR.forward_matrix(phib, phi, rho, h * SCALE)
    bucket = RE.project(pts, phib, psib)
    truth = RE.project(pts, phi, psib + rho)
    worst = 0.0
    for b, t_ in zip(bucket, truth):
        u, v = SCALE * b[0], -SCALE * b[1]                    # sprite pixel relative to the anchor, y down
        x2, y2 = A * u + B * v + Cc, D * u + E * v + F
        worst = max(worst, math.hypot(x2 - SCALE * t_[0], y2 - (-SCALE * t_[1])))
    ok &= check("forward matrix (Android)", worst < 1e-6 * SCALE, f"on-plane points map to the true projection within {worst:.2e} px")
    # composition with the PIL (inverse) coefficients must be the identity
    a, b2, c0, d, e, f0 = (lambda im: None, None, None, None, None, None)
    cb, c = math.cos(math.radians(phib)), math.cos(math.radians(phi))
    sb = math.sin(math.radians(phib)); tn = math.tan(math.radians(phi)); r = math.radians(rho); cr, sr = math.cos(r), math.sin(r)
    ia, ib, ic = cr, sr / c, h * SCALE * tn * sr                          # inverse map (output -> source), anchor-relative
    id_, ie, if_ = -cb * sr, cb * cr / c, h * SCALE * (cb * tn * cr - sb)
    M = np.array([[A, B, Cc], [D, E, F], [0, 0, 1]])
    Minv = np.array([[ia, ib, ic], [id_, ie, if_], [0, 0, 1]])
    dev = float(np.abs(M @ Minv - np.eye(3)).max())
    ok &= check("forward = inverse of the PIL warp", dev < 1e-9, f"forward x inverse differs from the identity by {dev:.1e}")
    return ok

def main():
    rnd = random.Random(3)
    ok = True
    phib, psib, rho, phi, h = 45.0, 30.0, 7.0, 52.0, 0.5
    pts_on = np.array([[rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), h] for _ in range(8)])
    pts_off = np.array([[rnd.uniform(-1.2, 1.2), rnd.uniform(-1.2, 1.2), z] for z in (0.0, 0.0, 0.1, 0.9, 0.95, 0.3, 0.0, 0.8)])

    def run(pts):
        """Each dot is warped in its OWN image, so neighbours cannot contaminate the centroid."""
        err, meas, off = [], [], []
        pred = RE.predicted(pts, phi, psib + rho, [(phib, 12)], f"plane:{h:.2f}")      # 12 yaws -> 30 deg step -> residual 7 deg
        truth = RE.project(pts, phi, psib + rho)
        bucket = RE.project(pts, phib, psib)
        for i in range(len(pts)):
            warped = SR.plane_affine(dot_image([bucket[i]]), phib, phi, rho, h * SCALE)
            cx, cy = centroid_near(warped, truth[i][0], truth[i][1], win=24)
            err.append(math.hypot(cx - (C + SCALE * truth[i][0]), cy - (C - SCALE * truth[i][1])))
            mx, my = centroid_near(warped, pred[i][0], pred[i][1], win=24)
            meas.append(math.hypot(mx - (C + SCALE * pred[i][0]), my - (C - SCALE * pred[i][1])))
            off.append(math.hypot(*(pred[i] - truth[i])) * SCALE)
        return err, meas, off

    err_on, meas_on, pred_on = run(pts_on)
    ok &= check("on-plane exactness", max(err_on) <= 0.6, f"dots at z=h land within {max(err_on):.2f} px of the true projection (<= 0.6)")
    err_off, meas_off, pred_off = run(pts_off)
    ok &= check("agrees with vertex maths", max(meas_off) <= 0.6, f"warped dots sit within {max(meas_off):.2f} px of where reproject_error.predicted says (<= 0.6)")
    ok &= check("off-plane error is real", max(pred_off) > 5 * max(0.1, max(err_on)), f"points off the plane are displaced by up to {max(pred_off):.1f} px at this test scale (on-plane {max(err_on):.2f} px), so the test is not vacuous")
    # identity
    im = dot_image(RE.project(pts_on, phib, psib))
    same = SR.plane_affine(im, phib, phib, 0.0, h * SCALE)
    d = np.abs(np.asarray(im.convert("L"), np.float32) - np.asarray(same.convert("L"), np.float32)).max()
    ok &= check("identity", d <= 1.5, f"max pixel difference {d:.1f}/255 when bucket == view (<= 1.5)")
    # rotation direction: a point on +X axis rotated clockwise by 90 deg (seen from above, pitch 0) must go to -Y (down the screen)
    sx = SR.plane_affine(dot_image([(1.0, 0.0)]), 0.0, 0.0, 90.0, 0.0)
    cx, cy = centroid_near(sx, 0.0, -1.0)
    ok &= check("clockwise convention", abs(cx - C) < 0.6 and abs(cy - (C + SCALE)) < 0.6, f"(+1, 0) rotated 90 deg clockwise lands at ({(cx - C) / SCALE:+.2f}, {-(cy - C) / SCALE:+.2f}) (want (0, -1))")
    ok &= test_forward_matrix()
    print("\nALL PASS" if ok else "\nFAILURES")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
