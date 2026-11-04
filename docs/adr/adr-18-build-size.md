# ADR-18 · Build & size

**Status:** accepted, partly implemented

## Decision
R8 full mode, baseline + startup profiles, resource shrinking, **per-ABI AAB, arm64-v8a only** (+x86_64 for emulators)

## Why
Waze ships two ABIs (≈ 61 MB zipped native)

## Rejected
Universal APK

## Revisit when
A device class needs armv7

## In the repo today
R8 and resource shrinking build (47 MB unsigned APK). ABIs arm64-v8a + x86_64. AAB size gate not set up.
