"""Build a small place/POI search index (SQLite FTS5) from an OSM extract. No Photon, no Java, no compiler.

    python3 build_index.py extract.osm.pbf search.sqlite
"""
import re
import sqlite3
import sys
import time
import unicodedata

import osmium

PBF = sys.argv[1] if len(sys.argv) > 1 else "/workspace/valhalla/data/malaysia.osm.pbf"
DB = sys.argv[2] if len(sys.argv) > 2 else "/workspace/search/search.sqlite"

PLACE_RANK = {"city": 100, "municipality": 70, "district": 65, "county": 65, "town": 80, "village": 60,
              "suburb": 50, "neighbourhood": 45, "quarter": 45, "hamlet": 40, "locality": 35, "island": 35}
POI_NODE_KEYS = ("amenity", "shop", "tourism", "leisure", "office", "aeroway", "railway", "healthcare",
                 "craft", "historic", "club", "place", "natural", "waterway", "man_made", "highway")
WAY_KEYS = ("amenity", "shop", "tourism", "leisure", "building", "place", "highway", "aeroway", "railway",
            "natural", "landuse", "historic")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not "\u0300" <= c <= "\u036f")
    return " ".join(re.sub(r"[^\w\s]", " ", s).split())


def kind_of(tags) -> str:
    for k in ("amenity", "shop", "tourism", "leisure", "office", "aeroway", "railway", "healthcare",
              "craft", "historic", "place", "highway", "natural", "waterway", "landuse", "man_made"):
        if k in tags:
            return f"{k}={tags[k]}"
    return "building" if "building" in tags else "other"


def rank_of(tags) -> int:
    if "place" in tags:
        return PLACE_RANK.get(tags["place"], 40)
    if tags.get("highway") in ("motorway", "trunk", "primary", "secondary", "tertiary"):
        return 25
    if tags.get("railway") == "station" or "aeroway" in tags:
        return 30
    if tags.get("tourism") in ("attraction", "museum", "hotel"):
        return 20
    return 10


def main() -> None:
    db = sqlite3.connect(DB)
    db.executescript("""
        PRAGMA journal_mode=OFF; PRAGMA synchronous=OFF;
        DROP TABLE IF EXISTS places; DROP TABLE IF EXISTS places_fts;
        CREATE TABLE places(id INTEGER PRIMARY KEY, name TEXT, norm TEXT, kind TEXT, kind_rank INT, lat REAL, lon REAL);
        CREATE VIRTUAL TABLE places_fts USING fts5(norm, content='', tokenize="unicode61 remove_diacritics 2", prefix='2 3');
    """)
    rows, t0, n = [], time.time(), 0

    def flush():
        db.executemany("INSERT INTO places(name,norm,kind,kind_rank,lat,lon) VALUES(?,?,?,?,?,?)", rows)
        rows.clear()

    db.execute("BEGIN")
    for o in osmium.FileProcessor(PBF).with_locations():
        n += 1
        if n % 5_000_000 == 0:
            print(f"{n / 1e6:.0f}M objects, {len(rows)} pending, {time.time() - t0:.0f}s", flush=True)
        tags = o.tags
        name = tags.get("name") or tags.get("name:en")
        if not name or len(name) > 80:
            continue
        if o.is_node():
            if not any(k in tags for k in POI_NODE_KEYS):
                continue
            lat, lon = o.location.lat, o.location.lon
        elif o.is_way():
            if not any(k in tags for k in WAY_KEYS):
                continue
            pts = [(nd.lat, nd.lon) for nd in o.nodes if nd.location.valid()]
            if not pts:
                continue
            lat = sum(p[0] for p in pts) / len(pts)
            lon = sum(p[1] for p in pts) / len(pts)
        else:
            continue
        key = norm(name)
        if not key:
            continue
        rows.append((name, key, kind_of(tags), rank_of(tags), lat, lon))
        if len(rows) >= 20000:
            flush()
    if rows:
        flush()
    db.execute("COMMIT")
    db.execute("INSERT INTO places_fts(rowid, norm) SELECT id, norm FROM places")
    db.execute("INSERT INTO places_fts(places_fts) VALUES('optimize')")
    db.commit()
    print("objects", n, "indexed", db.execute("select count(*) from places").fetchone()[0],
          "in", round(time.time() - t0), "s")


if __name__ == "__main__":
    main()
