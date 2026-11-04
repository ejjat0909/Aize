#!/usr/bin/env bash
# Captures a 10 s Perfetto trace of Aize from a connected device (API 29+). Usage: scripts/perfetto-capture.sh [out.perfetto-trace]
set -euo pipefail
out=${1:-aize.perfetto-trace}
adb shell perfetto -o /data/misc/perfetto-traces/aize.trace -t 10s \
  sched freq idle am wm gfx view binder_driver hal dalvik input res -a app.aize
adb pull /data/misc/perfetto-traces/aize.trace "$out"
echo "open $out at https://ui.perfetto.dev"
