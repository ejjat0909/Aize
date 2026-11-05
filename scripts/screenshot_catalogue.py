#!/usr/bin/env python3
"""Screenshot the design catalogue and diff it against the goldens.

The catalogue is a debug-only activity with one screen per section, so this script can launch a page by name and
get the same pixels every time: no taps, no scroll position, no leftover state. That is the whole point — "the
components look right" becomes a number.

Usage:
    scripts/screenshot_catalogue.py                 # compare every page against docs/catalogue/golden/
    scripts/screenshot_catalogue.py --update        # rewrite the goldens (review the images before committing)
    scripts/screenshot_catalogue.py --sections icon,button
    scripts/screenshot_catalogue.py --apk app/build/outputs/apk/debug/app-debug.apk

Exit codes: 0 all pages match, 1 a page differs or is missing, 2 no emulator / bad arguments.

The emulator must be running with the debug APK installed, at font scale 1.0. The script sets the font scale and
the light/dark mode itself, because a golden captured at another scale is a golden for another design.
"""
from __future__ import annotations

import argparse
import io
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageChops

REPO = Path(__file__).resolve().parent.parent
GOLDEN = REPO / "docs" / "catalogue" / "golden"
PACKAGE = "app.aize"
ACTIVITY = f"{PACKAGE}/.catalogue.CatalogueActivity"

# One page per enum value in app/src/debug/kotlin/app/aize/catalogue/CatalogueSection.kt.
# CatalogueCoverageTest fails if these drift apart.
SECTIONS = ["colour", "type", "icon", "button", "control", "surface", "shape", "motion"]

# Thresholds. These are not zero because text antialiasing moves a pixel or two between runs on the same
# emulator, and a gate that cries wolf is a gate people turn off. They are tight enough that a colour change,
# a radius change, a missing glyph or a shifted baseline all trip them.
MAX_MEAN_DIFF = 0.60        # mean absolute difference over every channel of every pixel
MAX_DIFF_PIXEL_PCT = 0.10   # percentage of pixels whose worst channel moves by more than 8/255
DIFF_PIXEL_THRESHOLD = 8
# The system navigation bar lives in the bottom of the screenshot and redraws itself (the gesture pill fades),
# which is not the app's pixels. Compare only the app's own area.
CONTENT_HEIGHT = 1848


def adb(serial: str | None, *args: str, binary: bool = False) -> bytes | str:
    cmd = ["adb"] + (["-s", serial] if serial else []) + list(args)
    out = subprocess.run(cmd, capture_output=True, check=False)
    if out.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed: {out.stderr.decode(errors='replace').strip()}")
    return out.stdout if binary else out.stdout.decode(errors="replace")


def one_device(serial: str | None) -> str:
    devices = [
        line.split()[0]
        for line in adb(None, "devices").splitlines()[1:]
        if line.strip() and line.split()[1] == "device"
    ]
    if serial:
        if serial not in devices:
            raise SystemExit(f"exit 2: device {serial} is not attached (attached: {devices or 'none'})")
        return serial
    if not devices:
        raise SystemExit("exit 2: no emulator or device attached — start one, then re-run")
    if len(devices) > 1:
        raise SystemExit(f"exit 2: more than one device ({devices}); pass --serial")
    return devices[0]


