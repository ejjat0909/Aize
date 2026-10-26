#!/usr/bin/env bash
# Run REA's JADX-backed Android tools on single-dex slices of the APK.
# (Loading the whole 60k-class APK into JADX is OOM-killed on a 1 GiB VM; one dex at a time fits.)
set -u
cd "$(dirname "$0")/.."
export REA_JADX_MCP_JAR="${REA_JADX_MCP_JAR:-/workspace/.rea-tools/jadx-headless-mcp-0.7.1-all.jar}"
export REA_JADX_HEAP_MIB="${REA_JADX_HEAP_MIB:-300}" REA_JADX_OPERATION_TIMEOUT_MS=300000
run() { n="$1"; shift; /usr/bin/time -f "%e s, %M KB" rea "$@" --format json > "rea/$n.json" 2> "rea/$n.err"; echo "$n exit=$? $(tail -1 rea/$n.err)" >> rea/batch.log; }
: > rea/batch.log
S6=tmp/mini-classes6.apk; S7=tmp/mini-classes7.apk
mkdir -p tmp rea
if [ ! -f "$S6" ] || [ ! -f "$S7" ]; then
  : "${APK:?set APK=/path/to/waze.apk to build the single-dex slices (classes6.dex, classes7.dex for 5.22.90.123)}"
  python3 "$(dirname "$0")/make_dex_slice.py" "$APK" classes6.dex "$S6"; python3 "$(dirname "$0")/make_dex_slice.py" "$APK" classes7.dex "$S7"
fi
run m-WazeRenderer-h        inspect-android-method $S6 com.waze.map.opengl.WazeRenderer h --overload-index 0
run m-WazeRenderer-i        inspect-android-method $S6 com.waze.map.opengl.WazeRenderer i --overload-index 0
run m-Location-sendUpdate   inspect-android-method $S6 com.waze.location.LocationSensorListener sendUpdateToNativeLayer --overload-index 0
run m-Location-createJni    inspect-android-method $S6 com.waze.location.LocationSensorListener createNativeLocationJNI --overload-index 0
run c-NativeCanvasRenderer  inspect-android-class  $S6 com.waze.map.NativeCanvasRenderer
run c-NetworkManager        inspect-android-class  $S6 com.waze.network.NetworkManager
run c-MainCanvasDelegator   inspect-android-class  $S6 com.waze.map.canvas.MainCanvasDelegatorImpl
run c-FreeMapAppActivity    inspect-android-class  $S7 com.waze.FreeMapAppActivity
run c-SoundNativeManager    inspect-android-class  $S7 com.waze.sound.SoundNativeManager
echo done >> rea/batch.log
