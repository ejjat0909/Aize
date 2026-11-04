# Building Aize on a fresh machine

## What you need

| Tool | Version used here | Notes |
|---|---|---|
| JDK | 17 | `JAVA_HOME` must point at it; the project targets 17 |
| Android SDK | platform 37, build-tools 36 | `ANDROID_HOME`; `sdkmanager "platforms;android-37.0"` |
| Gradle | wrapper (9.8.2) | `./gradlew`, nothing to install |
| Python | 3.11+ | design tokens, the asset tools, the search index builder |
| Rust | stable | `core/` and `backend/`; `rustup component add clippy rustfmt` |
| buf | 1.75+ | `proto/` linting |

Not needed to build the app: Docker, Rust, Blender. Blender is only needed to re-render the 3D sprites (`assets3d/blender/install_blender.sh`).

## Build and test

```bash
./gradlew :app:testDebugUnitTest :app:assembleDebug     # ~60 s warm, APK in app/build/outputs/apk/debug/
./gradlew :app:assembleRelease                          # R8 + resource shrinking, unsigned unless keys are set
cargo test --manifest-path core/Cargo.toml              # navigation core
cargo clippy --manifest-path core/Cargo.toml --all-targets -- -D warnings
buf lint proto
python3 design/generate_android.py --check              # generated code matches the tokens
python3 scripts/check_no_waze_assets.py                 # legal gate
```

## Build-time configuration

Everything that differs per environment comes in as a Gradle property or an environment variable; nothing is hard-coded and no secret is in the repo.

| Setting | How | Default |
|---|---|---|
| Server address baked into the app | `-Paize.server=https://host:port` | `http://10.0.2.2:8002` (emulator → host) |
| Environment tag in telemetry | `-Paize.env=staging` | `dev` |
| Release signing | `AIZE_KEYSTORE`, `AIZE_KEYSTORE_PASSWORD`, `AIZE_KEY_ALIAS`, `AIZE_KEY_PASSWORD` | unsigned release build |

The address is still editable in the app under **Server**, so a test build is never stuck with a stale link.

## Emulator

```bash
export ANDROID_AVD_HOME=/root/.android/avd ANDROID_HOME=/opt/android-sdk
$ANDROID_HOME/emulator/emulator -avd api34 -no-window -no-audio -gpu swiftshader_indirect &
adb install -r app/build/outputs/apk/debug/app-debug.apk
adb shell pm grant app.aize android.permission.ACCESS_FINE_LOCATION
adb emu geo fix 101.6862 3.1343        # lon lat
```

### Driving without a car (P4-11)

`scripts/replay-route.py` injects fixes along a real route, so guidance, voice and re-routing can be
exercised the same way every time:

```bash
# drive the server's own route at 45 km/h, then miss a turn 300 m to the side at 45 %
scripts/replay-route.py --route 3.1343,101.6862 3.1179,101.6770 --speed 45 --miss-at 0.45 --miss-offset 300

# a GPX track, with a 20 s tunnel halfway
scripts/replay-route.py --gpx track.gpx --speed 60 --tunnel-at 0.5 --tunnel-seconds 20
```

`--dry-run` prints the fixes without touching adb. Watch the result with
`adb logcat -s Aize AizeNav AizeVoice`.

The AVD needs `disk.dataPartition.size` small enough that the emulator's 1.2× free-space check passes; on this machine that means a 2 GB partition and an explicit `-data` image.

## Performance harness

`:benchmark` holds the Macrobenchmark tests (`scripts/baseline-profile.sh` regenerates the profile, `scripts/perfetto-capture.sh` takes a trace). First numbers and their caveats: `docs/verification/p0-perf.md`.
