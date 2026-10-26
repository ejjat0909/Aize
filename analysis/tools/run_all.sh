#!/usr/bin/env bash
# One-command static pipeline for an Android APK. Nothing is installed or executed from the APK.
#
#   bash analysis/tools/run_all.sh /path/to/app.apk analysis/data [--no-rea] [--jadx] [--report docs/01-waze-apk-structure-report.md]
#
# Needs: python3, unzip-free (Python zipfile), aapt2 (env AAPT2 or on PATH), openssl (signing block, optional).
# Optional: `rea` CLI (rea-agents >= 6.7) for the whole-APK inventory evidence; --jadx additionally runs
# rea_android_batch.sh (version-specific class list; needs REA_JADX_MCP_JAR and a few hundred MB of RAM per dex slice).
set -euo pipefail
APK="${1:?usage: run_all.sh APK OUT_DIR [--no-rea] [--jadx] [--report OUT.md]}"; OUT="${2:?OUT_DIR}"; shift 2
NO_REA=0; JADX=0; REPORT=""
while [ $# -gt 0 ]; do case "$1" in --no-rea) NO_REA=1;; --jadx) JADX=1;; --report) REPORT="$2"; shift;; *) echo "unknown arg $1"; exit 2;; esac; shift; done
HERE="$(cd "$(dirname "$0")" && pwd)"; ROOT="$(cd "$HERE/.." && pwd)"
AAPT2="${AAPT2:-$(command -v aapt2 || true)}"; [ -n "$AAPT2" ] && [ -x "$AAPT2" ] || { echo "aapt2 not found: set AAPT2=/path/to/build-tools/<ver>/aapt2" >&2; exit 2; }
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT; mkdir -p "$OUT"
step() { printf '\n== %s\n' "$*"; }

step "aapt2 resource table";           "$AAPT2" dump resources "$APK" > "$WORK/resources-dump.txt"
step "archive inventory";               python3 "$HERE/apk_inventory.py" "$APK" "$OUT/inventory.json" "$OUT/apk_files.csv"
step "resources, tokens, motion, layouts"; python3 "$HERE/resources_parse.py" "$APK" "$WORK/resources-dump.txt" "$WORK/res"
cp "$WORK/res/"{resources_summary,design_tokens,motion,layouts}.json "$WORK/res/resource_files.csv" "$OUT/"
step "manifest";                        python3 "$HERE/manifest_parse.py" "$APK" "$WORK/res/resource_ids.json" "$OUT/manifest.json"
step "DEX structure";                   python3 "$HERE/dex_scan.py" "$APK" "$OUT/dex_summary.json" "$WORK/first_party_classes.txt"
step "native libraries"
python3 - "$APK" "$WORK" <<'PY'
import sys, zipfile, shutil
z = zipfile.ZipFile(sys.argv[1]); w = sys.argv[2]
for member, dst in (("lib/arm64-v8a/libwaze.so", "libwaze-arm64.so"), ("lib/arm64-v8a/libogg_opus_encoder.so", "libogg_opus_encoder-arm64.so")):
    try:
        with z.open(member) as s, open(f"{w}/{dst}", "wb") as o: shutil.copyfileobj(s, o)
    except KeyError: print("missing", member)
pck = [n for n in z.namelist() if n.endswith(".pck")]
if pck:
    with z.open(pck[0]) as s, open(f"{w}/waze.pck", "wb") as o: shutil.copyfileobj(s, o)
PY
[ -f "$WORK/libwaze-arm64.so" ] && python3 "$HERE/elf_scan.py" "$WORK/libwaze-arm64.so" "$OUT/libwaze_summary.json"
[ -f "$WORK/libogg_opus_encoder-arm64.so" ] && python3 "$HERE/elf_scan.py" "$WORK/libogg_opus_encoder-arm64.so" "$OUT/libogg_opus_summary.json"
[ -f "$WORK/waze.pck" ] && python3 "$HERE/pck_scan.py" "$WORK/waze.pck" "$OUT/pck_summary.json" "$OUT/pck_files.csv"
step "features, assets, signing"
python3 "$HERE/features_scan.py" "$APK" "$WORK" "$WORK/first_party_classes.txt" "$OUT/resource_files.csv"; cp "$WORK/features.json" "$OUT/features.json"
python3 "$HERE/assets_scan.py" "$APK" "$OUT/assets.json" "$ROOT/data_ref/voicepack_valid_filenames.txt"
python3 "$HERE/signing_scan.py" "$APK" "$OUT/signing.json" || true

if [ "$NO_REA" = 0 ] && command -v rea >/dev/null 2>&1; then
  step "REA: whole-APK inventory evidence (rea inspect-artifact)"
  mkdir -p "$WORK/rea"; rea inspect-artifact "$APK" --format json > "$WORK/rea/apk-inspect-artifact.json"
  if [ "$JADX" = 1 ]; then echo "JADX slices: run  APK=$APK bash $HERE/rea_android_batch.sh  (version-specific class list; see analysis/README.md), then build_rea_index.py"; fi
  echo "REA inventory evidence saved to $WORK/rea (temporary). The committed analysis/data/rea_evidence_index.json is only rebuilt by build_rea_index.py after the JADX batch."
else
  echo "REA step skipped (--no-rea or rea not installed)"
fi
if [ -n "$REPORT" ] && [ -f "$OUT/rea_evidence_index.json" ]; then step "render structure report"; python3 "$HERE/render_structure_report.py" "$OUT" "$REPORT"; fi
echo; echo "done -> $OUT"
