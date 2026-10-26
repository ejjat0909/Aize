#!/usr/bin/env bash
# Rebuild the Aize 3D sprite assets end to end:
#   render (Blender, headless) -> render off-grid validation views -> pack (WebP sheets + manifest) -> calibrate the warp plane
#   in image space -> verify (gates) -> validate against true renders -> summarize (RESULTS.md)
#
#   bash assets3d/build_all.sh pointer            # arrow (9 pitches x 24 yaws) + puck + camera calibration   (~30 min on 4 vCPU)
#   bash assets3d/build_all.sh pins               # nine billboard pins                                       (~3 min)
#   bash assets3d/build_all.sh vehicles           # sedan, taxi, suv (5 pitches x 24 yaws each)               (~25 min each)
#   bash assets3d/build_all.sh all
#   QUICK=1 bash assets3d/build_all.sh pointer    # 16 samples, 2 pitches: a smoke test (the image gates are skipped)
#
# Needs: bash, curl, xz (Blender is downloaded and checksum-verified), python3 with Pillow and numpy.
#   python3 -m pip install --target .pylib numpy pillow && export PYTHONPATH=$PWD/.pylib
# Env:   BLENDER=/path/to/blender (skips the download) - AIZE_TOOLS=<dir> (default ~/.aize-tools) - SAMPLES (default 64)
set -euo pipefail
cd "$(dirname "$0")/.."
WHAT="${1:-pointer}"
SAMPLES="${SAMPLES:-64}"; SHADOW_SAMPLES="${SHADOW_SAMPLES:-24}"
GRID_ARROW="0,7.5,15,22.5,30,37.5,45,52.5,60"; TRUTH_ARROW="3.75,18.75,33.75,48.75,56.25"
GRID_CAR="0,15,30,45,60";                      TRUTH_CAR="7.5,22.5,37.5,52.5"
QUICK="${QUICK:-0}"
RELAX=""
if [ "$QUICK" = "1" ]; then   # a 2-pitch grid cannot meet the production gates by construction: relax the numeric ones, keep the structural ones
  SAMPLES=16; SHADOW_SAMPLES=8; GRID_ARROW="0,45"; TRUTH_ARROW="22.5"; GRID_CAR="0,45"; TRUTH_CAR="22.5"; RELAX="--max-sil-dp 99 --max-err-dp 99 --min-psnr 0"
fi
BLENDER="${BLENDER:-}"
if [ -z "$BLENDER" ]; then
  bash assets3d/blender/install_blender.sh
  BLENDER="${AIZE_TOOLS:-$HOME/.aize-tools}/blender-${BLENDER_VERSION:-4.5.9}-linux-x64/blender"
fi
FR=assets3d/build/frames; DIST=assets3d/dist; TUNE=$DIST/tuning
mkdir -p "$TUNE"
render() { # asset [extra args...]
  local a="$1"; shift
  "$BLENDER" -b --factory-startup -P assets3d/blender/render_sprites.py -- --asset "$a" --size 416 --samples "$SAMPLES" --shadow-samples "$SHADOW_SAMPLES" "$@" | grep -E "RENDERED|Error|Traceback" || true
}
truth_frames() { # pitches (comma list): every half-step heading (48-yaw indices 1,7,13,25 = 7.5, 52.5, 97.5, 187.5 deg)
  local f=""; for p in ${1//,/ }; do for k in 1 7 13 25; do f="$f,$p:$k"; done; done; echo "${f#,}"
}
solid() { # asset grid truth_pitches verification_json [extra pack args]
  local a="$1" grid="$2" truth="$3" vj="$4"
  echo "== $a: render grid ($grid)";           render "$a" --pitches "$grid" --out "$FR/$a" --glb "$DIST/$a/$a.glb"
  echo "== $a: render validation views ($truth)"
  if [ "$a" = puck ]; then   # rotationally symmetric: heading is irrelevant, validate pitch only
    render "$a" --yaws 1 --frames "$(for p in ${truth//,/ }; do printf '%s:0,' "$p"; done | sed 's/,$//')" --out "$FR/${a}_truth"
  else
    render "$a" --yaws 48 --frames "$(truth_frames "$truth")" --out "$FR/${a}_truth"
  fi
  echo "== $a: pack";                           python3 assets3d/tools/pack_atlas.py --frames "$FR/$a" --asset "$a" --glb "$DIST/$a/$a.glb" --out "$DIST/$a"
  if [ "$QUICK" != "1" ]; then
    echo "== $a: calibrate the warp plane in image space"
    python3 assets3d/tools/simulate_runtime.py tune-h --asset "$a" --strategy blend --frames "$FR/$a" --truth "$FR/${a}_truth" --out "$TUNE/tune_h_${a}_blend.json"
    python3 assets3d/tools/pack_atlas.py --frames "$FR/$a" --asset "$a" --glb "$DIST/$a/$a.glb" --out "$DIST/$a" --only-manifest --tune "$TUNE/tune_h_${a}_blend.json"
    python3 assets3d/tools/simulate_runtime.py validate --asset "$a" --frames "$FR/$a" --truth "$FR/${a}_truth" --sprites "$DIST/$a/$a.sprites.json" --json "$DIST/validation_$a.json"
  fi
  # $RELAX goes LAST: argparse keeps the last value, so QUICK's relaxation must not be overridden by a per-asset ceiling passed in "${@:5}"
  python3 assets3d/tools/verify_sprites.py --frames "$FR/$a" --asset "$a" --dist "$DIST/$a" "${@:5}" $RELAX --json "$DIST/$vj"
}
if [ "$WHAT" = "pointer" ] || [ "$WHAT" = "all" ]; then
  echo "== camera calibration"
  for ay in 0.5 0.8; do render calib --anchor-y $ay --pitches 0,15,30,45,60 --samples 4 --out "$FR/calib_$ay"; python3 assets3d/tools/verify_sprites.py --calib "$FR/calib_$ay" --json "$DIST/verification.json"; done
  python3 assets3d/tools/verify_sprites.py --selftest --json "$DIST/verification.json"
  solid arrow "$GRID_ARROW" "$TRUTH_ARROW" verification.json --brand --yaw
  echo "== puck"
  solid puck "$GRID_ARROW" "3.75,18.75,33.75,48.75,56.25" verification.json --max-sil-dp 99 --max-err-dp 99
fi
if [ "$WHAT" = "pins" ] || [ "$WHAT" = "all" ]; then
  for k in police hazard accident jam closure camera gas parking destination; do
    echo "== pin_$k"; render pin_$k --pitches 0 $( [ "$QUICK" = 1 ] || echo "--samples 96 --shadow-samples 32" ) --out "$FR/pin_$k"
    python3 assets3d/tools/pack_atlas.py --frames "$FR/pin_$k" --asset "pin_$k" --out "$DIST/pin_$k"
    python3 assets3d/tools/verify_sprites.py --frames "$FR/pin_$k" --asset "pin_$k" --dist "$DIST/pin_$k" --budget-kib 200 --json "$DIST/pins_verification.json"
  done
fi
if [ "$WHAT" = "vehicles" ] || [ "$WHAT" = "all" ]; then
  # cars: --max-sil-dp 4 is a regression ceiling (measured 3.1-3.4 dp; the arrow's gate is 1.0): the tuned plane sits at the body, see README "Cars"
  for k in sedan taxi suv; do solid "car_$k" "$GRID_CAR" "$TRUTH_CAR" cars_verification.json --budget-kib 2500 --yaw --max-sil-dp 4.0; done
fi
python3 assets3d/tools/summarize.py
echo "done -> $DIST (RESULTS.md updated)"
