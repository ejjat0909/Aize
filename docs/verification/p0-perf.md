# P0-09 — first performance numbers

Measured with the `:benchmark` module (Macrobenchmark 1.5.0, `StartupTimingMetric`, `StartupMode.COLD`, 5 iterations) on this build machine's emulator. **These are regression numbers, not product numbers.** The emulator renders with swiftshader on 2 emulated cores; a real phone will be several times faster. The point of this file is that the harness exists and the numbers are recorded, so a change that makes startup worse is visible.

| Metric | Measured (median) | Plan budget, mid-tier | Verdict |
|---|---|---|---|
| Cold start, TTID, no compilation | **3 541 ms** | ≤ 1 200 ms | 3× over budget, on software GL |
| Cold start, TTID, "baseline profile" mode | **3 437 ms** | ≤ 1 200 ms | 3% better than no compilation |

Device context reported by the benchmark: `sdk_gphone64_x86_64`, Android 14 (API 34), 2 cores at 2.0 GHz, 2.6 GB RAM, `run-from-apk` compilation.

## What this does and does not show

* The 3% gap between the two runs is **not** the value of a baseline profile: the app has no `baseline-prof.txt` yet, so both runs are effectively uncompiled. Once `scripts/baseline-profile.sh` has produced one, re-run and the gap becomes meaningful.
* Startup here includes MapLibre style load and the bundled KL tile archive; it is the app's real cold path, not a blank activity.
* No frame-time numbers yet. `JankStats` runs in debug builds (`adb logcat -s AizeJank`) but a jank budget needs a real device to mean anything.

## Reproducing

```bash
export ANDROID_AVD_HOME=/root/.android/avd ANDROID_HOME=/opt/android-sdk
$ANDROID_HOME/emulator/emulator -avd api34 -no-window -no-audio -gpu swiftshader_indirect &
./gradlew :benchmark:connectedBenchmarkAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=app.aize.benchmark.StartupBenchmark
# results: benchmark/build/outputs/connected_android_test_additional_output/**/benchmarkData.json
```

On a device, drop nothing and do not suppress the emulator warning: the numbers are then real and can be compared against the budget table in `02-aize-build-plan.md` §9.
