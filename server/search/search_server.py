"""Aize place search: SQLite FTS5 over named OSM places, POIs and roads.

    GET /search?q=klcc&lat=3.13&lon=101.68&limit=8  ->  {"results":[{"name","lat","lon","kind","dist_m"}]}

Ranking mixes FTS relevance, the place's importance (a city outranks a shop) and distance from the
caller, so "pavilion" near Kuala Lumpur finds the mall and not a shop in Penang.
"""
import json
import math
import re
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DB = sys.argv[1] if len(sys.argv) > 1 else "/workspace/valhalla/places.db"
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8001

conn = sqlite3.connect(DB, check_same_thread=False)


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = __import__("math").sin(dp / 2) ** 2 + __import__("math").cos(p1) * __import__("math").cos(p2) * __import__("math").sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def fts_query(q):
    """Every token becomes a prefix term; the last one is the one being typed, so it must prefix-match."""
    toks = [t for t in re.split(r"[^\w]+", q.lower()) if t]
    if not toks:
        return None
    return " ".join(f'"{t}"*' for t in toks)


KIND_WEIGHT = {
    "place=city": 100, "place=state": 90, "place=municipality": 80, "place=town": 75,
    "place=suburb": 60, "place=district": 60, "place=village": 50, "place=neighbourhood": 45,
    "place=quarter": 45, "place=island": 55, "place=locality": 40,
    "shop=mall": 70, "shop=department_store": 55, "tourism=attraction": 60, "tourism=museum": 55,
    "tourism=aquarium; attraction": 60, "tourism=hotel": 30, "aeroway=aerodrome": 60,
    "railway=station": 55, "amenity=hospital": 50, "amenity=university": 50, "amenity=airport": 60,
    "amenity=parking": 5, "amenity=fuel": 8, "highway=bus_stop": 5, "railway=stop": 5,
    "highway=residential": 12, "highway=service": 8, "building": 10,
}
ROAD_WEIGHT = 20


def weight(kind: str) -> float:
    if kind in KIND_WEIGHT:
        return KIND_WEIGHT[kind]
    if kind.startswith("highway="):
        return ROAD_WEIGHT
    if kind.startswith("place="):
        return 40
    if kind.startswith("shop="):
        return 35
    if kind.startswith("tourism="):
        return 35
    if kind.startswith("amenity="):
        return 25
    if kind.startswith("leisure="):
        return 25
    return 10


def search(q, lat=None, lon=None, limit=8):
    match = fts_query(q)
    if not match:
        return []
    rows = conn.execute(
        """
        SELECT p.name, p.norm, p.kind, p.lat, p.lon, bm25(places_fts) AS score
        FROM places_fts JOIN places p ON p.id = places_fts.rowid
        WHERE places_fts MATCH ? ORDER BY score LIMIT 800
        """,
        (match,),
    ).fetchall()
    want = " ".join(re.split(r"[^\w]+", q.lower())).strip()
    out = {}
    for name, norm, kind, plat, plon, score in rows:
        dist = haversine(lat, lon, plat, plon) if lat is not None and lon is not None else 0.0
        if norm == want:
            quality = 40.0
        elif norm.startswith(want):
            quality = 25.0
        elif want in norm.split():
            quality = 10.0
        else:
            quality = 0.0
        value = quality + weight(kind) + max(-8.0, -2.5 * math.log10(1 + dist / 100.0)) + min(6.0, -score)
        key = (norm, kind.split(";")[0])
        prev = out.get(key)
        if prev is None or value > prev["score"]:
            out[key] = {"name": name, "lat": plat, "lon": plon, "kind": kind,
                        "dist_m": round(dist), "score": round(value, 2)}
    return sorted(out.values(), key=lambda r: -r["score"])[:limit]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        qs = parse_qs(u.query)
        if u.path == "/search":
            q = (qs.get("q") or [""])[0].strip()
            try:
                lat = float((qs.get("lat") or ["nan"])[0])
                lon = float((qs.get("lon") or ["nan"])[0])
            except ValueError:
                lat = lon = None
            if lat is not None and (math.isnan(lat) or math.isnan(lon)):
                lat = lon = None
            limit = max(1, min(20, int((qs.get("limit") or ["8"])[0] or 8)))
            if len(q) < 2:
                return self._send(200, {"results": []})
            return self._send(200, {"results": search(q, lat, lon, limit)})
        if u.path == "/status":
            n = conn.execute("select count(*) from places").fetchone()[0]
            return self._send(200, {"search": "aize", "places": n})
        self._send(404, {"error": "not found"})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print(f"search on :{PORT} using {DB}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
