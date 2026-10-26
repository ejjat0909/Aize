#!/usr/bin/env python3
"""Generate the Aize purple design tokens + a WCAG contrast audit (stdlib only).

Outputs (next to this script's ../tokens/):
  aize-purple.tokens.json   W3C-design-tokens-style file (colour scales, light/dark themes, radii, elevation, motion, type, map, traffic, reports)
  CONTRAST.md               every foreground/background pair with its WCAG 2.x ratio and pass/fail
and prints a short summary. Exit status 1 if a *required* pair fails (used in CI).

Palette method: OKLCH tone ladders (perceptually even lightness), gamut-mapped to sRGB by reducing chroma.
Motion/shape numbers are derived from the Waze teardown (docs/01) but expressed as Aize tokens.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "tokens")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- colour maths
def _gamma(x):
    x = max(0.0, min(1.0, x))
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def oklch_lin(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_, m_, s_ = L + 0.3963377774 * a + 0.2158037573 * b, L - 0.1055613458 * a - 0.0638541728 * b, L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s, -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklch_hex(L, C, h):
    while C > 0:
        r, g, b = oklch_lin(L, C, h)
        if all(-1e-4 <= v <= 1 + 1e-4 for v in (r, g, b)):
            break
        C -= 0.002
    r, g, b = oklch_lin(L, max(C, 0), h)
    return "#%02X%02X%02X" % tuple(round(_gamma(v) * 255) for v in (r, g, b))


def lum(hexc):
    def f(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contrast(a, b):
    la, lb = lum(a), lum(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def blend(fg, bg, alpha):
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    g = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(alpha * x + (1 - alpha) * y) for x, y in zip(f, g))




def pick_badge(scale, glyph_hex, minimum=3.2, order=("300", "400", "500", "600", "700", "800", "900")):
    """Lightest scale step on which `glyph_hex` still reaches `minimum`:1 - saturated enough to pop on the map, dark enough to read."""
    for step in order:
        if contrast(glyph_hex, scale[step]) >= minimum:
            return scale[step]
    return scale[order[-1]]


# ---------------------------------------------------------------- scales
STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
L_LADDER = dict(zip(STEPS, [0.975, 0.945, 0.895, 0.825, 0.735, 0.645, 0.555, 0.475, 0.395, 0.315, 0.235]))


def scale(hue, chroma_peak, chroma_curve=None):
    curve = chroma_curve or dict(zip(STEPS, [0.08, 0.17, 0.33, 0.52, 0.74, 0.92, 1.0, 0.90, 0.76, 0.62, 0.48]))
    return {str(s): oklch_hex(L_LADDER[s], chroma_peak * curve[s], hue) for s in STEPS}


HUE_PURPLE = 297
purple = scale(HUE_PURPLE, 0.255)                       # brand: "Aize Violet"
lilac = scale(HUE_PURPLE + 22, 0.20)                    # secondary: warmer orchid
mint = scale(185, 0.115)                                # tertiary accent: cool teal for contrast against violet
neutral = {str(s): oklch_hex(L_LADDER[s], 0.016, HUE_PURPLE) for s in STEPS}   # lavender-tinted neutrals
neutral["0"], neutral["1000"] = "#000000", oklch_hex(0.15, 0.012, HUE_PURPLE)
red, amber, green, blue, orange = scale(27, 0.22), scale(78, 0.16), scale(150, 0.17), scale(255, 0.19), scale(55, 0.19)

W = "#FFFFFF"
themes = {
    "light": {
        "primary": purple["600"], "onPrimary": W, "primaryContainer": purple["100"], "onPrimaryContainer": purple["900"],
        "secondary": lilac["700"], "onSecondary": W, "secondaryContainer": lilac["100"], "onSecondaryContainer": lilac["900"],
        "tertiary": mint["700"], "onTertiary": W, "tertiaryContainer": mint["100"], "onTertiaryContainer": mint["900"],
        "background": neutral["50"], "onBackground": neutral["950"], "surface": W, "onSurface": neutral["950"],
        "surfaceVariant": neutral["100"], "onSurfaceVariant": neutral["700"], "surfaceContainer": neutral["100"], "outline": neutral["500"], "outlineVariant": neutral["200"],
        "error": red["600"], "onError": W, "errorContainer": red["100"], "onErrorContainer": red["900"],
        "success": green["700"], "warning": amber["700"], "info": blue["600"], "scrim": "#000000",
        "inverseSurface": neutral["900"], "inverseOnSurface": neutral["50"], "inversePrimary": purple["300"],
    },
    "dark": {
        "primary": purple["300"], "onPrimary": purple["900"], "primaryContainer": purple["800"], "onPrimaryContainer": purple["100"],
        "secondary": lilac["300"], "onSecondary": lilac["900"], "secondaryContainer": lilac["800"], "onSecondaryContainer": lilac["100"],
        "tertiary": mint["300"], "onTertiary": mint["900"], "tertiaryContainer": mint["800"], "onTertiaryContainer": mint["100"],
        "background": neutral["1000"], "onBackground": neutral["100"], "surface": neutral["950"], "onSurface": neutral["100"],
        "surfaceVariant": neutral["900"], "onSurfaceVariant": neutral["300"], "surfaceContainer": neutral["900"], "outline": neutral["500"], "outlineVariant": neutral["800"],
        "error": red["300"], "onError": red["900"], "errorContainer": red["800"], "onErrorContainer": red["100"],
        "success": green["300"], "warning": amber["300"], "info": blue["300"], "scrim": "#000000",
        "inverseSurface": neutral["100"], "inverseOnSurface": neutral["900"], "inversePrimary": purple["600"],
    },
}
# map surfaces (the base map is a calm, lavender-tinted neutral so purple routes pop)
map_style = {
    "light": {"background": "#F3F1F7", "land": "#F3F1F7", "water": "#CFE0F2", "park": "#DCEBD8", "building": "#E6E2EE", "roadMinor": "#FFFFFF", "roadMinorCasing": "#D9D4E4", "roadMajor": "#FFFFFF", "roadMajorCasing": "#C3BCD3", "highway": "#FBF9FF", "highwayCasing": "#A89FBF", "label": "#3F3A4D", "labelHalo": "#FFFFFF"},
    "dark": {"background": "#16131C", "land": "#16131C", "water": "#17283A", "park": "#1C2A22", "building": "#221E2B", "roadMinor": "#2C2738", "roadMinorCasing": "#1B1722", "roadMajor": "#3A3448", "roadMajorCasing": "#1B1722", "highway": "#4A4260", "highwayCasing": "#1B1722", "label": "#CFC8DE", "labelHalo": "#16131C"},
}
route = {"light": {"selected": purple["600"], "selectedCasing": W, "alternative": neutral["500"], "alternativeCasing": W, "passed": neutral["300"], "navArrow": purple["700"]},
         "dark": {"selected": purple["300"], "selectedCasing": neutral["1000"], "alternative": neutral["400"], "alternativeCasing": neutral["1000"], "passed": neutral["700"], "navArrow": purple["200"]}}
# functional colours keep conventional meaning; hues are Aize's own
traffic = {"light": {"free": green["600"], "light": amber["500"], "moderate": orange["500"], "heavy": red["500"], "standstill": red["900"]},
           "dark": {"free": green["400"], "light": amber["400"], "moderate": orange["400"], "heavy": red["400"], "standstill": red["600"]}}
reports = {"light": {"police": blue["600"], "hazard": amber["500"], "accident": red["600"], "jam": orange["600"], "closure": orange["800"], "camera": neutral["600"], "gas": green["600"], "place": lilac["500"], "chat": mint["600"], "map_issue": neutral["700"]},
           "dark": {"police": blue["300"], "hazard": amber["400"], "accident": red["400"], "jam": orange["400"], "closure": orange["500"], "camera": neutral["400"], "gas": green["400"], "place": lilac["300"], "chat": mint["400"], "map_issue": neutral["400"]}}

pins = {   # map pins: badge colour + glyph colour (glyph contrast is a REQUIRED audit pair)
    "police": {"badge": pick_badge(blue, "#FFFFFF"), "glyph": "#FFFFFF"},
    "hazard": {"badge": amber["400"], "glyph": neutral["950"]},
    "accident": {"badge": pick_badge(red, "#FFFFFF"), "glyph": "#FFFFFF"},
    "jam": {"badge": pick_badge(orange, "#FFFFFF"), "glyph": "#FFFFFF"},
    "closure": {"badge": pick_badge(red, "#FFFFFF", order=("700", "800", "900")), "glyph": "#FFFFFF"},
    "camera": {"badge": pick_badge(neutral, "#FFFFFF", order=("600", "700", "800")), "glyph": "#FFFFFF"},
    "gas": {"badge": pick_badge(green, "#FFFFFF"), "glyph": "#FFFFFF"},
    "parking": {"badge": pick_badge(lilac, "#FFFFFF"), "glyph": "#FFFFFF"},
    "destination": {"badge": themes["light"]["primary"], "glyph": "#FFFFFF"},
}

tokens = {
    "$description": "Aize design tokens — purple theme. Generated by design/generate_tokens.py; do not edit by hand.",
    "color": {"purple": purple, "lilac": lilac, "mint": mint, "neutral": neutral, "red": red, "amber": amber, "green": green, "blue": blue, "orange": orange},
    "theme": themes, "map": map_style, "route": route, "traffic": traffic, "reports": reports, "pins": pins,
    "radius": {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "pill": 999, "button": {"small": 18, "normal": 24, "large": 32}, "sheet": 24, "alert": 16},
    "elevation": {"0": 0, "1": 1, "2": 3, "3": 6, "4": 8, "5": 12},
    "spacing": {"2xs": 2, "xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24, "2xl": 32, "3xl": 48},
    "motion": {
        "duration": {"instant": 100, "fast": 150, "base": 200, "moderate": 300, "slow": 500, "deliberate": 700},
        "easing": {"standard": [0.4, 0.0, 0.2, 1.0], "decelerate": [0.0, 0.0, 0.2, 1.0], "accelerate": [0.4, 0.0, 1.0, 1.0], "silkyIn": [0.2, 0.7, -0.01, 1.0], "silkyOut": [0.9, 0.01, 0.99, 0.75]},
        "spring": {"popIn": {"stiffness": 380, "dampingRatio": 0.62}, "settle": {"stiffness": 200, "dampingRatio": 0.9}},
        "choreography": {"alertPopIn": {"alpha": 100, "scale": [200, 300], "startOffset": 300}, "sheetSlide": 150, "pageForward": 200, "pageBack": 200, "sheetUp": 700, "sheetDown": 500, "spinner": 600},
        "reducedMotion": "replace transforms with 100 ms cross-fades; disable looping Lottie/pulses",
    },
    "typography": {
        "fontFamily": {"primary": "Figtree", "fallback": ["Roboto", "sans-serif"], "mono": "JetBrains Mono"},
        "scale": {"displayLarge": [48, 56, 700], "headlineLarge": [32, 40, 700], "headlineMedium": [28, 36, 700], "titleLarge": [22, 28, 600], "titleMedium": [18, 24, 600], "bodyLarge": [16, 24, 400], "bodyMedium": [14, 20, 400], "labelLarge": [14, 20, 600], "labelSmall": [11, 16, 600],
                  "navInstruction": [28, 32, 700], "navDistance": [40, 44, 800], "etaPrimary": [24, 28, 800], "speedometer": [32, 36, 800]},
        "unit": "[size sp, line-height sp, weight]",
    },
    "size": {"touchTarget": 48, "reportButton": 56, "iconSmall": 20, "iconMedium": 24, "iconLarge": 32, "etaBarHeight": 72, "instructionBannerMinHeight": 96, "bottomSheetPeek": 120},
}

# ---------------------------------------------------------------- contrast audit
REQ = []  # (label, fg, bg, min, required)


def add(label, fg, bg, mn, required=True):
    REQ.append((label, fg, bg, mn, required))


for mode, t in themes.items():
    for pair in [("primary", "onPrimary", 4.5), ("primaryContainer", "onPrimaryContainer", 4.5), ("secondary", "onSecondary", 4.5), ("secondaryContainer", "onSecondaryContainer", 4.5),
                 ("tertiary", "onTertiary", 4.5), ("tertiaryContainer", "onTertiaryContainer", 4.5), ("error", "onError", 4.5), ("errorContainer", "onErrorContainer", 4.5),
                 ("background", "onBackground", 7.0), ("surface", "onSurface", 7.0), ("surfaceVariant", "onSurfaceVariant", 4.5), ("inverseSurface", "inverseOnSurface", 7.0)]:
        add(f"{mode}: {pair[1]} on {pair[0]}", t[pair[1]], t[pair[0]], pair[2])
    add(f"{mode}: primary as text/icon on background", t["primary"], t["background"], 4.5)
    add(f"{mode}: primary as text/icon on surface", t["primary"], t["surface"], 4.5)
    add(f"{mode}: outline (non-text UI) on background", t["outline"], t["background"], 3.0)
    for k in ("success", "warning", "info", "error"):
        add(f"{mode}: {k} on surface (icons/text)", t[k], t["surface"], 3.0)
    ms, rt = map_style[mode], route[mode]
    add(f"{mode}: selected route vs map land", rt["selected"], ms["land"], 3.0)
    add(f"{mode}: selected route vs road fill", rt["selected"], ms["roadMajor"], 3.0)
    add(f"{mode}: alternative route vs map land", rt["alternative"], ms["land"], 2.0)
    add(f"{mode}: map label on land", ms["label"], ms["land"], 4.5)
    add(f"{mode}: map label on water", ms["label"], ms["water"], 4.5, required=(mode == "light"))
bgm = {"light": W, "dark": themes["dark"]["surface"]}
for mode in ("light", "dark"):
    for name, c in traffic[mode].items():
        add(f"{mode}: traffic.{name} on surface (line/icon)", c, bgm[mode], 1.8 if name in ("light", "free") and mode == "light" else 2.4, required=False)
    for name, c in reports[mode].items():
        add(f"{mode}: report.{name} glyph colour on surface", c, bgm[mode], 3.0 if mode == "light" else 2.5, required=False)

for kind, pc in pins.items():
    add(f"pin {kind}: glyph on badge", pc["glyph"], pc["badge"], 3.0)

rows, fails = [], 0
for label, fg, bg, mn, req in REQ:
    r = contrast(fg, bg)
    ok = r >= mn
    if not ok and req:
        fails += 1
    rows.append((label, fg, bg, r, mn, ok, req))

with open(os.path.join(OUT, "CONTRAST.md"), "w") as fh:
    fh.write("# Aize colour contrast audit (WCAG 2.x)\n\nGenerated by `design/generate_tokens.py`. *Required* rows gate CI; *advisory* rows (traffic/report glyph colours) document known trade-offs — those colours are always paired with an icon or label, never colour alone.\n\n")
    fh.write("| Pair | Foreground | Background | Ratio | Min | Result | Gate |\n|---|:---:|:---:|---:|---:|:---:|:---:|\n")
    for label, fg, bg, r, mn, ok, req in rows:
        fh.write(f"| {label} | `{fg}` | `{bg}` | {r:.2f} | {mn:g} | {'✅ pass' if ok else '❌ FAIL'} | {'required' if req else 'advisory'} |\n")
    fh.write(f"\n**{sum(1 for x in rows if x[5])}/{len(rows)} pairs pass; {fails} required failure(s).**\n")

json.dump(tokens, open(os.path.join(OUT, "aize-purple.tokens.json"), "w"), indent=2)
print("purple scale:", purple)
print("themes light primary/onPrimary:", themes["light"]["primary"], themes["light"]["onPrimary"], "| dark primary:", themes["dark"]["primary"])
print(f"contrast: {sum(1 for x in rows if x[5])}/{len(rows)} pass, {fails} required failures")
for label, fg, bg, r, mn, ok, req in rows:
    if not ok:
        print(("REQUIRED FAIL " if req else "advisory fail ") + f"{label}: {fg} on {bg} = {r:.2f} < {mn}")
sys.exit(1 if fails else 0)
