#!/usr/bin/env bash
# Dockerless Valhalla for Aize: uses the prebuilt binaries inside the `pyvalhalla` wheel (no compiler needed),
# builds a routing graph from a Geofabrik extract and serves /route on :8002.
#
#   server/valhalla-setup.sh build      # download wheel + OSM extract, build tiles (~3 min, ~4 GB RAM peak, ~1 GB disk after)
#   server/valhalla-setup.sh serve      # run the HTTP service in the foreground (port 8010)
#
# In production the public port 8002 is served by server/proxy.py, which forwards /search to the search
# service and everything else here, so the app only ever needs one address.
#
# Env: DIR (default ./valhalla-data), PBF_URL (default Malaysia/Singapore/Brunei). Linux x86_64, Python 3.12+.
set -euo pipefail
DIR="${DIR:-$PWD/valhalla-data}"
PBF_URL="${PBF_URL:-https://download.geofabrik.de/asia/malaysia-singapore-brunei-latest.osm.pbf}"
PKG="$DIR/pkg"; export LD_LIBRARY_PATH="$PKG/pyvalhalla.libs" PYTHONPATH="$PKG"
case "${1:-}" in
  build)
    mkdir -p "$DIR/whl" "$DIR/data" "$DIR/tiles"
    [ -d "$PKG" ] || { python3 -m pip download pyvalhalla --no-deps -d "$DIR/whl"; python3 -m zipfile -e "$DIR"/whl/pyvalhalla-*.whl "$PKG"; chmod +x "$PKG"/valhalla/bin/*; }
    [ -f "$DIR/data/extract.osm.pbf" ] || python3 -c "import urllib.request,shutil,sys; shutil.copyfileobj(urllib.request.urlopen(sys.argv[1]), open(sys.argv[2],'wb'), 1<<20)" "$PBF_URL" "$DIR/data/extract.osm.pbf"
    python3 "$PKG/valhalla/valhalla_build_config.py" --mjolnir-tile-dir "$DIR/tiles" --mjolnir-timezone "$DIR/timezones.sqlite" \
      --mjolnir-admin "$DIR/admins.sqlite" --mjolnir-concurrency "$(nproc)" --httpd-service-listen "tcp://*:8010" > "$DIR/valhalla.json"
    "$PKG/valhalla/bin/valhalla_build_tiles" -c "$DIR/valhalla.json" "$DIR/data/extract.osm.pbf" ;;
  serve) exec "$PKG/valhalla/bin/valhalla_service" "$DIR/valhalla.json" 2 ;;
  *) echo "usage: $0 build|serve" >&2; exit 2 ;;
esac
