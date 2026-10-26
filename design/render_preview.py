#!/usr/bin/env python3
"""Render design/preview/aize-theme-preview.png from the generated tokens (Pillow only).

An illustrative specimen — NOT final UI: palette ramps + the navigation HUD (instruction banner, ETA bar,
speed bubble, report button, alert pill, route line, user puck) in light and dark. Uses DejaVu as a stand-in
for the Figtree typeface. Original artwork; nothing from Waze is reproduced.
"""
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
T = json.load(open(os.path.join(HERE, "tokens", "aize-purple.tokens.json")))
os.makedirs(os.path.join(HERE, "preview"), exist_ok=True)


def _contrast_line():
    """'87/87 contrast pairs pass' from the audit the tokens were generated with (never a typed number)."""
    import re
    m = re.search(r"\*\*(\d+)/(\d+) pairs pass; (\d+) required failure", open(os.path.join(HERE, "tokens", "CONTRAST.md")).read())
    return f"{m.group(1)}/{m.group(2)} contrast pairs pass" if m else "see CONTRAST.md"


CONTRAST_LINE = _contrast_line()
S = 2  # supersample for smooth edges
FD = "/usr/share/fonts/truetype/dejavu/"


def font(size, bold=False):
    for name in ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",):
        try:
            return ImageFont.truetype(FD + name, int(size * S))
        except OSError:
            pass
    return ImageFont.load_default()


def hex2rgb(h, a=255):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def rr(d, box, r, fill, outline=None, width=1):
    x0, y0, x1, y1 = [v * S for v in box]
    d.rounded_rectangle((x0, y0, x1, y1), radius=r * S, fill=fill, outline=outline, width=width * S)


def text(d, xy, s, f, fill, anchor="la"):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def line(d, pts, w, fill):
    p = [(x * S, y * S) for x, y in pts]
    d.line(p, fill=fill, width=int(w * S), joint="curve")
    for x, y in p:
        d.ellipse((x - w * S / 2, y - w * S / 2, x + w * S / 2, y + w * S / 2), fill=fill)


