#!/usr/bin/env python3
"""Contact sheet of the SHIPPED assets (packed WebP sheets + the runtime algorithm), at deliberately off-grid views.

  python3 assets3d/tools/make_preview.py            # -> assets3d/preview/aize-3d-contact-sheet.png

Pointer and vehicles are drawn by simulate_runtime.SpriteSet.draw (two bracketing pitch buckets, one affine matrix each, blended), pins
as their single cell.  Light and dark map backgrounds come from the design tokens.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import simulate_runtime as SR  # noqa: E402
import sprite_lib as S  # noqa: E402

A3D = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
DIST = os.path.join(A3D, "dist")
OUT = os.path.join(A3D, "preview", "aize-3d-contact-sheet.png")
FD = "/usr/share/fonts/truetype/dejavu/"
TIER = "xxhdpi"
T = 232                     # tile size
PAD = 22


def font(sz, bold=False):
    return ImageFont.truetype(FD + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), sz)


def draw_solid(stem, phi, rel):
    ss = SR.SpriteSet(os.path.join(DIST, stem, f"{stem}.sprites.json"), TIER)
    return ss.draw(phi, rel), ss


def tile(bg, sprite, scale_to, label=None, anchor=(0.5, 0.5), place=(0.5, 0.5)):
    im = Image.new("RGB", (T, T), bg)
    sp = sprite
    k = scale_to / max(sp.size)
    sp = sp.resize((max(1, int(sp.size[0] * k)), max(1, int(sp.size[1] * k))), Image.LANCZOS)
    x = int(T * place[0] - sp.size[0] * anchor[0])
    y = int(T * place[1] - sp.size[1] * anchor[1])
    base = im.convert("RGBA")
    base.alpha_composite(sp, (x, y))
    im = base.convert("RGB")
    if label:
        d = ImageDraw.Draw(im)
        d.text((8, T - 22), label, font=font(12), fill=(110, 100, 135) if sum(bg) > 400 else (170, 160, 195))
    return im


def main():
    tk = json.load(open(S.TOKENS))
    light, dark = S.hex_rgb(tk["map"]["light"]["land"]), S.hex_rgb(tk["map"]["dark"]["land"])
    views = [(0, 0), (0, 45), (30, 0), (30, 120), (52, 37), (60, 0), (60, 200)]
    cars = [c for c in ("car_sedan", "car_taxi", "car_suv") if os.path.exists(os.path.join(DIST, c, f"{c}.sprites.json"))]
    pins = [p for p in ("police", "hazard", "accident", "jam", "closure", "camera", "gas", "parking", "destination") if os.path.exists(os.path.join(DIST, f"pin_{p}", f"pin_{p}.sprites.json"))]
    cols = 9
    W = PAD * 2 + cols * T
    rows = [("Pointer · arrow and puck (light map)", light), ("Pointer · arrow and puck (dark map)", dark), ("Vehicle skins · pitch 45°, three headings each", light), ("Map pins · viewport-aligned billboards (light and dark)", light)]
    H = 150 + len(rows) * (T + 56) + 30
    sheet = Image.new("RGB", (W, H), (251, 250, 253))
    d = ImageDraw.Draw(sheet)
    d.text((PAD, 24), "Aize · 3D assets rendered in Blender", font=font(34, True), fill=(39, 3, 79))
    d.text((PAD, 74), "Shipped WebP sheets reconstructed by the runtime algorithm at off-grid views (pitch / heading in each caption); original models, token-driven colours.", font=font(15), fill=(92, 85, 104))
    d.text((PAD, 98), "Light = day map colours, dark = night map colours; everything is lit from the upper left so shadows fall to the lower right.", font=font(15), fill=(92, 85, 104))
    y = 140
    # rows 1-2: arrow at several views + puck
    for r, (title, bg) in enumerate(rows[:2]):
        d.text((PAD, y), title, font=font(18, True), fill=(39, 3, 79))
        y += 30
        for c, (phi, rel) in enumerate(views):
            sp, ss = draw_solid("arrow", phi, rel)
            sheet.paste(tile(bg, sp, int(T * 0.95), f"arrow  pitch {phi}°  heading {rel}°"), (PAD + c * T, y))
        if os.path.exists(os.path.join(DIST, "puck", "puck.sprites.json")):
            for c, phi in ((7, 30), (8, 60)):
                ps, _ = draw_solid("puck", float(phi), 0.0)
                sheet.paste(tile(bg, ps, int(T * 0.85), f"puck  pitch {phi}°"), (PAD + c * T, y))
        y += T + 26
    # row 3: cars
    d.text((PAD, y), rows[2][0], font=font(18, True), fill=(39, 3, 79))
    y += 30
    c = 0
    for stem in cars:
        for rel in (30, 150, 300):
            sp, _ = draw_solid(stem, 45.0, float(rel))
            sheet.paste(tile(light, sp, int(T * 0.95), f"{stem[4:]}  heading {rel}°"), (PAD + c * T, y))
            c += 1
    y += T + 26
    # row 4: pins on light and dark
    d.text((PAD, y), rows[3][0], font=font(18, True), fill=(39, 3, 79))
    y += 30
    for c, k in enumerate(pins):
        stem = f"pin_{k}"
        m = json.load(open(os.path.join(DIST, stem, f"{stem}.sprites.json")))
        sh = m["tiers"][TIER]["sheets"]["0"]
        cell = Image.open(os.path.join(DIST, stem, sh["file"])).convert("RGBA")
        bg = light if c < 5 else dark
        sheet.paste(tile(bg, cell, int(T * 0.9), k, anchor=(m["anchor"][0], m["anchor"][1]), place=(0.5, 0.80)), (PAD + c * T, y))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    sheet.save(OUT, optimize=True)
    print("wrote", OUT, sheet.size, f"cars={cars} pins={len(pins)}")


if __name__ == "__main__":
    main()
