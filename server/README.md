# Aize server: routing + place search, no Docker

Two small services behind one port, so the app needs a single address.

| Port | What | How |
|------|------|-----|
| 8002 | public entry point | `search/proxy.py` — `/search*` → search server, everything else → Valhalla |
| 8010 | Valhalla 3.9.1 (`/route`, `/status`, …) | `valhalla-setup.sh`, prebuilt `pyvalhalla` wheel |
| 8001 | place search (`/search?q=…`) | `search/search_server.py`, SQLite FTS5 |

## Build

```bash
# 1. routing graph (~650 MB of tiles, ~3 min, 4 GB RAM peak)
DIR=./valhalla-data server/valhalla-setup.sh build

# 2. search index from the same extract (~90 MB, ~2.5 min)
python3 -m pip download osmium --no-deps -d /tmp/whl && python3 -m zipfile -e /tmp/whl/osmium-*.whl search/pkg
PYTHONPATH=search/pkg python3 search/build_index.py valhalla-data/data/extract.osm.pbf valhalla-data/places.db
```

## Run

```bash
DIR=./valhalla-data server/valhalla-setup.sh serve &                  # :8010
python3 search/search_server.py valhalla-data/places.db 8001 &        # :8001
PORT=8002 SEARCH_URL=http://127.0.0.1:8001 VALHALLA_URL=http://127.0.0.1:8010 python3 search/proxy.py
```

Check it:

```bash
curl 'localhost:8002/status'                       # {"version":"3.9.1", ...}
curl 'localhost:8002/search?q=klcc&lat=3.13&lon=101.68'
```

## Search ranking

Every name in the extract (places, shops, amenities, roads, stations) is indexed with FTS5 prefix matching.
Results are ranked by match quality (exact > prefix > word), a per-kind weight (a mall outranks a bus stop,
a city outranks a shop) and distance from the caller. Duplicate road segments are collapsed to the nearest one.

It is not Photon: no address parsing, no house numbers, no transliteration. For "Jalan Ampang" or "Suria KLCC"
it is enough; for "12 Jalan Ampang" it is not.

## Keep it running

The three services are meant to be systemd units so they come back after a
reboot; see `deploy/README.md`. Memory after the first route: Valhalla about
500 MB, search about 60 MB — a 1 GiB host runs the full Malaysia graph.
