#!/usr/bin/env python3
"""Drive the app along a route without leaving the desk.

The emulator has no GPS, so every fix has to be injected. This script injects them
properly: it walks a route at a configurable speed and can also misbehave on purpose
(stop reporting, jump, miss a turn) so the guidance, the re-route policy and the
notification can be exercised the same way every time.

Input is either a GPX track, or a Valhalla route fetched from the server (`--route`), which
is the more useful default: the app is then driven along the very road it planned.

Examples
--------
    # drive the planned route from KL Sentral to KLCC at 60 km/h
    scripts/replay-route.py --route 3.1343,101.6862 3.1179,101.6770 --speed 60

    # drive a recorded GPX at 2x, then miss the turn by 300 m after 40 % of the route
    scripts/replay-route.py --gpx track.gpx --speed 30 --miss-at 0.4 --miss-offset 300

    # what a tunnel looks like: no fixes for 20 s, then resume
    scripts/replay-route.py --route ... --tunnel-at 0.5 --tunnel-seconds 20

The script talks to adb only; it does not need the app to be built. Start the app, pick a
destination, and run this in another terminal.
"""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

DEFAULT_SERVER = "https://56399b2f75b741eaa53cf4456e42703c.bxcpreview.site"
UA = "aize-replay/1.0"


def adb(*args: str) -> str:
    out = subprocess.run(["adb", *args], capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"adb {' '.join(args)} failed: {out.stderr.strip()}")
    return out.stdout


def decode_polyline(text: str, precision: int = 6) -> list[tuple[float, float]]:
    """Valhalla's encoded shape -> [(lat, lon)]."""
    factor = 10 ** precision
    points: list[tuple[float, float]] = []
    i = 0
    lat = lon = 0
    while i < len(text):
        values = []
        for _ in range(2):
            result = shift = 0
            while True:
                b = ord(text[i]) - 63
                i += 1
                result |= (b & 0x1F) << shift
                shift += 5
                if b < 0x20:
                    break
            values.append(~(result >> 1) if result & 1 else result >> 1)
        lat += values[0]
        lon += values[1]
        points.append((lat / factor, lon / factor))
    return points


def fetch_route(server: str, origin: tuple[float, float], dest: tuple[float, float]) -> list[tuple[float, float]]:
    body = {
        "locations": [{"lat": origin[0], "lon": origin[1]}, {"lat": dest[0], "lon": dest[1]}],
        "costing": "auto",
    }
    url = f"{server.rstrip('/')}/route?json=" + urllib.parse.quote(json.dumps(body))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    return parse_shape(data)


def parse_shape(payload: dict) -> list[tuple[float, float]]:
    """Accepts a full Valhalla response or a bare trip object, joins every leg's shape."""
    trip = payload.get("trip", payload)
    points: list[tuple[float, float]] = []
    for leg in trip["legs"]:
        leg_points = decode_polyline(leg["shape"])
        points.extend(leg_points if not points else leg_points[1:])
    return points


def read_gpx(path: str) -> list[tuple[float, float]]:
    tree = ET.parse(path)
    root = tree.getroot()
    points = []
    for node in root.iter():
        if node.tag.endswith("trkpt"):        # gpx tracks; waypoints are not a drive
            points.append((float(node.get("lat")), float(node.get("lon"))))
    return points


def haversine(a: tuple[float, float], b: tuple[float, float]) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def offset(point: tuple[float, float], metres: float, bearing_deg: float) -> tuple[float, float]:
    """Move a point by `metres` towards `bearing_deg` (0 = north)."""
    dlat = (metres * math.cos(math.radians(bearing_deg))) / 111_320.0
    dlon = (metres * math.sin(math.radians(bearing_deg))) / (111_320.0 * math.cos(math.radians(point[0])))
    return point[0] + dlat, point[1] + dlon


def fix(lat: float, lon: float) -> None:
    adb("emu", "geo", "fix", f"{lon:.6f}", f"{lat:.6f}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Replay a route into the emulator's GPS.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--route", nargs=2, metavar=("ORIGIN", "DEST"), help="lat,lon lat,lon to route on the server")
    src.add_argument("--gpx", help="GPX track to replay")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--speed", type=float, default=50.0, help="km/h along the route (default 50)")
    ap.add_argument("--step", type=float, default=1.0, help="seconds between fixes (default 1)")
    ap.add_argument("--max-speed-kmh", type=float, default=0.0, help="cap the speed, useful for tight turns")
    ap.add_argument("--miss-at", type=float, default=-1.0, help="fraction of the route where the turn is missed")
    ap.add_argument("--miss-offset", type=float, default=250.0, help="metres to the side when missing the turn")
    ap.add_argument("--tunnel-at", type=float, default=-1.0, help="fraction of the route where fixes stop")
    ap.add_argument("--tunnel-seconds", type=float, default=20.0)
    ap.add_argument("--jump-at", type=float, default=-1.0, help="fraction of the route where the fix teleports")
    ap.add_argument("--jump-metres", type=float, default=1500.0)
    ap.add_argument("--dry-run", action="store_true", help="print the plan and the fixes, do not touch adb")
    args = ap.parse_args()

    if args.route:
        origin = tuple(float(v) for v in args.route[0].split(","))
        dest = tuple(float(v) for v in args.route[1].split(","))
        points = fetch_route(args.server, origin, dest)
    else:
        points = read_gpx(args.gpx)
    if len(points) < 2:
        sys.exit("the route has fewer than two points")

    lengths = [haversine(a, b) for a, b in zip(points, points[1:])]
    prefix = [0.0]
    for length in lengths:
        prefix.append(prefix[-1] + length)
    total = prefix[-1]
    print(f"{len(points)} points, {total / 1000:.2f} km, {args.speed:.0f} km/h, fix every {args.step:.0f} s")

    speed = args.speed / 3.6
    if args.max_speed_kmh:
        speed = min(speed, args.max_speed_kmh / 3.6)
    travelled = 0.0
    next_report = 0.0
    index = 0
    injected = 0
    tunnel_done = False

    while travelled <= total:
        fraction = travelled / total
        # walk the polyline to the point at `travelled`
        while index < len(lengths) - 1 and travelled > prefix[index + 1]:
            index += 1
        before = prefix[index]
        segment = lengths[index] if index < len(lengths) else 0.0
        t = 0.0 if segment <= 0 else min(1.0, max(0.0, (travelled - before) / segment))
        a, b = points[index], points[min(index + 1, len(points) - 1)]
        lat = a[0] + (b[0] - a[0]) * t
        lon = a[1] + (b[1] - a[1]) * t
        bearing = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360

        if 0 <= args.miss_at <= fraction:
            lat, lon = offset((lat, lon), args.miss_offset, bearing + 90)
        if 0 <= args.jump_at <= fraction:
            lat, lon = offset((lat, lon), args.jump_metres, bearing + 180)

        if args.dry_run:
            print(f"  {fraction * 100:5.1f}%  {lat:.6f},{lon:.6f}")
        else:
            fix(lat, lon)
        injected += 1

        if not tunnel_done and 0 <= args.tunnel_at <= fraction:
            tunnel_done = True
            print(f"  tunnel: no fixes for {args.tunnel_seconds:.0f} s")
            if not args.dry_run:
                time.sleep(args.tunnel_seconds)

        if fraction >= next_report:
            print(f"  {fraction * 100:5.1f}%  {travelled / 1000:5.2f} km")
            next_report = fraction + 0.1

        travelled += speed * args.step
        if not args.dry_run:
            time.sleep(args.step)

    print(f"done: {injected} fixes injected over {total / 1000:.2f} km")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