def prepare(serial: str, apk: Path | None) -> None:
    if apk is not None:
        adb(serial, "install", "-r", str(apk))
    # A golden is only a golden at a known font scale and theme.
    adb(serial, "shell", "settings", "put", "system", "font_scale", "1.0")
    adb(serial, "shell", "cmd", "uimode", "night", "no")
    adb(serial, "shell", "settings", "put", "system", "screen_off_timeout", "1800000")
    # The emulator's SystemUI likes to throw "isn't responding" over whatever is being photographed. A golden
    # with a dialog in it is a golden of the dialog.
    adb(serial, "shell", "settings", "put", "global", "hide_error_dialogs", "1")
    adb(serial, "shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb(serial, "shell", "wm", "dismiss-keyguard")


def capture(serial: str, section: str) -> Image.Image:
    adb(serial, "shell", "am", "force-stop", PACKAGE)
    adb(serial, "shell", "am", "start", "-W", "-n", ACTIVITY, "--es", "section", section)
    # The catalogue is static, but a page that animates in would capture mid-transition; one second is the
    # cheapest way to be sure and the whole run is under a minute.
    subprocess.run(["sleep", "1.2"], check=True)
    png = adb(serial, "exec-out", "screencap", "-p", binary=True)
    return Image.open(io.BytesIO(png)).convert("RGB")


def compare(shot: Image.Image, golden_path: Path) -> tuple[float, float, str]:
    """Returns (mean difference, percent of differing pixels, verdict)."""
    if not golden_path.exists():
        return 0.0, 100.0, "missing golden"
    golden = Image.open(golden_path).convert("RGB")
    if golden.size != shot.size:
        return 255.0, 100.0, f"size {shot.size[0]}x{shot.size[1]} vs golden {golden.size[0]}x{golden.size[1]}"
    shot = shot.crop((0, 0, shot.size[0], min(shot.size[1], CONTENT_HEIGHT)))
    golden = golden.crop((0, 0, golden.size[0], min(golden.size[1], CONTENT_HEIGHT)))
    diff = ImageChops.difference(shot, golden)
    # Mean over every channel, from the histograms: getdata() is deprecated and a 2M-pixel Python sum is slow.
    total = 0
    for band in diff.split():
        hist = band.histogram()
        total += sum(value * count for value, count in enumerate(hist))
    mean = total / (shot.size[0] * shot.size[1] * 3)
    # A pixel "differs" when any channel moves more than the antialiasing threshold.
    worst = diff.split()[0]
    for band in diff.split()[1:]:
        worst = ImageChops.lighter(worst, band)
    hist = worst.histogram()
    differing = sum(hist[DIFF_PIXEL_THRESHOLD + 1:])
    pct = 100.0 * differing / (shot.size[0] * shot.size[1])
    ok = mean <= MAX_MEAN_DIFF and pct <= MAX_DIFF_PIXEL_PCT
    return mean, pct, "ok" if ok else "differs"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Screenshot the Aize design catalogue and diff it against goldens.")
    parser.add_argument("--update", action="store_true", help="rewrite the golden images instead of comparing")
    parser.add_argument("--serial", help="adb serial, when more than one device is attached")
    parser.add_argument("--apk", type=Path, help="install this APK first")
    parser.add_argument("--sections", help=f"comma-separated subset of: {','.join(SECTIONS)}")
    parser.add_argument("--out", type=Path, default=GOLDEN, help="golden directory (default docs/catalogue/golden)")
    args = parser.parse_args(argv)

    sections = SECTIONS
    if args.sections:
        sections = [s.strip() for s in args.sections.split(",") if s.strip()]
        unknown = [s for s in sections if s not in SECTIONS]
        if unknown:
            print(f"exit 2: unknown section(s) {unknown}; known: {SECTIONS}")
            return 2

    try:
        serial = one_device(args.serial)
        prepare(serial, args.apk)
    except RuntimeError as e:
        print(f"exit 2: {e}")
        return 2

    args.out.mkdir(parents=True, exist_ok=True)
    failures = 0
    print(f"{'page':10} {'mean':>7} {'differs':>8}  verdict")
    for section in sections:
        shot = capture(serial, section)
        golden_path = args.out / f"{section}.png"
        if args.update:
            shot.save(golden_path)
            print(f"{section:10} {'-':>7} {'-':>8}  written {golden_path.relative_to(REPO)}")
            continue
        mean, pct, verdict = compare(shot, golden_path)
        if verdict != "ok":
            failures += 1
            # Keep the actual capture next to the goldens so a failure can be looked at, not just read about.
            shot.save(args.out / f"{section}.actual.png")
        print(f"{section:10} {mean:7.2f} {pct:7.2f}%  {verdict}")
    if args.update:
        print(f"wrote {len(sections)} golden image(s) to {args.out.relative_to(REPO)}")
        return 0
    if failures:
        print(f"{failures} of {len(sections)} page(s) differ; actual captures are in {args.out.relative_to(REPO)}/*.actual.png")
        return 1
    print(f"all {len(sections)} pages match")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