def phone(mode, label):
    th, mp, rt, tr, rp = T["theme"][mode], T["map"][mode], T["route"][mode], T["traffic"][mode], T["reports"][mode]
    Wd, Hd = 360, 740
    img = Image.new("RGBA", (Wd * S, Hd * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img, "RGBA")
    rr(d, (0, 0, Wd, Hd), 36, hex2rgb("#1A1722"))                              # device body
    rr(d, (8, 8, Wd - 8, Hd - 8), 30, hex2rgb(mp["land"]))                    # screen / land
    scr = Image.new("RGBA", (Wd * S, Hd * S), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scr, "RGBA")
    # --- map: water, park, buildings, roads
    sd.polygon([(x * S, y * S) for x, y in [(8, 520), (150, 470), (230, 560), (120, 640), (8, 700)]], fill=hex2rgb(mp["water"]))
    sd.polygon([(x * S, y * S) for x, y in [(230, 190), (352, 170), (352, 300), (250, 320)]], fill=hex2rgb(mp["park"]))
    for bx, by, bw, bh in [(40, 190, 50, 36), (100, 215, 42, 54), (60, 300, 64, 40), (250, 360, 40, 50), (300, 390, 40, 36)]:
        sd.rectangle((bx * S, by * S, (bx + bw) * S, (by + bh) * S), fill=hex2rgb(mp["building"]))
    minor = [[(8, 250), (352, 280)], [(8, 420), (352, 400)], [(90, 120), (120, 700)], [(270, 120), (230, 700)]]
    for pts in minor:
        line(sd, pts, 9, hex2rgb(mp["roadMinorCasing"]))
    for pts in minor:
        line(sd, pts, 6.5, hex2rgb(mp["roadMinor"]))
    hw = [(8, 610), (140, 520), (200, 400), (180, 260), (210, 120)]
    line(sd, hw, 16, hex2rgb(mp["highwayCasing"]))
    line(sd, hw, 13, hex2rgb(mp["highway"]))
    # alternative + selected route (line casing + fill), ETA tag on the alternative
    alt = [(60, 640), (110, 560), (130, 470), (215, 430), (250, 330), (240, 210)]
    line(sd, alt, 11, hex2rgb(rt["alternativeCasing"]))
    line(sd, alt, 7, hex2rgb(rt["alternative"]))
    sel = [(180, 600), (200, 520), (190, 420), (172, 330), (180, 250), (205, 150)]
    line(sd, sel, 17, hex2rgb(rt["selectedCasing"]))
    line(sd, sel, 12, hex2rgb(rt["selected"]))
    # congested stretch drawn over the route as a traffic overlay
    line(sd, [(190, 420), (172, 330)], 6, hex2rgb(tr["heavy"]))
    # user puck + accuracy ring
    cx, cy = 180, 585
    sd.ellipse(((cx - 34) * S, (cy - 34) * S, (cx + 34) * S, (cy + 34) * S), fill=hex2rgb(rt["selected"], 40))
    sd.ellipse(((cx - 15) * S, (cy - 15) * S, (cx + 15) * S, (cy + 15) * S), fill=hex2rgb("#FFFFFF" if mode == "light" else th["surface"]))
    sd.polygon([(cx * S, (cy - 11) * S), ((cx + 9) * S, (cy + 9) * S), (cx * S, (cy + 4) * S), ((cx - 9) * S, (cy + 9) * S)], fill=hex2rgb(rt["navArrow"]))
    # alert pill on route
    f10 = font(10.5, True)
    rr(sd, (212, 296, 318, 326), 15, hex2rgb(th["surface"]), outline=hex2rgb(rp["police"]), width=2)
    sd.ellipse((218 * S, 303 * S, 237 * S, 322 * S), fill=hex2rgb(rp["police"]))
    text(sd, (245, 311), "Police", f10, hex2rgb(th["onSurface"]), "lm")
    img.alpha_composite(scr)
    d = ImageDraw.Draw(img, "RGBA")
    # --- instruction banner (top)
    rr(d, (18, 20, Wd - 18, 118), 22, hex2rgb(th["primary"]))
    # right-turn arrow
    ax, ay = 52, 52
    pts = [(ax, ay + 40), (ax, ay + 12), (ax + 22, ay + 12), (ax + 22, ay + 2), (ax + 42, ay + 22), (ax + 22, ay + 42), (ax + 22, ay + 32), (ax + 12, ay + 32), (ax + 12, ay + 40)]
    d.polygon([(x * S, y * S) for x, y in pts], fill=hex2rgb(th["onPrimary"]))
    text(d, (112, 42), "300 m", font(30, True), hex2rgb(th["onPrimary"]), "lm")
    text(d, (112, 82), "Turn right onto Jalan Aize", font(12.5), hex2rgb(th["onPrimary"]), "lm")
    # speed bubble + limit
    rr(d, (18, 400, 78, 460), 30, hex2rgb(th["surface"]), outline=hex2rgb(th["outlineVariant"]), width=1)
    text(d, (48, 421), "62", font(21, True), hex2rgb(th["onSurface"]), "mm")
    text(d, (48, 446), "km/h", font(8.5), hex2rgb(th["onSurfaceVariant"]), "mm")
    d.ellipse((24 * S, 340 * S, 70 * S, 386 * S), fill=hex2rgb("#FFFFFF"), outline=hex2rgb(T["color"]["red"]["600"]), width=5 * S)
    text(d, (47, 363), "60", font(15, True), hex2rgb("#1B1B1F"), "mm")
    # report FAB + recenter
    d.ellipse((286 * S, 470 * S, 342 * S, 526 * S), fill=hex2rgb(th["primary"]))
    d.polygon([(314 * S, 484 * S), (330 * S, 512 * S), (298 * S, 512 * S)], fill=hex2rgb(th["onPrimary"]))
    d.rectangle((312.5 * S, 492 * S, 315.5 * S, 503 * S), fill=hex2rgb(th["primary"]))
    d.ellipse((312.5 * S, 506 * S, 315.5 * S, 509 * S), fill=hex2rgb(th["primary"]))
    rr(d, (292, 540, 336, 584), 22, hex2rgb(th["surface"]), outline=hex2rgb(th["outlineVariant"]), width=1)
    d.ellipse((306 * S, 554 * S, 322 * S, 570 * S), outline=hex2rgb(th["primary"]), width=3 * S)
    # --- ETA bar (bottom)
    rr(d, (14, 620, Wd - 14, 716), 26, hex2rgb(th["surface"]), outline=hex2rgb(th["outlineVariant"]), width=1)
    text(d, (38, 648), "14 min", font(25, True), hex2rgb(th["onSurface"]), "lm")
    d.ellipse((152 * S, 640 * S, 164 * S, 652 * S), fill=hex2rgb(tr["light"]))
    text(d, (38, 684), "8.4 km  ·  arrive 09:41", font(12), hex2rgb(th["onSurfaceVariant"]), "lm")
    rr(d, (262, 636, 336, 700), 22, hex2rgb(th["errorContainer"]))
    text(d, (299, 668), "Exit", font(14, True), hex2rgb(th["onErrorContainer"]), "mm")
    text(d, (Wd / 2, 728), "", font(8), (0, 0, 0, 255), "mm")
    return img.resize((Wd * S // 2 * 1, Hd * S // 2 * 1), Image.LANCZOS) if False else img


def swatch_sheet(w, h):
    img = Image.new("RGBA", (w * S, h * S), hex2rgb("#FBFAFD"))
    d = ImageDraw.Draw(img, "RGBA")
    text(d, (24, 24), "Aize · purple theme", font(26, True), hex2rgb("#27034F"), "lm")
    text(d, (24, 56), f"Generated by design/generate_tokens.py · OKLCH tone ladders · {CONTRAST_LINE}", font(11), hex2rgb("#5C5568"), "lm")
    y = 92
    for name, key in (("Purple  (brand · primary)", "purple"), ("Lilac  (secondary)", "lilac"), ("Mint  (tertiary)", "mint"), ("Neutral  (lavender-tinted)", "neutral")):
        text(d, (24, y), name, font(12, True), hex2rgb("#27034F"), "lm")
        y += 14
        steps = [k for k in T["color"][key] if k.isdigit() and 50 <= int(k) <= 950]
        for i, k in enumerate(steps):
            x = 24 + i * 52
            rr(d, (x, y, x + 48, y + 44), 8, hex2rgb(T["color"][key][k]))
            c = T["color"][key][k]
            ink = "#FFFFFF" if int(k) >= 500 else "#1B1B1F"
            text(d, (x + 24, y + 22), k, font(9.5, True), hex2rgb(ink), "mm")
        y += 54
        text(d, (24, y), "  ".join(f"{k}:{T['color'][key][k]}" for k in steps[4:8]), font(8.5), hex2rgb("#5C5568"), "lm")
        y += 26
    # functional palettes
    text(d, (24, y), "Traffic (light / dark)", font(12, True), hex2rgb("#27034F"), "lm")
    y += 14
    for i, k in enumerate(T["traffic"]["light"]):
        x = 24 + i * 100
        rr(d, (x, y, x + 46, y + 26), 6, hex2rgb(T["traffic"]["light"][k]))
        rr(d, (x + 48, y, x + 94, y + 26), 6, hex2rgb(T["traffic"]["dark"][k]))
        text(d, (x + 47, y + 38), k, font(8.5), hex2rgb("#5C5568"), "mm")
    y += 54
    text(d, (24, y), "Report types (light)", font(12, True), hex2rgb("#27034F"), "lm")
    y += 14
    for i, (k, v) in enumerate(T["reports"]["light"].items()):
        x = 24 + (i % 5) * 104
        yy = y + (i // 5) * 46
        d.ellipse((x * S, yy * S, (x + 28) * S, (yy + 28) * S), fill=hex2rgb(v))
        text(d, (x + 34, yy + 14), k.replace("_", " "), font(9.5), hex2rgb("#1B1B1F"), "lm")
    y += 96
    text(d, (24, y), "Motion tokens", font(12, True), hex2rgb("#27034F"), "lm")
    mo = T["motion"]
    text(d, (24, y + 20), "durations (ms): " + "  ".join(f"{k} {v}" for k, v in mo["duration"].items()), font(9.5), hex2rgb("#1B1B1F"), "lm")
    text(d, (24, y + 38), "easing: standard (0.4,0,0.2,1) · silkyIn (0.2,0.7,-0.01,1) · silkyOut (0.9,0.01,0.99,0.75)", font(9.5), hex2rgb("#1B1B1F"), "lm")
    text(d, (24, y + 56), "radius: 4 8 12 16 24 · buttons 18/24/32 · elevation 0 1 3 6 8 12 dp", font(9.5), hex2rgb("#1B1B1F"), "lm")
    return img


PANEL = 620
sheet = swatch_sheet(PANEL, 740)
pl, pd_ = phone("light", "Light"), phone("dark", "Dark")
Wd, Hd = 360, 740
W_total = PANEL + 24 + Wd + 24 + Wd + 24
canvas = Image.new("RGBA", (W_total * S, (Hd + 48) * S), hex2rgb("#FBFAFD"))
canvas.alpha_composite(sheet, (0, 24 * S))
canvas.alpha_composite(pl, ((PANEL + 24) * S, 24 * S))
canvas.alpha_composite(pd_, ((PANEL + 24 + Wd + 24) * S, 24 * S))
out = canvas.convert("RGB").resize((W_total * S // 2 * 1, (Hd + 48) * S // 2 * 1), Image.LANCZOS) if False else canvas.convert("RGB")
out.save(os.path.join(HERE, "preview", "aize-theme-preview.png"), optimize=True)
print("saved", os.path.join(HERE, "preview", "aize-theme-preview.png"), out.size)
