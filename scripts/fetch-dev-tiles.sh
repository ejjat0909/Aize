#!/usr/bin/env bash
# Download the dev basemap for the walking-skeleton APK: a Kuala Lumpur extract (~17 MB) of the Protomaps daily
# OpenStreetMap build, written to data/dev/assets/tiles/ (gitignored; Gradle bundles it into the debug APK).
#
#   scripts/fetch-dev-tiles.sh                # KL, zoom 0-15
#   BBOX=100.5,2.8,102,3.6 scripts/fetch-dev-tiles.sh
#
# Needs the `pmtiles` CLI (https://github.com/protomaps/go-pmtiles/releases) on PATH.
# Data: (c) OpenStreetMap contributors, ODbL - the app shows the attribution; see NOTICE.md.
set -euo pipefail
cd "$(dirname "$0")/.."
command -v pmtiles >/dev/null || { echo "pmtiles CLI not found; install it from https://github.com/protomaps/go-pmtiles/releases" >&2; exit 1; }
BBOX="${BBOX:-101.62,3.04,101.78,3.24}"
MAXZOOM="${MAXZOOM:-15}"
DAY="${BUILD_DATE:-$(date -u -d 'yesterday' +%Y%m%d 2>/dev/null || date -u -v-1d +%Y%m%d)}"
OUT="data/dev/assets/tiles/kuala-lumpur.pmtiles"
mkdir -p "$(dirname "$OUT")"
rm -f "$OUT"
pmtiles extract "https://build.protomaps.com/${DAY}.pmtiles" "$OUT" --bbox="$BBOX" --maxzoom="$MAXZOOM"
ls -l "$OUT"
