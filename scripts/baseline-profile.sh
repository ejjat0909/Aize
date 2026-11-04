#!/usr/bin/env bash
# Regenerates app/src/main/baseline-prof.txt on a connected device or emulator (API 28+).
set -euo pipefail
cd "$(dirname "$0")/.."
./gradlew :benchmark:connectedBenchmarkAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=app.aize.benchmark.BaselineProfileGenerator \
  -Pandroid.testInstrumentationRunnerArguments.androidx.benchmark.enabledRules=BaselineProfile \
  -Pandroid.testInstrumentationRunnerArguments.androidx.benchmark.suppressErrors=EMULATOR
out=$(find benchmark/build/outputs -name '*baseline-prof.txt' | head -1)
[ -n "$out" ] || { echo "no baseline profile produced" >&2; exit 1; }
cp "$out" app/src/main/baseline-prof.txt
echo "wrote app/src/main/baseline-prof.txt ($(wc -l < app/src/main/baseline-prof.txt) rules)"
